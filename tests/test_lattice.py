"""向量化反射表 vs 标量参考实现：必须逐项一致。

`lattice.reflections()` 是为了让「a/b/c 三轴同时精修」可行而写的向量化版本
（单次 ~10 ms，标量版 ~88 ms）。它是性能关键路径，一旦引入近似就会让
Rietveld 拟合悄悄偏掉，所以这里用标量实现做**金标准**逐项比对。
"""

from __future__ import annotations

import numpy as np
import pytest

from lfp.core.profile.forward import reflection_table  # noqa: F401  (契约存在性)
from lfp.core.profile.lattice import reflections
from lfp.core.profile.struct import compute_peaks


def _scalar(struct, wavelength: float, lo: float, hi: float):
    peaks, _skipped = compute_peaks(struct, wavelength=wavelength,
                                    two_min=lo, two_max=hi)
    tt = np.asarray([p[0] for p in peaks], dtype=float)
    ii = np.asarray([p[1] for p in peaks], dtype=float)
    return tt, ii


def test_vectorized_matches_scalar(struct):
    lo, hi, wl = 10.0, 80.0, 1.54056
    vec = reflections(struct, wavelength=wl, two_min=lo, two_max=hi)
    tt_s, ii_s = _scalar(struct, wl, lo, hi)

    assert vec.two_theta.size == tt_s.size, "峰条数不一致"
    assert np.allclose(vec.two_theta, tt_s, atol=1e-9)
    # 强度是任意单位，只要两边的总标度一致就能逐条比较相对值
    ii_v = np.asarray(vec.intensity, dtype=float)
    assert ii_s.max() > 0 and ii_v.max() > 0
    rel = np.max(np.abs(ii_v / ii_v.max() - ii_s / ii_s.max()))
    assert rel < 1e-9, f"相对强度偏差 {rel:.2e}"


def test_hkl_canonicalised(struct):
    """指数规范化：首非零指数为正，避免 (-2 0 0) 与 (2 0 0) 同峰两张脸。"""
    vec = reflections(struct, two_min=10.0, two_max=60.0)
    hkl = np.asarray(vec.hkl)
    assert hkl.ndim == 2 and hkl.shape[1] == 3
    for h, k, l in hkl:
        first = next((v for v in (h, k, l) if v != 0), 0)
        assert first > 0, f"未规范化的指数: {(h, k, l)}"


def test_ascending_and_profitable(struct):
    """输出必须按 2θ 升序（前向模型按此顺序铺峰，顺序错会导致峰张冠李戴）。"""
    vec = reflections(struct, two_min=5.0, two_max=120.0)
    assert np.all(np.diff(vec.two_theta) > 0)
    assert vec.two_theta[0] >= 5.0 - 1e-6
    assert vec.two_theta[-1] <= 120.0 + 1e-6
    assert np.all(np.asarray(vec.n_merged) >= 1)


def test_po_weighting_changes_intensities(struct):
    """择优取向必须真的改变强度比（否则 PO 精修是空转）。"""
    base = reflections(struct, two_min=10.0, two_max=60.0)
    po = reflections(struct, two_min=10.0, two_max=60.0, po=(0, 2, 0, 0.7))
    i0 = np.asarray(base.intensity, dtype=float)
    i1 = np.asarray(po.intensity, dtype=float)
    assert i0.size == i1.size
    ratio = (i1 / np.maximum(i0, 1e-30))
    assert not np.allclose(ratio, 1.0), "March–Dollase 未生效"
    assert np.all(ratio > 0)
