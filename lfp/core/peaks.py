"""寻峰与单峰拟合。

寻峰
----
在扣背景后的净谱上找局部极大，用**峰突出度**（prominence：峰顶到两侧最低
鞍部的落差）而不是绝对高度做阈值。突出度判据对连续衰减背景与肩峰更稳健，
也是 SciPy ``find_peaks`` 的标准定义（与 scipy.signal.peak_prominences 一致）。

单峰拟合
--------
对每个候选峰在 ±half 窗口内拟合::

    y = a0 + a1·(2θ − 2θ_c) + η·L(2θ) + (1−η)·G(2θ)

即「局部线性背景 + pseudo-Voigt」，参数 (a0, a1, 2θ_c, 峰高, FWHM, η) 用
有界最小二乘求解，返回峰位、FWHM、净峰高、积分面积与拟合 R²。
拟合失败（点数不足/不收敛）时退化为「窗口内极大值 + 半高宽」的解析估计，
并在结果里标记 ``fitted=False``，不静默返回坏数。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from lfp.core.dtypes import Pattern

#: 默认寻峰阈值（相对净谱最大值的比例）
DEFAULT_MIN_REL_HEIGHT = 0.01
DEFAULT_MIN_PROMINENCE = 0.005
#: 默认信噪比下限（峰高 / 稳健噪声）。低于 3 的「峰」在粉末谱上不可靠。
DEFAULT_MIN_SNR = 3.0
#: 默认拟合窗口半宽（度）
DEFAULT_FIT_HALF = 0.6


@dataclass(frozen=True)
class ObservedPeak:
    """实测谱上的一条峰。"""

    two_theta: float
    height: float            # 净峰高（扣局部背景后）
    area: float              # 积分面积（pV 解析面积）
    fwhm: float              # 度
    eta: float               # Lorentz 占比
    snr: float               # 峰高 / 局部噪声（相邻点差分的稳健标准差）
    r2: float                # 拟合决定系数
    fitted: bool             # False = 解析退化估计
    left: float              # 峰区左边界（度）
    right: float             # 峰区右边界（度）


def d_of(two_theta: float, wavelength: float) -> float:
    """Bragg 方程求 d (Å)。"""
    s = math.sin(math.radians(two_theta / 2.0))
    return wavelength / (2.0 * s) if s > 1e-9 else float("inf")


def _robust_sigma(y: np.ndarray) -> float:
    """相邻点差分的稳健噪声估计（MAD），避免把峰本身计入噪声。"""
    if y.size < 3:
        return float(np.std(y)) if y.size else 0.0
    d = np.diff(y)
    mad = float(np.median(np.abs(d - np.median(d))))
    return max(1.4826 * mad / math.sqrt(2.0), 1e-9)


def _pv(x, pos, fwhm, eta):
    fwhm = max(float(fwhm), 1e-4)
    z = (x - pos) / fwhm
    return eta / (1.0 + 4.0 * z * z) + (1.0 - eta) * np.exp(-4.0 * math.log(2) * z * z)


def _fit_one(x: np.ndarray, y: np.ndarray, pos0: float, half: float):
    """在窗口内拟合 pV + 线性背景；失败返回 None。

    位置边界收得很紧（±40 % 窗口宽，且不超过 0.25°）：单峰拟合最典型的失效
    模式是「用一条又宽又高的 pV 把整段窗口包住」，此时位置会跑到窗口边缘、
    峰高虚高 2 倍以上（真实数据上表现为 29.7° 的峰被报成 28.6° 的胖峰）。
    位置接近检测到的局部极大是我们唯一的先验，必须用上。
    """
    lo, hi = pos0 - half, pos0 + half
    m = (x >= lo) & (x <= hi)
    if np.count_nonzero(m) < 8:
        return None
    xs, ys = x[m], y[m]
    h0 = float(np.max(ys) - np.min(ys))
    if h0 <= 0:
        return None
    pos_half = min(0.40 * half, 0.25)
    p0 = [float(np.min(ys)), 0.0, pos0, h0, max(half / 3.0, 0.02), 0.5]
    lower = [-np.inf, -np.inf, pos0 - pos_half, 0.0, 1e-3, 0.0]
    upper = [np.inf, np.inf, pos0 + pos_half, h0 * 2.0 + 1.0, 4.0 * half, 1.0]
    try:
        from scipy.optimize import least_squares
        res = least_squares(
            lambda p: (p[0] + p[1] * (xs - pos0)
                       + p[3] * _pv(xs, p[2], p[4], p[5])) - ys,
            p0, bounds=(lower, upper), method="trf", max_nfev=160,
            ftol=1e-5, xtol=1e-5, gtol=1e-5)
        p = res.x
        model = p[0] + p[1] * (xs - pos0) + p[3] * _pv(xs, p[2], p[4], p[5])
        ss_res = float(np.sum((ys - model) ** 2))
        ss_tot = float(np.sum((ys - np.mean(ys)) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        return float(p[2]), float(p[3]), float(p[4]), float(p[5]), r2, True
    except Exception:
        return None


def _analytic(x: np.ndarray, y: np.ndarray, pos0: float, half: float):
    """退化估计：窗口极大 + 半高宽（线性插值）×1.0（pV 近似 G 的 FWHM）。"""
    m = (x >= pos0 - half) & (x <= pos0 + half)
    if np.count_nonzero(m) < 3:
        return pos0, 0.0, 0.0, 0.5, 0.0, False
    xs, ys = x[m], y[m]
    i = int(np.argmax(ys))
    peak = float(ys[i])
    base = float(np.min(ys))
    height = max(peak - base, 0.0)
    half_level = base + 0.5 * height
    left = right = xs[i]
    for j in range(i, 0, -1):
        if ys[j - 1] <= half_level:
            left = xs[j - 1] + (half_level - ys[j - 1]) / max(ys[j] - ys[j - 1], 1e-12) * (xs[j] - xs[j - 1])
            break
    for j in range(i, len(xs) - 1):
        if ys[j + 1] <= half_level:
            right = xs[j] + (ys[j] - half_level) / max(ys[j] - ys[j + 1], 1e-12) * (xs[j + 1] - xs[j])
            break
    return float(xs[i]), height, max(right - left, 1e-3), 0.5, 0.0, False


def find_peaks(pattern: Pattern, *, min_rel_height: float = DEFAULT_MIN_REL_HEIGHT,
               min_prominence: float = DEFAULT_MIN_PROMINENCE,
               fit_half: float = DEFAULT_FIT_HALF,
               background: np.ndarray | None = None,
               min_snr: float = DEFAULT_MIN_SNR,
               max_peaks: int = 200) -> list[ObservedPeak]:
    """在（扣背景后的）谱上寻峰并逐个拟合。

    pattern        : 谱（建议先扣背景；background 给定时先做净谱化再寻峰）
    min_rel_height : 峰高下限（相对净谱最大值）
    min_prominence : 突出度下限（相对净谱最大值）
    fit_half       : 单峰拟合窗口半宽（度）
    min_snr        : 信噪比下限（峰高 / 稳健噪声）
    """
    x = np.asarray(pattern.two_theta, dtype=np.float64)
    y = np.asarray(pattern.intensity, dtype=np.float64)
    if background is not None:
        y = np.maximum(y - np.asarray(background, dtype=np.float64), 0.0)
    if x.size < 10:
        return []
    ymax = float(np.max(y))
    if ymax <= 0:
        return []
    try:
        from scipy.signal import find_peaks as _fp
        idx, props = _fp(y, height=min_rel_height * ymax,
                         prominence=min_prominence * ymax)
    except Exception:
        idx = np.array([i for i in range(1, y.size - 1)
                        if y[i] >= y[i - 1] and y[i] >= y[i + 1]
                        and y[i] >= min_rel_height * ymax])
    if idx.size == 0:
        return []
    # 按高度取前 max_peaks 条，最终按 2θ 升序输出
    if idx.size > max_peaks:
        order = np.argsort(y[idx])[::-1][:max_peaks]
        idx = np.sort(idx[order])
    noise = _robust_sigma(y)
    out: list[ObservedPeak] = []
    for i in idx:
        pos0 = float(x[i])
        win = (x >= pos0 - fit_half) & (x <= pos0 + fit_half)
        # 数据本身给出的净峰高（窗口内极差）：用来判断拟合是否「胖得离谱」
        h_raw = float(np.max(y[win]) - np.min(y[win])) if np.count_nonzero(win) >= 3 \
            else float(max(y[i], 0.0))
        fit = _fit_one(x, y, pos0, fit_half)
        if fit is None:
            pos, height, fwhm, eta, r2, ok = _analytic(x, y, pos0, fit_half)
        else:
            pos, height, fwhm, eta, r2, ok = fit
            # 拟合质量闸门：位置跑出窗口 40 %、R² < 0.5 或峰高超过数据极差 2 倍，
            # 都判定为「拟合失效」并退回解析估计——宁可给个粗糙的几何估计，
            # 也不要把一个假峰当真峰交给判定与报告。
            bad = (abs(pos - pos0) > 0.40 * fit_half + 0.02
                   or r2 < 0.5
                   or height > 2.0 * h_raw + 1.0
                   or fwhm <= 0)
            if bad:
                pos, height, fwhm, eta, r2, ok = _analytic(x, y, pos0, fit_half)
        if height <= 0 or fwhm <= 0:
            continue
        # pV 解析积分面积 = 峰高·FWHM·(1.5708η + 1.0645(1−η))
        area = height * fwhm * (1.5708 * eta + 1.06447 * (1.0 - eta))
        out.append(ObservedPeak(two_theta=pos, height=height, area=area,
                                fwhm=fwhm, eta=eta, snr=height / noise,
                                r2=r2, fitted=ok,
                                left=pos - fit_half, right=pos + fit_half))
    # 去重：多起点可能收敛到同一峰（曲线拟合把相邻极大拉到同一位置），
    # 按峰高优先保留，再做位置合并。
    out.sort(key=lambda p: p.height, reverse=True)
    kept: list[ObservedPeak] = []
    for p in out:
        if p.snr < min_snr:
            continue
        if any(abs(p.two_theta - q.two_theta)
               < max(0.03, 0.3 * min(p.fwhm, q.fwhm)) for q in kept):
            continue
        kept.append(p)
    kept.sort(key=lambda p: p.two_theta)
    return kept
