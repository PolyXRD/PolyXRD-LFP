"""Rietveld R 因子（Rwp / Rp / Rexp / χ² / GOF / R_Bragg）。

口径说明（GSAS-II / 通用 Rietveld 口径）
----------------------------------------
- 权重 w_i = 1/σ_i²，σ 缺省按计数统计 σ_i = √max(y_obs_i, 1)。
- **背景计入**（GSAS-II 口径）：Σ 与分母对全部数据点求和，拟合的背景包含在
  y_calc 内。FullProf 等软件另有「背景不计入」变体（先扣背景再算）；本模块
  按传入数组原样计算，便于与其它软件交叉比对。
- Rexp = 100·√((N−P)/Σ w·y_o²)，χ² = (Rwp/Rexp)²，**GOF = Rwp/Rexp = √χ²**。
  GOF 越接近 1 越好；<1 通常表示 σ 高估（权重偏软）而非「拟合更好」。
- R_Bragg（R_B）另行计算，见 :mod:`lfp.core.refine.rbragg`。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RFactors:
    """拟合优度因子（百分数口径）。"""

    rwp: float
    rp: float
    rexp: float
    chi2: float
    rbragg: float | None = None

    @property
    def gof(self) -> float:
        """GOF = Rwp / Rexp（= √χ²）。Rexp 为 0 时返回 inf。"""
        return self.rwp / self.rexp if self.rexp > 0 else float("inf")


def compute_rfactors(yobs, ycalc, *, n_params: int,
                     sigma: np.ndarray | None = None,
                     include_bg: bool = True,
                     rbragg: float | None = None) -> RFactors:
    """计算 Rwp / Rp / Rexp / χ²（GOF 由 :attr:`RFactors.gof` 派生）。

    yobs, ycalc : 等长观测/计算强度数组
    n_params    : 可调参数总数 P（用于 Rexp）
    sigma       : 每点 σ；None -> √max(y_obs, 1)（计数统计）
    include_bg  : 保留参数以对齐家族口径（True 表示背景已含在 y_calc 中）
    rbragg      : 可选的 R_Bragg（百分点），由调用方另行计算后填入
    """
    yo = np.asarray(yobs, dtype=np.float64)
    yc = np.asarray(ycalc, dtype=np.float64)
    if yo.shape != yc.shape or yo.ndim != 1 or yo.size == 0:
        raise ValueError("yobs 与 ycalc 必须是等长的一维非空数组")
    sig = (np.sqrt(np.maximum(yo, 1.0)) if sigma is None
           else np.asarray(sigma, dtype=np.float64))
    w = 1.0 / (sig * sig)

    denom = float(np.sum(w * yo * yo))
    if denom <= 0.0:
        raise ValueError("Σw·y_o² 为 0，无法计算 R 因子")
    diff = yo - yc
    rwp = 100.0 * np.sqrt(float(np.sum(w * diff * diff)) / denom)
    s_obs = float(np.sum(yo))
    if s_obs == 0.0:
        raise ValueError("Σy_o 为 0，无法计算 Rp")
    rp = 100.0 * float(np.sum(np.abs(diff))) / s_obs
    n = yo.size
    p = max(int(n_params), 1)
    rexp = 100.0 * np.sqrt(max(n - p, 1) / denom)
    chi2 = (rwp / rexp) ** 2 if rexp > 0 else float("inf")
    return RFactors(rwp=float(rwp), rp=float(rp), rexp=float(rexp),
                    chi2=float(chi2), rbragg=rbragg)
