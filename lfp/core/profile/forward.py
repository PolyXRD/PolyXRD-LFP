"""Rietveld 前向模型（LiFePO4 版）—— 单相计算谱。

与家族 RutAna 的 ``compute_phase_profile`` 同一数学骨架::

    y(2θ) = Σ_hkl |F|²·LP·Ω(2θ − 2θ_hkl − zero)
    Ω = pseudo-Voigt(FWHM, η)

本工具的**三处扩展**（均为 LFP 专用需求所必需）：

1. **晶粒尺寸与微应变**（Scherrer / Wilson，Lorentzian 宽化分量）
   β_L(2θ) = K·λ / (D·cosθ) + 4·ε·tanθ          （弧度，转度后使用）
   - 尺寸项 K·λ/(D cosθ)：K = 0.9（Scherrer 常数），D 为沿散射矢量的
     体积平均相干衍射畴尺寸；这是 Rietveld 中「晶粒尺寸」的标准口径，
     与谢乐公式 D = Kλ/(β cosθ) 完全一致（β 取 Lorentzian 积分宽度）。
   - 应变项 4ε tanθ：Wilson 微应变展宽，ε = Δd/d 的均方根。
   二者与仪器高斯分量（Caglioti U,V,W）按 Thompson–Cox–Hastings 公式
   合成 Voigt 的 FWHM 与 η：::

       FWHM⁵ = G⁵ + 2.69269G⁴L + 2.42843G³L² + 4.47163G²L³
               + 0.07842GL⁴ + L⁵
       η = 1.36603q − 0.47719q² + 0.11116q³,  q = L/FWHM

   启用尺寸/应变后 η 由 q 决定（不再作为自由参数，避免与尺寸项简并）。

2. **正交晶系三轴独立缩放**由调用方通过缩放后的 CifStructure 传入
   （见 :func:`scaled_cell`），前向模型本身只吃晶胞。

3. **Kα1/Kα2 双线**、**March–Dollase 择优取向**、**低角不对称**、
   **经验高角衰减** 沿用家族口径（默认行为与原实现一致）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from lfp.core.profile.cif import CifStructure
from lfp.core.profile.lattice import ReflectionTable, reflections
from lfp.core.profile.shape import (
    DEFAULT_WAVELENGTH,
    _pv_peak,
    march_dollase_weight,
    resolve_wavelengths,
)

#: FWHM 下限保护（防止 Caglioti 退化导致除零）
MIN_W = 1e-4
#: 峰窗口宽度（以 FWHM 为单位）+ 固定余量（度）
WINDOW_HALFWIDTHS = 8.0
WINDOW_PAD = 0.05
#: Scherrer 常数（FWHM 口径，球形/等轴晶粒常用 0.9）
SCHERRER_K = 0.9
#: 弧度 → 度
RAD2DEG = 180.0 / math.pi


@dataclass(frozen=True)
class ProfileParams:
    """峰形参数集（Rietveld 非线性参数）。

    zero      : 零点偏移 (度)，直接加在峰位上
    U, V, W   : Caglioti 仪器 FWHM² = U·tan²θ + V·tanθ + W（度²，高斯分量）
    eta       : pseudo-Voigt Lorentz 占比（未启用尺寸/应变时有效）
    size_nm   : 体积平均晶粒尺寸 (nm)；0 = 不启用尺寸宽化
    strain    : 微应变 ε = Δd/d（无量纲）；0 = 不启用应变宽化
    anode     : 阳极靶（启用 Kα1/α2 双线）；None = 单色光
    ka_ratio  : Iα2/Iα1
    po_r      : {相名: (h,k,l,r)} March–Dollase 择优取向
    wavelength: 基准波长 (Å)，anode=None 时使用
    asym      : 低角不对称度（s = asym/tanθ，左右 FWHM 分别 ×(1±s)）
    bfactor   : 经验高角衰减 exp(−B/2d²)
    integrated: True = 峰高按积分强度归一化（Rietveld 标度 S 的标准口径）
    """

    zero: float = 0.0
    U: float = 0.0
    V: float = 0.0
    W: float = 0.02
    eta: float = 0.5
    size_nm: float = 0.0
    strain: float = 0.0
    anode: str | None = "Cu"
    ka_ratio: float = 0.5
    po_r: dict | None = None
    wavelength: float = DEFAULT_WAVELENGTH
    asym: float = 0.0
    bfactor: float = 0.0
    integrated: bool = True
    scherrer_k: float = SCHERRER_K

    # ------------------------------------------------------------------ #
    @property
    def size_model(self) -> bool:
        """是否启用了尺寸/应变宽化模型。"""
        return self.size_nm > 0.0 or self.strain > 0.0

    def with_changes(self, **kw) -> "ProfileParams":
        """返回替换若干字段后的新实例（dataclass frozen 的便捷写法）。"""
        return replace(self, **kw)


def scaled_cell(struct: CifStructure, fa: float = 1.0, fb: float = 1.0,
                fc: float = 1.0) -> CifStructure:
    """按比例缩放 a/b/c（角度不变，分数坐标不变）-> 新 CifStructure。

    正交晶系精修中这是「精修晶胞」的标准做法：只改边长、不改原子分数坐标，
    因此峰位随晶胞线性移动，而结构因子只轻微变化（s 随 2θ 固定窗口重算）。
    """
    if abs(fa - 1.0) < 1e-12 and abs(fb - 1.0) < 1e-12 and abs(fc - 1.0) < 1e-12:
        return struct
    a, b, c, al, be, ga = struct.cell
    out = CifStructure(struct.name, (a * fa, b * fb, c * fc, al, be, ga),
                       struct.atoms)
    out.n_asym, out.n_sym_ops = struct.n_asym, struct.n_sym_ops
    out.space_group = struct.space_group
    out.space_group_number = struct.space_group_number
    out.formula, out.formula_weight = struct.formula, struct.formula_weight
    out.z_formula, out.mineral, out.source = (struct.z_formula, struct.mineral,
                                             struct.source)
    return out


def caglioti_fwhm(U: float, V: float, W: float, two_theta: float) -> float:
    """Caglioti 高斯分量 FWHM (度)：FWHM² = U·tan²θ + V·tanθ + W，θ = 2θ/2。"""
    t = math.tan(math.radians(max(two_theta, 1e-6)) / 2.0)
    return math.sqrt(max(U * t * t + V * t + W, 1e-6))


def lorentzian_fwhm(size_nm: float, strain: float, two_theta: float,
                    wavelength: float, k: float = SCHERRER_K) -> float:
    """尺寸 + 应变贡献的 Lorentzian 分量 FWHM (度)。

    β_L = Kλ/(D cosθ) + 4ε tanθ （弧度）→ ×180/π 转为度。
    size_nm ≤ 0 时尺寸项为 0；strain ≤ 0 时应变项为 0。
    """
    if size_nm <= 0.0 and strain <= 0.0:
        return 0.0
    th = math.radians(max(two_theta, 1e-6) / 2.0)
    beta = 0.0
    if size_nm > 0.0:
        d_ang = size_nm * 10.0                      # nm → Å
        beta += k * wavelength / (d_ang * max(math.cos(th), 1e-6))
    if strain > 0.0:
        beta += 4.0 * strain * math.tan(th)
    return beta * RAD2DEG


def voigt_mix(gsigma: float, lwidth: float) -> tuple[float, float]:
    """TCH 公式：由高斯/洛伦兹分量 FWHM 合成 (FWHM, η)。"""
    g = max(gsigma, 0.0)
    l = max(lwidth, 0.0)
    if l <= 0.0:
        return max(g, MIN_W), 0.0
    if g <= 0.0:
        return max(l, MIN_W), 1.0
    f5 = (g ** 5 + 2.69269 * g ** 4 * l + 2.42843 * g ** 3 * l ** 2
          + 4.47163 * g ** 2 * l ** 3 + 0.07842 * g * l ** 4 + l ** 5)
    fwhm = max(f5 ** 0.2, MIN_W)
    q = min(max(l / fwhm, 0.0), 1.0)
    eta = 1.36603 * q - 0.47719 * q * q + 0.11116 * q ** 3
    return fwhm, min(max(eta, 0.0), 1.0)


def peak_shape(prm: ProfileParams, two_theta: float) -> tuple[float, float]:
    """该峰位处的 (FWHM, η)。启用尺寸/应变时 η 由 Voigt 混合决定。"""
    g = caglioti_fwhm(prm.U, prm.V, max(prm.W, MIN_W), two_theta)
    if not prm.size_model:
        return max(g, MIN_W), prm.eta
    l = lorentzian_fwhm(prm.size_nm, prm.strain, two_theta,
                        prm.wavelength, prm.scherrer_k)
    return voigt_mix(g, l)


def _window_slice(grid: np.ndarray, pos: float, half: float) -> tuple[int, int]:
    i0 = int(np.searchsorted(grid, pos - half, side="left"))
    i1 = int(np.searchsorted(grid, pos + half, side="right"))
    return max(i0, 0), min(i1, grid.size)


def _asym_split(pos_shifted: float, fwhm: float, asym: float) -> tuple[float, float]:
    """不对称峰形的左右 FWHM：s = asym/tanθ，左尾 ×(1+s)、右尾 ×(1−s)。"""
    if asym == 0.0:
        return fwhm, fwhm
    th = math.radians(max(pos_shifted, 1e-3) / 2.0)
    s = max(-0.85, min(0.85, asym / max(math.tan(th), 1e-3)))
    return fwhm * (1.0 + s), fwhm * (1.0 - s)


def _add_peak(prof: np.ndarray, grid: np.ndarray, pos: float, height: float,
              fwhm: float, eta: float, asym: float, bfactor: float,
              d: float | None, integrated: bool) -> None:
    """把单个峰只累加到 ±(8·FWHM + 0.05°) 窗口内。"""
    if bfactor > 0.0 and d is not None and d > 0:
        height = height * math.exp(min(50.0, -bfactor / (2.0 * d * d)))
    if integrated:
        height = height / max(fwhm * (1.06447 + 0.50633 * eta), 1e-12)
    fl, fr = _asym_split(pos, fwhm, asym)
    half = WINDOW_HALFWIDTHS * max(fl, fr) + WINDOW_PAD
    i0, i1 = _window_slice(grid, pos, half)
    if i1 <= i0:
        return
    if fl == fr:
        prof[i0:i1] += height * _pv_peak(grid[i0:i1], pos, fwhm, eta)
    else:
        x = grid[i0:i1] - pos
        left = height * _pv_peak(x / fl * fwhm + pos, pos, fwhm, eta)
        right = height * _pv_peak(x / fr * fwhm + pos, pos, fwhm, eta)
        prof[i0:i1] += np.where(x < 0, left, right)


def phase_profile(struct: CifStructure, grid: np.ndarray, prm: ProfileParams,
                  tmin: float = 5.0, tmax: float = 120.0,
                  table: ReflectionTable | None = None) -> np.ndarray:
    """单相计算谱（无归一化、无背景、无噪声）。

    struct : 该相 CifStructure（晶胞可已被缩放）
    grid   : 2θ 网格 (度, 升序)
    prm    : 峰形参数
    table  : 预计算的反射表（缺省按 prm 的波长/双线/PO 现算）
    """
    grid = np.asarray(grid, dtype=np.float64)
    if table is None:
        comps = resolve_wavelengths(prm.wavelength, prm.anode, prm.ka_ratio)
        po = None
        if prm.po_r:
            entry = prm.po_r.get(struct.name)
            if entry is not None:
                po = (entry[0], entry[1], entry[2], float(entry[3]))
        table = reflections(struct, prm.wavelength, tmin, tmax, comps, po)
    prof = np.zeros_like(grid)
    if len(table) == 0:
        return prof
    pos_all = table.two_theta + prm.zero
    for pos, height, d in zip(pos_all, table.intensity, table.d):
        if height <= 0.0:
            continue
        fwhm, eta = peak_shape(prm, pos)
        _add_peak(prof, grid, pos, height, max(fwhm, MIN_W), eta,
                  prm.asym, prm.bfactor, d, prm.integrated)
    return prof


def reflection_table(struct: CifStructure, prm: ProfileParams,
                     tmin: float = 5.0, tmax: float = 120.0) -> ReflectionTable:
    """按 prm 的波长/双线/择优取向计算反射表（供精修与 R_Bragg 复用）。"""
    comps = resolve_wavelengths(prm.wavelength, prm.anode, prm.ka_ratio)
    po = None
    if prm.po_r:
        entry = prm.po_r.get(struct.name)
        if entry is not None:
            po = (entry[0], entry[1], entry[2], float(entry[3]))
    return reflections(struct, prm.wavelength, tmin, tmax, comps, po)


def strongest_peak_position(struct: CifStructure, prm: ProfileParams,
                            tmin: float = 5.0, tmax: float = 120.0) -> float:
    """最强衍射峰的 2θ（不含 zero）。"""
    table = reflection_table(struct, prm, tmin, tmax)
    if len(table) == 0:
        raise ValueError(f"{struct.name}: 窗口内无衍射峰")
    return float(table.two_theta[table.strongest()])


def scherrer_size(beta_deg: float, two_theta: float,
                  wavelength: float, k: float = SCHERRER_K) -> float:
    """谢乐公式：由纯物理宽化 β(度, FWHM) 求晶粒尺寸 (nm)。

    D = K·λ / (β_rad·cosθ)。独立于前向模型，供「寻峰 + 谢乐」快速估算路径使用。
    """
    beta = math.radians(max(beta_deg, 1e-9))
    th = math.radians(two_theta / 2.0)
    return k * wavelength / (beta * max(math.cos(th), 1e-6)) / 10.0
