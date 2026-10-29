"""物相判定：判据、鲁棒性、以及「误判比漏判更危险」的负例。

判定是整个软件的闸门：判错就会拿一个不属于自己的结构去精修，得到一组
看起来漂亮但物理上无意义的晶胞参数。因此这里既测**该判过的一定判过**，
也测**不该判过的绝不能判过**（负例比正例更重要）。
"""

from __future__ import annotations

import numpy as np
import pytest

from conftest import make_pattern
from lfp.core.dtypes import Pattern
from lfp.core.profile.forward import scaled_cell
from lfp.core.refine.api import identify_pattern
from lfp.core.refine.nonlinear import initial_params


def test_synthetic_lfp_is_identified(struct):
    pat = make_pattern(struct)
    res = identify_pattern(pat, struct)
    assert res.is_lfp
    assert res.coverage >= 0.70
    assert res.top_strong_matched == 3
    assert res.unexplained <= 0.35
    assert res.summary_key() == "ident.verdict.pass"
    assert res.n_matched >= 3
    assert res.n_ref_used > 0
    # 健康样本不该触发残差闸门，且零点应回到合成值附近（默认 zero=0.02）
    assert res.model_ok
    assert res.resid_rms <= 0.45 * res.tolerance
    assert res.zero_shift == pytest.approx(0.02, abs=0.06)


def test_zero_shift_is_recovered(struct):
    """仪器零点/样品位移 ±0.15° 必须能被吸收，不能因峰位整体平移而判否。

    注意精度要求不是网格步长（0.02°）级别的：网格只负责建立对应关系，
    零点由最小二乘反解给出。早期实现只用网格取覆盖率最大者，零点会被
    报成 0.04°（覆盖率关于 dz 在 ±tol 内是平台，最优点随机落点）。
    """
    pat = make_pattern(struct, zero=0.15)
    res = identify_pattern(pat, struct)
    assert res.is_lfp
    assert res.zero_shift == pytest.approx(0.15, abs=0.06)


def test_negative_zero_shift_is_recovered(struct):
    """反向零点同样成立（避免反解符号写反却被正偏差掩盖）。"""
    res = identify_pattern(make_pattern(struct, zero=-0.12), struct)
    assert res.is_lfp
    assert res.zero_shift == pytest.approx(-0.12, abs=0.06)


def test_small_isotropic_cell_change_is_absorbed(struct):
    """晶胞整体胀缩 0.4 %（固溶体/Li 含量变化量级）仍应判为 LFP。"""
    shifted = scaled_cell(struct, 1.004, 1.004, 1.004)
    res = identify_pattern(make_pattern(shifted, zero=0.05), struct)
    assert res.is_lfp
    assert res.cell_scales is not None


def test_large_anisotropic_distortion_is_rejected(struct):
    """各向异性形变达 ±1 % 时判否——判定用的是「各向同性胀缩 + 零点」模型，
    超出模型能力就该拒绝，而不是硬凑一个覆盖率交差。"""
    distorted = scaled_cell(struct, 1.01, 0.995, 1.0)
    res = identify_pattern(make_pattern(distorted, zero=0.05), struct)
    assert not res.is_lfp
    assert res.summary_key() != "ident.verdict.pass"


def test_mild_anisotropy_is_rejected_by_residual_gate(struct):
    """覆盖率能过关、但峰位残差超标的各向异性形变，必须由残差闸门拦下。

    这是「模型充分性」判据唯一能被单独验证的场景：该样本覆盖率 0.73、
    前三强 3/3、未解释强度 0.32，三条基本判据全部通过，只有「两参数模型
    解释不了峰位」这一条成立。若哪天有人把闸门删掉或放宽，这条测试会红。
    """
    distorted = scaled_cell(struct, 1.01, 0.997, 1.0)
    res = identify_pattern(make_pattern(distorted, zero=0.05), struct)
    assert res.coverage >= 0.70, "样本应保持较高覆盖率，否则测不到闸门"
    assert res.top_strong_matched == 3
    assert res.unexplained <= 0.35
    assert not res.model_ok
    assert not res.is_lfp


def _foreign_pattern(seed: int = 3) -> Pattern:
    """一组与 LFP 无关的峰（间距、强弱的排布都不同）。"""
    x = np.arange(10.0, 90.0, 0.02)
    y = np.full_like(x, 80.0)
    for pos, amp in ((12.5, 900.0), (21.0, 400.0), (25.0, 1200.0),
                     (31.0, 300.0), (41.0, 500.0), (55.0, 350.0)):
        y += amp * np.exp(-((x - pos) ** 2) / (2 * 0.09 ** 2))
    y = np.random.default_rng(seed).poisson(y).astype(float)
    return Pattern(x, y, {"wavelength": 1.54056, "anode": "Cu"})


def test_foreign_pattern_is_rejected(struct):
    res = identify_pattern(_foreign_pattern(), struct)
    assert not res.is_lfp
    assert res.summary_key() in ("ident.verdict.fail", "ident.verdict.partial")
    assert res.coverage < 0.7


def test_flat_pattern_is_rejected(struct):
    x = np.arange(10.0, 60.0, 0.02)
    res = identify_pattern(Pattern(x, np.full_like(x, 50.0)), struct)
    assert not res.is_lfp


# --------------------------------------------------------------------------- #
# 真实仪器数据回归（目录可用时才跑）
# --------------------------------------------------------------------------- #
REAL_CASES = [
    ("LiFePO4#01##20250520-100220_100.txt", True),
    ("LinSuanTieLi#1##20250527-141148_100.txt", True),
    ("FePO4#01##20250520-132913_100.txt", False),
    ("PVDF#01##20250527-161442_100.txt", False),
    ("LLZTO#01##20250521-130019_100.txt", False),
    ("ShiMo-C3#1##20250527-180340_100.txt", False),
    ("1. Si.txt", False),
    ("羟基磷灰石#01##20250522-094117_100.txt", False),
]


@pytest.mark.parametrize("name,expect", REAL_CASES)
def test_real_patterns(struct, real_data_dir, name, expect):
    if real_data_dir is None:
        pytest.skip("未提供真实谱图目录（POLYXRD_LFP_DATA）")
    path = real_data_dir / name
    if not path.exists():
        pytest.skip(f"缺少样本 {name}")
    from lfp.core.io import read_pattern

    res = identify_pattern(read_pattern(path), struct)
    assert res.is_lfp is expect, (
        f"{name}: 判定 {res.is_lfp}（期望 {expect}），"
        f"coverage={res.coverage:.3f}, unexplained={res.unexplained:.3f}, "
        f"top3={res.top_strong_matched}")
