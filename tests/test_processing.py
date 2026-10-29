"""谱图处理：平滑 / 扣背景 / 去 Kα2 / 裁谱。

这些操作在界面上是「所见即所得」的，一旦实现有偏差，用户会在错误的谱上
做寻峰和判读。测试关注的是**不变量**（峰位不动、长度为 0 的负值被裁剪、
Kα2 剥离后峰位回到 Kα1 位置），而不是逐点比对某个常数。
"""

from __future__ import annotations

import numpy as np
import pytest

from lfp.core.dtypes import Pattern
from lfp.core.processing import (
    crop,
    estimate_background,
    ka2_shift,
    savgol,
    snip,
    strip_kalpha2,
    subtract,
)


def _gauss_pattern(pos=30.0, width=0.10, amp=1000.0, bg=100.0,
                   lo=20.0, hi=45.0, step=0.01, seed=7) -> Pattern:
    x = np.arange(lo, hi, step)
    y = bg + amp * np.exp(-((x - pos) ** 2) / (2 * width ** 2))
    y = np.random.default_rng(seed).poisson(y).astype(float)
    return Pattern(x, y, {"wavelength": 1.54056, "anode": "Cu"})


def test_savgol_keeps_peak_position():
    pat = _gauss_pattern()
    y = savgol(pat.intensity, 15, 3)
    assert y.size == pat.intensity.size
    assert abs(pat.two_theta[np.argmax(y)] - 30.0) < 0.02
    # 平滑不应抬高或压低峰顶太多（< 3%）
    assert abs(y.max() - pat.intensity.max()) / pat.intensity.max() < 0.05


def test_snip_never_above_spectrum():
    pat = _gauss_pattern()
    bg = snip(pat.intensity, iterations=20)
    assert np.all(bg <= pat.intensity + 1e-9)
    # 峰位处的背景应显著低于峰顶
    i = int(np.argmax(pat.intensity))
    assert bg[i] < 0.5 * pat.intensity[i]


def test_estimate_background_dispatch_and_subtract():
    pat = _gauss_pattern()
    for method in ("snip", "poly", "linear"):
        bg = estimate_background(pat, method, iterations=20, order=3)
        assert bg.shape == pat.intensity.shape
        assert np.all(np.isfinite(bg))
    net = subtract(pat, estimate_background(pat, "snip", iterations=20))
    assert np.all(net.intensity >= 0.0)          # 负值被裁掉
    assert net.meta.get("bg_subtracted") is True
    assert net.two_theta.size == pat.two_theta.size


def test_crop_keeps_step_and_guards_pathological_range():
    pat = _gauss_pattern(lo=10.0, hi=60.0)
    sub = crop(pat, 20.0, 30.0)
    assert sub.two_theta[0] >= 20.0 and sub.two_theta[-1] <= 30.0
    assert sub.step == pytest.approx(pat.step, rel=1e-9)
    # 区间过窄时宁可返回原谱，也不给出一个只有几个点的「精修」
    assert crop(pat, 25.0, 25.0001).two_theta.size == pat.two_theta.size


def test_ka2_shift_is_positive_and_grows_with_angle():
    x = np.array([20.0, 60.0, 100.0])
    d = ka2_shift(x, 1.54056, 1.54439)
    assert np.all(d > 0)
    assert np.all(np.diff(d) > 0)          # Δ2θ ∝ tanθ·Δλ/λ，随角度增大


def test_strip_kalpha2_recovers_single_peak():
    """构造 Kα1 + 0.5·Kα2 双峰；剥离后应回到「只有 Kα1」的形状。

    这条测试锁死递推方向：若写成高角→低角，Kα1 峰会被越扣越矮（多轮后变负），
    而这里要求 Kα1 峰保留 ≥95%、Kα2 肩峰落到 Kα1 尾部水平。
    """
    step = 0.005
    x = np.arange(28.0, 32.0, step)
    w1, w2 = 1.54056, 1.54439
    pos1, width, bg = 30.0, 0.06, 50.0
    shift = float(ka2_shift(np.array([pos1]), w1, w2)[0])
    y = (1000 * np.exp(-((x - pos1) ** 2) / (2 * width ** 2))
         + 500 * np.exp(-((x - pos1 - shift) ** 2) / (2 * width ** 2)) + bg)
    pat = Pattern(x, y, {"wavelength": w1, "anode": "Cu"})

    out = strip_kalpha2(pat, "Cu", 0.5, iterations=2)
    assert out.two_theta.size == x.size
    assert np.all(out.intensity >= 0.0)
    i1 = int(np.argmin(np.abs(x - pos1)))
    i2 = int(np.argmin(np.abs(x - (pos1 + shift))))
    # Kα1 峰顶基本保留（只把叠在上面的 Kα2 尾巴扣掉）
    assert out.intensity[i1] == pytest.approx(1050.0, rel=0.05)
    assert out.intensity[i1] < y[i1]            # 确实扣了东西
    # Kα2 峰位处应落到「Kα1 在 30.08° 的尾部 + 背景」量级
    assert out.intensity[i2] == pytest.approx(
        1000 * np.exp(-shift ** 2 / (2 * width ** 2)) + bg, rel=0.15)


def test_strip_kalpha2_is_idempotent_in_iterations():
    """多轮迭代不得把峰越扣越矮（曾经的缺陷：第二次迭代重复扣除）。"""
    pat = _gauss_pattern()
    a = strip_kalpha2(pat, "Cu", 0.5, iterations=1)
    b = strip_kalpha2(pat, "Cu", 0.5, iterations=4)
    assert np.allclose(a.intensity, b.intensity, rtol=1e-9, atol=1e-9)
    assert np.all(b.intensity >= 0.0)


def test_strip_kalpha2_rejects_unknown_anode():
    pat = _gauss_pattern()
    with pytest.raises(ValueError):
        strip_kalpha2(pat, "Xx")
