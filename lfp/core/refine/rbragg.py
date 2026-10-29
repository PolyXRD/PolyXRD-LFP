"""R_Bragg（R_B）积分强度 R 因子。

定义
----
R_B = Σ_hkl | I_obs,hkl − I_calc,hkl | / Σ_hkl I_obs,hkl × 100%

其中 I_calc,hkl 由结构模型直接给出（S·|F|²·LP·w_α，含择优取向与高角衰减），
I_obs,hkl 需从**重叠的实测谱**中分离。本模块采用 Rietveld 领域通用的
「按计算峰形比例分摊」口径（profile-partitioned integrated intensity）：

1. 对每条计算反射 hkl，按当前峰形参数（FWHM/η/不对称）生成单位峰高的
   pseudo-Voigt 曲线 P_hkl(2θ)，只落在 ±(8·FWHM+0.05°) 窗口内；
2. 对每个数据点，把扣背景后的净强度 (y_obs − y_bg) 按 P_hkl/ΣP 的比例
   分摊给覆盖该点的各反射（重叠峰因此按理论强度比例分配，不重复计数）；
3. 累加得 I_obs,hkl，与 I_calc,hkl 逐条比较。

局限（写进报告与说明书）
------------------------
- 该口径对**强重叠**反射只能按理论比例分摊，因此 R_B 在重叠严重的低角区
  偏「乐观」；Rwp 是逐点残差，不受此影响。两者应结合判读。
- 只统计到数据范围之内、且 I_calc ≥ 最强反射 1% 的反射（弱反射的 I_obs
  基本是噪声，纳入会人为抬高 R_B）；被剔除的条数一并返回，便于复核。
- 若样品含未建模的第二相，其峰不属于任何计算反射，会把净强度留在
  「未分配池」而不计入 R_B —— 因此 R_B 低并不自动代表单相纯样，
  须与 Rwp、残差图共同判读。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from lfp.core.profile.forward import (
    MIN_W,
    ProfileParams,
    _asym_split,
    _window_slice,
    peak_shape,
)
from lfp.core.profile.lattice import ReflectionTable
from lfp.core.profile.shape import _pv_peak

#: 参与 R_B 计算的最弱反射阈值（相对最强反射的积分强度）
WEAK_THRESHOLD = 0.01
#: 峰窗口宽度（FWHM 倍数）+ 固定余量（度），与前向模型一致
WINDOW_HALFWIDTHS = 8.0
WINDOW_PAD = 0.05


@dataclass(frozen=True)
class BraggStat:
    """R_Bragg 结果与其明细。"""

    rb: float
    n_used: int
    n_total: int
    two_theta: np.ndarray
    hkl: np.ndarray
    i_obs: np.ndarray
    i_calc: np.ndarray

    def as_rows(self) -> list[tuple[float, str, float, float]]:
        """(2θ, hkl 字符串, I_obs, I_calc) 明细行（两者均已换算到同一强度口径）。"""
        out = []
        for pos, hk, io, ic in zip(self.two_theta, self.hkl, self.i_obs, self.i_calc):
            out.append((float(pos), f"({int(hk[0])} {int(hk[1])} {int(hk[2])})",
                        float(io), float(ic)))
        return out


def peak_amplitudes(table: ReflectionTable, prm: ProfileParams,
                    scale: float) -> np.ndarray:
    """各反射在前向模型里的实际峰高（与 :mod:`lfp.core.profile.forward` 同口径）。

    分摊重叠峰时必须用**峰高**而不是单位曲线：Kα1/Kα2 双线、以及简并反射
    之间的强度比，全靠振幅体现。用单位峰高会把 2:1 的 Kα 双线摊成 1:1，
    R_B 随之虚假升高（本模块 v1 的实测教训）。
    """
    amps = np.empty(len(table))
    for k, (pos0, inten, d) in enumerate(
            zip(table.two_theta, table.intensity, table.d)):
        pos = float(pos0) + prm.zero
        fwhm, eta = peak_shape(prm, pos)
        fwhm = max(fwhm, MIN_W)
        amp = float(inten) * float(scale)
        if prm.bfactor > 0.0 and d > 0:
            amp *= math.exp(min(50.0, -prm.bfactor / (2.0 * d * d)))
        if prm.integrated:
            amp /= fwhm * (1.06447 + 0.50633 * eta)
        amps[k] = amp
    return amps


def _peak_profiles(grid: np.ndarray, table: ReflectionTable,
                   prm: ProfileParams, amps: np.ndarray):
    """各反射在网格上的 pV 曲线片段（已乘峰高）：(i0, i1, 曲线) 列表与总覆盖。"""
    ptot = np.zeros_like(grid)
    segs: list[tuple[int, int, np.ndarray]] = []
    for k, (pos0, amp) in enumerate(zip(table.two_theta, amps)):
        if amp <= 0:
            continue
        pos = float(pos0) + prm.zero
        fwhm, eta = peak_shape(prm, pos)
        fwhm = max(fwhm, MIN_W)
        fl, fr = _asym_split(pos, fwhm, prm.asym)
        half = WINDOW_HALFWIDTHS * max(fl, fr) + WINDOW_PAD
        i0, i1 = _window_slice(grid, pos, half)
        if i1 <= i0:
            continue
        if fl == fr:
            prof = _pv_peak(grid[i0:i1], pos, fwhm, eta)
        else:
            x = grid[i0:i1] - pos
            left = _pv_peak(x / fl * fwhm + pos, pos, fwhm, eta)
            right = _pv_peak(x / fr * fwhm + pos, pos, fwhm, eta)
            prof = np.where(x < 0, left, right)
        prof = prof * amp
        ptot[i0:i1] += prof
        segs.append((i0, i1, prof))
    return segs, ptot


def bragg_rfactor(grid: np.ndarray, yobs: np.ndarray, ybg: np.ndarray,
                  table: ReflectionTable, prm: ProfileParams,
                  scale: float, threshold: float = WEAK_THRESHOLD) -> BraggStat:
    """计算 R_Bragg。

    grid  : 2θ 网格（与 yobs 等长、升序）
    yobs  : 实测强度
    ybg   : 拟合背景曲线（与 yobs 等长）
    table : 该相的反射表（:func:`lfp.core.profile.forward.reflection_table`）
    prm   : 峰形参数（zero/FWHM/η/asym/bfactor）
    scale : 该相的 Rietveld 标度 S（线性层解出）
    """
    grid = np.asarray(grid, dtype=np.float64)
    net = np.asarray(yobs, dtype=np.float64) - np.asarray(ybg, dtype=np.float64)
    if len(table) == 0:
        return BraggStat(float("nan"), 0, 0, np.zeros(0), np.zeros((0, 3)),
                         np.zeros(0), np.zeros(0))

    icalc = np.asarray(table.intensity, dtype=np.float64) * float(scale)
    if prm.bfactor > 0.0:
        icalc = icalc * np.exp(np.minimum(50.0, -prm.bfactor / (2.0 * table.d ** 2)))

    amps = peak_amplitudes(table, prm, scale)
    segs, ptot = _peak_profiles(grid, table, prm, amps)
    # 分摊：I_obs,hkl = Σ_{窗口内点} net·P_hkl/ΣP
    # 注意：逐点求和得到的是「计数·点」，须乘步长换算成「计数·度」，
    # 才能与 I_calc = S·|F|²·LP（积分强度口径）同量纲比较。
    step = float(np.median(np.diff(grid))) if grid.size > 1 else 1.0
    iobs = np.zeros(len(table))
    for k, (i0, i1, prof) in enumerate(segs):
        denom = ptot[i0:i1]
        w = np.divide(prof, denom, out=np.zeros_like(prof), where=denom > 1e-12)
        iobs[k] = float(np.sum(net[i0:i1] * w)) * step

    imax = float(np.max(icalc)) if icalc.size else 0.0
    use = icalc >= threshold * imax if imax > 0 else np.zeros_like(icalc, bool)
    if not np.any(use):
        return BraggStat(float("nan"), 0, len(table), table.two_theta, table.hkl,
                         iobs, icalc)
    num = float(np.sum(np.abs(iobs[use] - icalc[use])))
    den = float(np.sum(iobs[use]))
    rb = 100.0 * num / den if den > 0 else float("nan")
    return BraggStat(float(rb), int(np.count_nonzero(use)), len(table),
                     table.two_theta[use], table.hkl[use],
                     iobs[use], icalc[use])


def rbragg_verdict(rb: float) -> str:
    """R_B 的经验判读档位（仅用于界面提示，不作合规判据）。

    经验参考（McCusker et al., J. Appl. Cryst. 32 (1999) 36，Rietveld 精修
    报告惯例）：R_B 与 Rwp 同量级或更低属正常；R_B 显著低于 Rwp 常见于
    强重叠谱；R_B 明显高于 Rwp 提示结构模型（原子坐标/占位/Uiso）有系统偏差。
    """
    if not math.isfinite(rb):
        return "unknown"
    if rb <= 5.0:
        return "good"
    if rb <= 10.0:
        return "fair"
    return "poor"
