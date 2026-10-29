"""高层分析入口：判定 → 分阶段精修 → R 因子 → 报告数据。

对外只暴露两件事：
- :func:`identify_pattern`：只做「是不是 LiFePO4」的判定；
- :func:`run_analysis`：判定通过后做完整的 Rietveld 精修并打包结果。

为什么分阶段精修
----------------
一次性放开 10 个非线性参数（零点、峰形、尺寸、应变、不对称、三条边长）
在真实粉末谱上极易发散：晶胞错误会让所有峰位系统性偏离，优化器于是把
峰宽「撑宽」去覆盖错位的峰，最后卡在 Rwp 20%+ 的局部极小。分阶段把
**互相解耦的自由度**依次放开，每阶段都从上一阶段的最优点出发：

    阶段 1  仅线性层（标度 + 背景）           —— 定标度与背景
    阶段 2  零点 + 峰形（尺寸/应变/η/不对称） —— 定峰位零点与峰宽
    阶段 3  + 晶胞 a/b/c                      —— 定晶胞
    阶段 4  用户勾选的全部（U,V,W / B / PO）  —— 精细收敛

最终取「所有阶段中 Rwp 最小」的解，避免后一阶段反而破坏拟合（真实数据
上偶有发生，尤其是 B 因子与仪器宽化同时放开时）。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Callable

import numpy as np

from lfp.core.dtypes import Pattern
from lfp.core.identify import IdentifyResult, identify_lfp
from lfp.i18n.i18n_manager import tr
from lfp.core.profile.cif import CifStructure
from lfp.core.profile.forward import (
    ProfileParams,
    reflection_table,
    scaled_cell,
)
from lfp.core.refine.nonlinear import (
    RefineCanceled,
    RefineConfig,
    RefineResult,
    initial_params,
    refine,
)
from lfp.core.refine.rbragg import BraggStat, bragg_rfactor
from lfp.core.symmetry import SymmetryInfo, describe_structure


class NotLFPError(RuntimeError):
    """判定结果不是 LiFePO4 —— 按软件纪律终止后续精修。"""

    def __init__(self, result: IdentifyResult):
        super().__init__("该谱图未被判定为 LiFePO4")
        self.result = result


@dataclass(frozen=True)
class AnalysisResult:
    """一次完整分析的产物（界面/报告/导出共用）。"""

    identification: IdentifyResult | None
    refinement: RefineResult
    struct: CifStructure             # 精修后的结构（晶胞已缩放）
    cell: tuple[float, float, float, float, float, float]
    volume: float
    symmetry: SymmetryInfo
    size_nm: float | None
    strain: float | None
    bragg: BraggStat | None
    two_theta: np.ndarray
    yobs: np.ndarray
    ycalc: np.ndarray
    diff: np.ndarray
    background: np.ndarray
    elapsed_s: float = 0.0
    stages: list[tuple[str, float]] = field(default_factory=list)

    # -- 派生量 ---------------------------------------------------------
    @property
    def rwp(self) -> float:
        return self.refinement.rf.rwp

    @property
    def gof(self) -> float:
        return self.refinement.rf.gof

    @property
    def rbragg(self) -> float | None:
        return self.bragg.rb if self.bragg is not None else None

    @property
    def cell_scales(self) -> tuple[float, float, float]:
        return self.refinement.cell_scales

    def fwhm_at(self, two_theta: float) -> float | None:
        """该 2θ 处的仪器+样品总 FWHM（度），用于报告与诊断。"""
        from lfp.core.profile.forward import peak_shape
        f, _eta = peak_shape(self.refinement.params, two_theta)
        return float(f)

    def eta_at(self, two_theta: float) -> float:
        from lfp.core.profile.forward import peak_shape
        return float(peak_shape(self.refinement.params, two_theta)[1])

    def reflections(self):
        """精修终态的反射表（含 hkl，供峰表导出）。"""
        return reflection_table(self.struct, self.refinement.params,
                                min(float(self.two_theta[0]), 5.0),
                                float(self.two_theta[-1]))


#: 进度回调签名 cb(message, pct)（pct 为 0..1，None 表示不确定）
ProgressCb = Callable[[str, "float | None"], None] | None


def identify_pattern(pattern: Pattern, struct: CifStructure,
                     prm: ProfileParams | None = None,
                     two_min: float | None = None,
                     two_max: float | None = None) -> IdentifyResult:
    """判定实测谱是否为 LiFePO4（薄封装，便于 GUI 层统一调用）。"""
    prm = prm or initial_params(wavelength=_wavelength_of(pattern))
    return identify_lfp(pattern, struct, prm, two_min, two_max)


def _wavelength_of(pattern: Pattern) -> float:
    meta = getattr(pattern, "meta", {}) or {}
    try:
        return float(meta.get("wavelength", 1.54056))
    except (TypeError, ValueError):
        return 1.54056


def _emit(cb, msg: str, pct: float | None) -> None:
    if cb is None:
        return
    try:
        cb(msg, pct)
    except Exception:
        pass


def _stage_configs(cfg: RefineConfig) -> list[tuple[str, RefineConfig]]:
    """按「由简到繁」给出阶段配置。

    阶段名是 **i18n 键**而不是现成文案：进度消息会直接显示在忙窗与状态栏上，
    写死中文等于让英文界面漏出中文。内核可以引用 ``lfp.i18n.i18n_manager``
    （它不依赖 Qt，是叶子模块），从而保证只维护一份文案。
    """
    base = replace(cfg, refine_zero=False, refine_uvw=False, refine_eta=False,
                   refine_size=False, refine_strain=False, refine_asym=False,
                   refine_bfactor=False, refine_cell=False, refine_po=False)
    shape_only = replace(base, refine_zero=True,
                         refine_size=True, refine_strain=True,
                         refine_eta=(not (cfg.refine_size or cfg.refine_strain)),
                         refine_asym=True)
    with_cell = replace(shape_only, refine_cell=True)
    stages = [("stage.linear", base)]
    if any((cfg.refine_size, cfg.refine_strain, cfg.refine_zero, cfg.refine_asym)):
        stages.append(("stage.shape", shape_only))
    if cfg.refine_cell:
        stages.append(("stage.cell", with_cell))
    full = replace(with_cell,
                   refine_uvw=cfg.refine_uvw,
                   refine_eta=cfg.refine_eta and not (cfg.refine_size or cfg.refine_strain),
                   refine_bfactor=cfg.refine_bfactor,
                   refine_po=cfg.refine_po)
    stages.append(("stage.full", full))
    return stages


def run_analysis(pattern: Pattern, struct: CifStructure, cfg: RefineConfig,
                 prm0: ProfileParams | None = None,
                 *, check_lfp: bool = True, ident: IdentifyResult | None = None,
                 progress_cb: ProgressCb = None,
                 cancel_cb: Callable[[], bool] | None = None
                 ) -> AnalysisResult:
    """判定 + 分阶段 Rietveld 精修 + R 因子，返回完整结果。

    check_lfp : True 时先判定；非 LFP 抛 :class:`NotLFPError`（携带判定证据）。
    ident     : 已有判定结果时直接复用（界面在导入时已判定过，避免重复计算；
                其预拟合晶胞也会作为精修起点）。
    """
    t_start = time.perf_counter()
    tt = np.asarray(pattern.two_theta, dtype=np.float64)
    yobs = np.asarray(pattern.intensity, dtype=np.float64)
    wl = _wavelength_of(pattern)
    prm0 = prm0 or initial_params(wavelength=wl)

    two_min = max(float(tt[0]), 5.0)
    two_max = float(tt[-1])
    cfg = replace(cfg, tmin=two_min, tmax=two_max)

    if ident is not None:
        if not ident.is_lfp and check_lfp:
            raise NotLFPError(ident)
    elif check_lfp:
        _emit(progress_cb, tr("stage.identify"), 0.02)
        ident = identify_lfp(pattern, struct, prm0, two_min, two_max)
        if not ident.is_lfp:
            raise NotLFPError(ident)

    scales0 = (1.0, 1.0, 1.0)
    if ident is not None and ident.cell_scales is not None:
        scales0 = tuple(ident.cell_scales)   # type: ignore[assignment]

    stages = _stage_configs(cfg)
    best: RefineResult | None = None
    prm = prm0
    scales = scales0
    log: list[tuple[str, float]] = []
    for k, (label_key, scfg) in enumerate(stages):
        if cancel_cb is not None and cancel_cb():
            raise RefineCanceled("用户取消")
        pct = 0.05 + 0.85 * (k / max(len(stages), 1))
        label = tr(label_key)
        _emit(progress_cb,
              tr("stage.progress", i=k + 1, n=len(stages), label=label), pct)
        res = refine(struct, pattern, prm, scfg, scales0=scales)
        log.append((label, float(res.rf.rwp)))
        # 采用「更低 Rwp」的解；同分保留后一阶段（自由度更全，便于后续）
        if best is None or res.rf.rwp <= best.rf.rwp + 1e-9:
            best = res
            prm = res.params
            scales = tuple(res.cell_scales)  # type: ignore[assignment]
    if best is None:            # 理论上不可达（阶段列表非空）
        raise RuntimeError("精修未产生任何结果")
    _emit(progress_cb, tr("stage.rbragg"), 0.93)

    final_struct = scaled_cell(struct, *best.cell_scales)
    table = reflection_table(final_struct, best.params,
                             min(two_min, 5.0), two_max)
    bragg = bragg_rfactor(tt, yobs, best.bg_curve, table, best.params,
                          best.scale)
    rf = replace(best.rf, rbragg=bragg.rb)
    best = replace(best, rf=rf)

    cell = tuple(float(x) for x in final_struct.cell)
    elapsed = time.perf_counter() - t_start
    _emit(progress_cb, tr("stage.done"), 1.0)
    return AnalysisResult(
        identification=ident, refinement=best, struct=final_struct, cell=cell,
        volume=float(final_struct.volume), symmetry=describe_structure(final_struct),
        size_nm=(best.params.size_nm if best.params.size_nm > 0 else None),
        strain=(best.params.strain if best.params.strain > 0 else None),
        bragg=bragg, two_theta=tt, yobs=yobs, ycalc=best.ycalc,
        diff=yobs - best.ycalc, background=best.bg_curve, elapsed_s=elapsed,
        stages=log)
