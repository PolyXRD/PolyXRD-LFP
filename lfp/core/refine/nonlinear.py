"""Rietveld 精修内核（变量投影最小二乘）。

技术路线（与家族 RutAna 的 B 法同源，按 LFP 需求扩展）
----------------------------------------------------
1. **变量投影**：标度 S 与背景系数是线性参数，每次迭代内用加权 lstsq 解析
   求解（:mod:`lfp.core.refine.linear`），非线性优化只面对峰形与晶胞参数，
   条件数大幅改善。
2. **非线性优化**：默认 scipy ``least_squares(method="trf")``（真实粉末谱上
   比自写 LM 稳，能守住 Caglioti 的正定内点）；scipy 不可用时回落到自写
   LM（:mod:`lfp.core.refine.lm`）。
3. **正交晶系三轴晶胞**：a/b/c 各自按比例缩放（角度固定），缩放后重建
   CifStructure，峰位随晶胞线性移动、结构因子按新的 s 重算。
4. **晶粒尺寸 / 微应变**：尺寸与应变以 Lorentzian 宽化进入 Voigt（TCH 合成），
   尺寸 D 直接作为被精修参数，收敛值即报告值（口径见 forward 模块文档）。
5. **多起点重启**：Caglioti 在 U=V=0 处有吸引子（家族 v1.0.0 实测），
   若优化落在 U→0 / W 触界或 Rwp 异常高，则用若干确定性起点重试并取最优。

参数向量顺序（严格固定，pack/unpack/bounds 三处必须一致）::

    [zero] [U V W] [eta] [size_nm] [strain] [asym] [bfactor] [fa fb fc] [po r...]
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from lfp.core.dtypes import Pattern
from lfp.i18n.i18n_manager import tr
from lfp.core.profile.cif import CifStructure
from lfp.core.profile.forward import (
    MIN_W,
    ProfileParams,
    phase_profile,
    reflection_table,
    scaled_cell,
)
from lfp.core.refine.linear import background_basis, solve_linear_detail
from lfp.core.refine.lm import lm_minimize
from lfp.core.refine.rfactors import RFactors, compute_rfactors

# ---------------------------------------------------------------- 参数边界
ZERO_BOUNDS = (-0.5, 0.5)
U_BOUNDS = (0.0, 5.0)
V_BOUNDS = (-0.5, 0.5)
ETA_BOUNDS = (0.05, 1.0)
#: 晶粒尺寸 (nm)：下限 0.5 nm（约 2 个晶胞，再小则模型无意义）
SIZE_BOUNDS = (0.5, 5000.0)
#: 微应变 ε = Δd/d：上限 5%（更大的「微」应变已超出 Rietveld 适用范围）
STRAIN_BOUNDS = (0.0, 0.05)
ASYM_BOUNDS = (-0.05, 0.30)
BFACTOR_BOUNDS = (0.0, 6.0)
#: 晶胞比例边界 ±3%（覆盖 FePO4/LiFePO4 混相位移与热膨胀量级）
CELL_BOUNDS = (0.97, 1.03)
PO_BOUNDS = (0.2, 5.0)

#: Rwp 超过此值视为「明显未收敛」，触发多起点重启
RESTART_RWP_TRIGGER = 25.0

#: 内置 LFP 的惯习面择优取向默认方向 (h k l)：橄榄石型板状晶常沿 (020) 取向
DEFAULT_PO_HKL = {"lfp": (0, 2, 0)}


class RefineCanceled(RuntimeError):
    """用户在精修过程中请求取消。"""


@dataclass(frozen=True)
class RefineConfig:
    """精修开关与数值配置（GUI 复选项直接映射到这里的布尔字段）。"""

    refine_zero: bool = True
    refine_uvw: bool = False        # 仪器 Caglioti（需标样标定，默认不放开）
    refine_eta: bool = True         # 未启用尺寸模型时才有意义
    refine_size: bool = True        # 晶粒尺寸 D
    refine_strain: bool = True      # 微应变 ε
    refine_asym: bool = True        # 低角不对称
    refine_bfactor: bool = False    # 经验高角衰减（异常时再放开）
    refine_cell: bool = True        # a / b / c
    refine_po: bool = False         # March–Dollase 择优取向
    n_bg: int = 6
    bg_mode: str = "cheb"           # "cheb" | "tent"
    tmin: float = 5.0
    tmax: float = 120.0
    backend: str = "scipy"          # "scipy" | "lm"
    max_nfev: int = 4000
    max_iter: int = 40
    sigma: np.ndarray | None = None
    progress_cb: object = None      # callable(msg: str, pct: float | None)
    on_iter: object = None          # callable(gen: int, rwp: float)
    cancel_cb: object = None        # callable() -> bool


@dataclass(frozen=True)
class RefineResult:
    """精修结果（不含晶胞的绝对数值——那由调用方按 scales 计算后报告）。"""

    params: ProfileParams
    scale: float
    bg_coeffs: np.ndarray
    bg_curve: np.ndarray
    ycalc: np.ndarray
    rf: RFactors
    success: bool
    history: list[float] = field(default_factory=list)
    cell_scales: tuple[float, float, float] = (1.0, 1.0, 1.0)
    iters: int = 0
    restarted: bool = False
    message: str = ""
    n_params: int = 0


# --------------------------------------------------------------------------- #
# 打包 / 解包 / 边界
# --------------------------------------------------------------------------- #
def _use_size_model(cfg: RefineConfig) -> bool:
    return bool(cfg.refine_size or cfg.refine_strain)


def _pack(prm: ProfileParams, cfg: RefineConfig,
          scales: tuple[float, float, float]) -> np.ndarray:
    x: list[float] = []
    if cfg.refine_zero:
        x.append(prm.zero)
    if cfg.refine_uvw:
        x.extend([prm.U, prm.V, prm.W])
    if cfg.refine_eta and not _use_size_model(cfg):
        x.append(prm.eta)
    if cfg.refine_size:
        x.append(prm.size_nm if prm.size_nm > 0 else 100.0)
    if cfg.refine_strain:
        x.append(max(prm.strain, 0.0))
    if cfg.refine_asym:
        x.append(prm.asym)
    if cfg.refine_bfactor:
        x.append(prm.bfactor)
    if cfg.refine_cell:
        x.extend(list(scales))
    if cfg.refine_po and prm.po_r:
        for name in sorted(prm.po_r):
            x.append(float(prm.po_r[name][3]))
    return np.array(x, dtype=np.float64) if x else np.zeros(0)


def _unpack(x: np.ndarray, base: ProfileParams, cfg: RefineConfig,
            scales0: tuple[float, float, float]
            ) -> tuple[ProfileParams, tuple[float, float, float]]:
    i = 0
    zero, U, V, W, eta = base.zero, base.U, base.V, base.W, base.eta
    size, strain = base.size_nm, base.strain
    asym, bfactor = base.asym, base.bfactor
    if cfg.refine_zero:
        zero = float(x[i]); i += 1
    if cfg.refine_uvw:
        U, V, W = float(x[i]), float(x[i + 1]), float(x[i + 2]); i += 3
    if cfg.refine_eta and not _use_size_model(cfg):
        eta = float(x[i]); i += 1
    if cfg.refine_size:
        size = float(x[i]); i += 1
    if cfg.refine_strain:
        strain = float(x[i]); i += 1
    if cfg.refine_asym:
        asym = float(x[i]); i += 1
    if cfg.refine_bfactor:
        bfactor = float(x[i]); i += 1
    scales = list(scales0)
    if cfg.refine_cell:
        scales = [float(x[i]), float(x[i + 1]), float(x[i + 2])]; i += 3
    po_r = base.po_r
    if cfg.refine_po and base.po_r:
        po_r = {}
        for name in sorted(base.po_r):
            e = base.po_r[name]
            po_r[name] = (e[0], e[1], e[2], float(x[i])); i += 1
    prm = ProfileParams(zero=zero, U=U, V=V, W=max(W, MIN_W), eta=eta,
                        size_nm=max(size, 0.0), strain=max(strain, 0.0),
                        anode=base.anode, ka_ratio=base.ka_ratio, po_r=po_r,
                        wavelength=base.wavelength, asym=asym, bfactor=bfactor,
                        integrated=base.integrated, scherrer_k=base.scherrer_k)
    return prm, (scales[0], scales[1], scales[2])


def _bounds(cfg: RefineConfig) -> tuple[np.ndarray, np.ndarray]:
    lo: list[float] = []
    hi: list[float] = []
    if cfg.refine_zero:
        lo.append(ZERO_BOUNDS[0]); hi.append(ZERO_BOUNDS[1])
    if cfg.refine_uvw:
        lo.extend([U_BOUNDS[0], V_BOUNDS[0], MIN_W])
        hi.extend([U_BOUNDS[1], V_BOUNDS[1], U_BOUNDS[1]])
    if cfg.refine_eta and not _use_size_model(cfg):
        lo.append(ETA_BOUNDS[0]); hi.append(ETA_BOUNDS[1])
    if cfg.refine_size:
        lo.append(SIZE_BOUNDS[0]); hi.append(SIZE_BOUNDS[1])
    if cfg.refine_strain:
        lo.append(STRAIN_BOUNDS[0]); hi.append(STRAIN_BOUNDS[1])
    if cfg.refine_asym:
        lo.append(ASYM_BOUNDS[0]); hi.append(ASYM_BOUNDS[1])
    if cfg.refine_bfactor:
        lo.append(BFACTOR_BOUNDS[0]); hi.append(BFACTOR_BOUNDS[1])
    if cfg.refine_cell:
        lo.extend([CELL_BOUNDS[0]] * 3); hi.extend([CELL_BOUNDS[1]] * 3)
    return np.array(lo, dtype=np.float64), np.array(hi, dtype=np.float64)


# --------------------------------------------------------------------------- #
# 残差
# --------------------------------------------------------------------------- #
class _Model:
    """一次精修会话的模型缓存：晶胞缩放 -> 反射表 -> 计算谱。"""

    def __init__(self, struct: CifStructure, pat: Pattern, base: ProfileParams,
                 cfg: RefineConfig,
                 scales0: tuple[float, float, float] = (1.0, 1.0, 1.0)):
        self.struct = struct
        self.pat = pat
        self.base = base
        self.cfg = cfg
        self.scales0 = tuple(float(s) for s in scales0)
        self.history: list[float] = []
        self.gen = 0
        self.tt = np.asarray(pat.two_theta, dtype=np.float64)
        yo = np.asarray(pat.intensity, dtype=np.float64)
        # ---- 强度归一化：最强峰 → 1000 计数的工作尺度 ----
        # 不同来源的谱强度量级差异极大（真实仪器谱 ~1e3 计数，某些软件导出的
        # 未归一化面积强度可达 1e9）。归一化把最小二乘搬到良态尺度上，避免
        # 大数相乘时的精度损失。**R 因子的语义必须保持**：σ 同步除以同一因子，
        # 于是残差 (Δy/k)/(σ/k) = Δy/σ 与 k 无关，Rwp/Rexp/GOF 与归一化前完全
        # 一致（GOF 仍等于 √χ²_ν）。若改成 σ=√(y/k) 会让 Rexp 随 k 漂移，
        # GOF 变成「和数据量级有关」的数——那是错的。
        peak = float(np.max(yo)) if yo.size else 0.0
        self.norm = (peak / 1000.0) if peak > 0 else 1.0
        self.yo = yo / self.norm
        self.sigma = (np.asarray(cfg.sigma, dtype=np.float64) / self.norm
                      if cfg.sigma is not None
                      else np.sqrt(np.maximum(yo, 1.0)) / self.norm)
        self._tables: dict[tuple, object] = {}

    # -- 缓存 ------------------------------------------------------------
    def table(self, prm: ProfileParams, scales) -> object:
        key = (round(scales[0], 8), round(scales[1], 8), round(scales[2], 8),
               prm.anode, round(prm.ka_ratio, 6), round(prm.wavelength, 6),
               _po_key(prm))
        hit = self._tables.get(key)
        if hit is None:
            st = scaled_cell(self.struct, *scales)
            hit = reflection_table(st, prm, self.cfg.tmin, self.cfg.tmax)
            if len(self._tables) > 64:
                self._tables.clear()
            self._tables[key] = hit
        return hit

    def profile(self, prm: ProfileParams, scales) -> np.ndarray:
        st = scaled_cell(self.struct, *scales)
        return phase_profile(st, self.tt, prm, self.cfg.tmin, self.cfg.tmax,
                             table=self.table(prm, scales))

    # -- 残差 ------------------------------------------------------------
    def residual(self, x: np.ndarray) -> np.ndarray:
        cfg = self.cfg
        if cfg.cancel_cb is not None:
            try:
                if cfg.cancel_cb():
                    raise RefineCanceled("用户取消")
            except RefineCanceled:
                raise
            except Exception:
                pass
        prm, scales = _unpack(x, self.base, cfg, self.scales0)
        basis = self.profile(prm, scales)[None, :]
        _coef, ycalc, _drop = solve_linear_detail(
            basis, self.tt, self.yo, self.sigma, cfg.n_bg, cfg.bg_mode)
        rwp = compute_rfactors(
            self.yo, ycalc,
            n_params=int(x.size) + 1 + cfg.n_bg).rwp
        self.history.append(rwp)
        self.gen += 1
        if cfg.on_iter is not None:
            try:
                cfg.on_iter(self.gen, rwp)
            except Exception:
                pass
        if cfg.progress_cb is not None and self.gen % 25 == 0:
            try:
                cfg.progress_cb(tr("stage.eval", n=self.gen, rwp=rwp), None)
            except Exception:
                pass
        return (self.yo - ycalc) / self.sigma


def _po_key(prm: ProfileParams):
    """择优取向缓存键（h,k,l 固定，只允许 r 变化时复用反射表）。"""
    if not prm.po_r:
        return None
    return tuple((k, v[0], v[1], v[2]) for k, v in sorted(prm.po_r.items()))


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #
def refine(struct: CifStructure, pat: Pattern, prm0: ProfileParams,
           cfg: RefineConfig,
           scales0: tuple[float, float, float] = (1.0, 1.0, 1.0)) -> RefineResult:
    """单相 Rietveld 精修。

    struct  : 结构模型（起始晶胞）
    pat     : 实测谱（2θ, 强度）
    prm0    : 峰形初值（size_nm=0 时自动取 100 nm 起点；strain 取 0）
    cfg     : 精修开关
    scales0 : 晶胞起始比例（通常 (1,1,1)；可给「按已知峰位预缩放」的结果）
    """
    if cfg.progress_cb is not None:
        try:
            cfg.progress_cb(tr("stage.build"), 0.0)
        except Exception:
            pass
    model = _Model(struct, pat, prm0, cfg, scales0)

    x0 = _pack(prm0, cfg, model.scales0)
    if cfg.refine_po and prm0.po_r:
        n_po = len(prm0.po_r)
    else:
        n_po = 0
    lo, hi = _bounds(cfg)
    if n_po:
        lo = np.concatenate([lo, np.full(n_po, PO_BOUNDS[0])])
        hi = np.concatenate([hi, np.full(n_po, PO_BOUNDS[1])])
    if x0.size:
        x0 = np.clip(x0, lo, hi)

    restarted = False
    if x0.size == 0:
        ycalc = model.profile(prm0, model.scales0)
        coef, ycalc, _ = solve_linear_detail(
            ycalc[None, :], model.tt, model.yo, model.sigma,
            cfg.n_bg, cfg.bg_mode)
        best_x, best_cost, success = x0, 0.0, True
        message = "无可精修的非线性参数（仅解线性层）"
    else:
        best_x, best_cost, success, message = _optimize(model, x0, lo, hi, cfg)
        prm_best, sc_best = _unpack(best_x, prm0, cfg, model.scales0)
        stuck = (not success) or prm_best.W <= 2.0 * MIN_W
        if not stuck:
            model.residual(best_x)
            stuck = model.history[-1] > RESTART_RWP_TRIGGER
        if stuck:
            restarted = True
            for cand in _restart_params(prm_best, cfg):
                x_try = _pack(cand, cfg, sc_best)
                if x_try.size != x0.size:
                    continue
                x_try = np.clip(x_try, lo, hi)
                x2, c2, ok2, msg2 = _optimize(model, x_try, lo, hi, cfg)
                if c2 < best_cost:
                    best_x, best_cost, success = x2, c2, ok2
                    message = msg2
                    prm_best, sc_best = _unpack(best_x, prm0, cfg, model.scales0)

    # ---- 终态：解析线性层 + 全因子
    prm, scales = _unpack(best_x, prm0, cfg, model.scales0)
    if cfg.progress_cb is not None:
        try:
            cfg.progress_cb(tr("stage.final"), 0.95)
        except Exception:
            pass
    basis = model.profile(prm, scales)[None, :]
    coef, ycalc, _dropped = solve_linear_detail(
        basis, model.tt, model.yo, model.sigma, cfg.n_bg, cfg.bg_mode)
    bg_basis = background_basis(model.tt, cfg.n_bg, cfg.bg_mode)
    bg_curve = bg_basis @ coef[1:]
    n_params = int(best_x.size) + 1 + int(cfg.n_bg)
    rf = compute_rfactors(model.yo, ycalc, n_params=n_params,
                          sigma=model.sigma)
    # 还原到用户数据的原始强度单位（R 因子是比值，不受影响）
    k = model.norm
    return RefineResult(params=prm, scale=float(coef[0]) * k,
                        bg_coeffs=coef[1:].copy() * k,
                        bg_curve=bg_curve * k, ycalc=ycalc * k, rf=rf,
                        success=success,
                        history=list(model.history), cell_scales=scales,
                        iters=model.gen, restarted=restarted, message=message,
                        n_params=n_params)


def _optimize(model: _Model, x0: np.ndarray, lo: np.ndarray, hi: np.ndarray,
              cfg: RefineConfig):
    """跑一次优化，返回 (x, cost, success, message)。"""
    use_scipy = False
    if cfg.backend == "scipy":
        try:
            from scipy.optimize import least_squares  # noqa: F401
            use_scipy = True
        except Exception:
            use_scipy = False
    if use_scipy:
        from scipy.optimize import least_squares
        sr = least_squares(model.residual, x0, bounds=(lo, hi), method="trf",
                           x_scale="jac", max_nfev=int(cfg.max_nfev))
        return sr.x, float(sr.cost), bool(sr.success), str(sr.message)
    lm = lm_minimize(model.residual, x0, bounds=(lo, hi),
                     max_iter=int(cfg.max_iter))
    return lm.x, lm.cost, bool(lm.success), lm.message


def _restart_params(prm: ProfileParams, cfg: RefineConfig):
    """确定性修复起点：把 Caglioti 与尺寸项放到「内力可降」的位置。"""
    pts = []
    for u, w, size in ((0.01, 0.01, prm.size_nm or 100.0),
                       (0.03, 0.02, prm.size_nm or 60.0),
                       (0.0, 0.02, prm.size_nm or 200.0)):
        pts.append(replace(prm, U=u, V=0.0, W=w,
                           size_nm=(size if cfg.refine_size else prm.size_nm)))
    return pts


def initial_params(wavelength: float = 1.54056, anode: str | None = "Cu",
                   ka_ratio: float = 0.5) -> ProfileParams:
    """给出稳健的精修初值（经验值，来自家族真实数据调优与 LFP 实测谱）。

    W 取 0.008 deg²（约 0.09° 仪器 FWHM，常见粉末衍射仪量级），
    U/V 保守取 0（不放开精修时固定为 0），尺寸初值 100 nm，应变 0。
    """
    return ProfileParams(zero=0.0, U=0.0, V=0.0, W=0.008, eta=0.6,
                         size_nm=100.0, strain=0.0, anode=anode,
                         ka_ratio=ka_ratio, wavelength=wavelength)
