"""结果导出：CSV（汇总 / 拟合谱 / 反射表 / 寻峰）、HTML 报告、PNG。

CSV 一律 UTF-8 **带 BOM**（``utf-8-sig``），Excel 双击直接正确显示中文；
数值不做四舍五入以外的格式化（保留足够位数供复核）。
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

import numpy as np

from lfp.i18n import current_language, tr

CSV_ENCODING = "utf-8-sig"


def _write_csv(path: str | Path, rows: Sequence[Sequence[object]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding=CSV_ENCODING) as fh:
        writer = csv.writer(fh)
        for row in rows:
            writer.writerow(row)


def summary_rows(result, sample: str, file_name: str, meta: dict | None = None
                 ) -> list[tuple[str, str]]:
    """一次分析的关键结果（报告/CSV 共用，顺序即阅读顺序）。"""
    meta = meta or {}
    a, b, c, al, be, ga = result.cell
    sym = result.symmetry
    rf = result.refinement.rf
    ident = result.identification
    rows: list[tuple[str, str]] = [
        (tr("csv.sample"), sample),
        (tr("csv.file"), file_name),
        (tr("csv.anode"), str(meta.get("anode") or "—")),
        (tr("csv.wavelength"), f"{meta.get('wavelength', 0):.5f}"),
        (tr("csv.range"), "%.2f–%.2f" % tuple(meta.get("range") or (0, 0))),
        (tr("csv.step"), f"{meta.get('step_hint') or meta.get('step') or 0:.3f}"),
    ]
    if ident is not None:
        rows += [
            (tr("csv.ident"), tr(ident.summary_key())),
            (tr("csv.coverage"), f"{ident.coverage:.4f}"),
            (tr("csv.unexplained"), f"{ident.unexplained:.4f}"),
            (tr("csv.resid"), f"{ident.resid_rms:.4f}"),
            (tr("csv.resid_ratio"), f"{ident.resid_ratio:.4f}"),
            (tr("csv.reason"), "；".join(
                tr(k, **ident.reason_kw()) for k in ident.fail_reasons())),
        ]
    rows += [
        (tr("csv.a"), f"{a:.6f}"),
        (tr("csv.b"), f"{b:.6f}"),
        (tr("csv.c"), f"{c:.6f}"),
        (tr("csv.alpha"), f"{al:.4f}"),
        (tr("csv.beta"), f"{be:.4f}"),
        (tr("csv.gamma"), f"{ga:.4f}"),
        (tr("csv.volume"), f"{result.volume:.4f}"),
        (tr("csv.system"), sym.system_label(current_language())),
        (tr("csv.spacegroup"), sym.space_group or "—"),
        (tr("csv.sg_number"), "" if sym.number is None else str(sym.number)),
        (tr("csv.pointgroup"), sym.point_group or "—"),
        (tr("csv.laue"), sym.laue_class or "—"),
        (tr("csv.bravais"), sym.bravais or "—"),
        (tr("csv.size"), "" if result.size_nm is None else f"{result.size_nm:.2f}"),
        (tr("csv.strain"), "" if result.strain is None
         else f"{result.strain * 100:.4f}"),
        (tr("csv.zero"), f"{result.refinement.params.zero:.5f}"),
        (tr("csv.rwp"), f"{rf.rwp:.4f}"),
        (tr("csv.rp"), f"{rf.rp:.4f}"),
        (tr("csv.rexp"), f"{rf.rexp:.4f}"),
        (tr("csv.chi2"), f"{rf.chi2:.4f}"),
        (tr("csv.gof"), f"{result.gof:.4f}"),
        (tr("csv.rb"), "" if result.rbragg is None else f"{result.rbragg:.4f}"),
        (tr("csv.nparams"), str(result.refinement.n_params)),
        (tr("csv.points"), str(int(np.asarray(result.two_theta).size))),
        (tr("csv.elapsed"), f"{result.elapsed_s:.1f}"),
    ]
    return rows


def write_summary_csv(path: str | Path, rows: Sequence[tuple[str, str]]) -> None:
    _write_csv(path, [[tr("csv.col.item"), tr("csv.col.value")], *rows])


def write_pattern_csv(path: str | Path, result) -> None:
    """拟合谱四列：2θ / 实测 / 计算 / 差值 / 背景。"""
    header = [tr("csv.col.2th"), tr("csv.col.obs"), tr("csv.col.calc"),
              tr("csv.col.diff"), tr("csv.col.bg")]
    tt = np.asarray(result.two_theta)
    rows = [[f"{tt[i]:.4f}", f"{result.yobs[i]:.2f}", f"{result.ycalc[i]:.2f}",
             f"{result.diff[i]:.2f}", f"{result.background[i]:.2f}"]
            for i in range(tt.size)]
    _write_csv(path, [header, *rows])


def write_bragg_csv(path: str | Path, result) -> None:
    """布拉格反射表：2θ / hkl / I_obs / I_calc。"""
    header = [tr("csv.col.2th"), tr("csv.col.hkl"), tr("csv.col.iobs"),
              tr("csv.col.icalc")]
    rows: list[list[object]] = []
    if result.bragg is not None:
        for pos, hkl, io, ic in result.bragg.as_rows():
            rows.append([f"{pos:.4f}", hkl, f"{io:.2f}", f"{ic:.2f}"])
    _write_csv(path, [header, *rows])


def write_peaks_csv(path: str | Path, peaks) -> None:
    """寻峰结果：2θ / 净峰高 / FWHM / η / 面积 / SNR / 拟合R²。"""
    header = [tr("csv.col.2th"), tr("csv.col.height"), tr("csv.col.fwhm"),
              tr("csv.col.eta"), tr("csv.col.area"), tr("csv.col.snr"),
              tr("csv.col.r2")]
    rows = [[f"{p.two_theta:.4f}", f"{p.height:.2f}", f"{p.fwhm:.4f}",
             f"{p.eta:.3f}", f"{p.area:.2f}", f"{p.snr:.1f}", f"{p.r2:.3f}"]
            for p in peaks]
    _write_csv(path, [header, *rows])


def write_text(path: str | Path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
