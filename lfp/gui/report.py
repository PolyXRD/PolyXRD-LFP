"""自包含 HTML 报告（图片 base64 内嵌，浏览器直接打开/打印为 PDF）。

报告结构对齐 Rietveld 惯例（McCusker et al., J. Appl. Cryst. 32 (1999) 36
「Rietveld refinement round robin」建议的报告清单）：样品与测量条件、
结构模型与对称性、精修参数与开关、晶胞参数、微结构、拟合优度因子、
观测/计算/差值图、布拉格反射表、方法与局限说明。

数值一律来自 :class:`lfp.core.refine.api.AnalysisResult`，报告层不做任何
再计算，避免「界面显示与报告数值不一致」这类最难查的缺陷。
"""

from __future__ import annotations

import base64
import datetime
import html
from typing import Sequence

from lfp.i18n import tr
from lfp.version import APP_CONTACT_EMAIL, APP_NAME, __version__

_STYLE = """
  :root{ --ink:#0F172A; --muted:#64748B; --line:#E2E8F0; --brand:#0284C7; }
  body{ font-family:"Segoe UI","Microsoft YaHei",system-ui,sans-serif;
        color:var(--ink); background:#F1F5F9; margin:0; line-height:1.62;
        font-size:13.5px; }
  .page{ max-width:840px; margin:24px auto 48px; background:#fff;
         border:1px solid var(--line); border-radius:14px; padding:30px 38px;
         box-shadow:0 8px 28px rgba(15,23,42,.08); }
  h1{ font-size:21px; margin:0 0 2px; letter-spacing:.2px; }
  .sub{ font-size:12px; color:var(--muted); margin-bottom:20px; }
  h2{ font-size:12.5px; color:var(--brand); letter-spacing:1.2px;
      text-transform:uppercase; border-bottom:1px solid var(--line);
      padding-bottom:5px; margin:26px 0 10px; }
  table{ width:100%; border-collapse:collapse; font-size:13px; }
  td,th{ padding:5px 8px; border-bottom:1px solid #F1F5F9; vertical-align:top; }
  th{ text-align:left; color:var(--muted); font-weight:600; font-size:12px;
      border-bottom:1px solid var(--line); }
  td.k{ color:var(--muted); width:34%; }
  td.v{ font-weight:600; text-align:right; font-variant-numeric:tabular-nums; }
  td.num{ text-align:right; font-variant-numeric:tabular-nums; }
  .grid{ display:grid; grid-template-columns:1fr 1fr; gap:0 26px; }
  .verdict{ display:inline-block; padding:2px 10px; border-radius:999px;
            font-weight:700; font-size:12.5px; }
  .good{ background:#DCFCE7; color:#15803D; }
  .fair{ background:#DBEAFE; color:#1D4ED8; }
  .warn{ background:#FEF3C7; color:#B45309; }
  .bad{ background:#FEE2E2; color:#B91C1C; }
  img{ width:100%; border:1px solid var(--line); border-radius:8px;
       margin-top:10px; }
  .note{ font-size:12px; color:var(--muted); background:#F8FAFC;
         border-left:3px solid var(--brand); padding:9px 12px;
         border-radius:0 6px 6px 0; margin-top:10px; }
  .foot{ font-size:11px; color:#94A3B8; margin-top:26px; text-align:center;
         border-top:1px solid var(--line); padding-top:12px; }
  @media print{ body{ background:#fff; } .page{ box-shadow:none; border:0;
      margin:0; padding:0; max-width:none; } h2{ page-break-after:avoid; } }
"""


def _rows_html(rows: Sequence[tuple[str, str, str | None]]) -> str:
    """(标签, 值, 档位) -> 表格行；档位非空时值着色。"""
    out = []
    for label, value, level in rows:
        cls = f' class="{level}"' if level else ""
        if level:
            value_html = f'<span class="verdict {level}">{html.escape(value)}</span>'
        else:
            value_html = html.escape(value)
        out.append(f"<tr><td class='k'>{html.escape(label)}</td>"
                   f"<td class='v'{cls}>{value_html}</td></tr>")
    return "".join(out)


def _bragg_table(rows: Sequence[tuple[float, str, float, float]],
                 limit: int = 40) -> str:
    """布拉格反射表（按计算强度取前 limit 条）。"""
    if not rows:
        return ""
    body = "".join(
        f"<tr><td class='num'>{pos:.3f}</td><td>{html.escape(hkl)}</td>"
        f"<td class='num'>{ic:.1f}</td><td class='num'>{io:.1f}</td></tr>"
        for pos, hkl, io, ic in rows)
    return (f"<table><thead><tr><th>{html.escape(tr('report.col.2th'))}</th>"
            f"<th>{html.escape(tr('report.col.hkl'))}</th>"
            f"<th style='text-align:right'>{html.escape(tr('report.col.icalc'))}</th>"
            f"<th style='text-align:right'>{html.escape(tr('report.col.iobs'))}</th>"
            f"</tr></thead><tbody>{body}</tbody></table>")


def build_html_report(*, result, sample: str, file_name: str,
                      cfg_rows: Sequence[tuple[str, str]],
                      png_b64: str = "") -> str:
    """构建报告 HTML。

    result   : :class:`lfp.core.refine.api.AnalysisResult`
    sample   : 样品名（界面输入，空则取文件名主干）
    file_name: 谱图文件名
    cfg_rows : 精修参数与开关的 (标签, 值) 列表
    png_b64  : 拟合图 PNG 的 base64
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    a, b, c, al, be, ga = result.cell
    sym = result.symmetry
    rf = result.refinement.rf
    ident = result.identification

    ident_rows = []
    if ident is not None:
        ident_rows = [
            (tr("row.ident.verdict"), tr(ident.summary_key()),
             "good" if ident.is_lfp else "bad"),
            (tr("row.ident.coverage"), f"{ident.coverage * 100:.1f} %", None),
            (tr("row.ident.top3"), f"{ident.top_strong_matched} / 3", None),
            (tr("row.ident.unexplained"), f"{ident.unexplained * 100:.1f} %", None),
            (tr("row.ident.shift"), f"{ident.zero_shift:+.3f}°", None),
            (tr("row.ident.resid"),
             tr("ident.resid.value", rms=ident.resid_rms, tol=ident.tolerance),
             "good" if ident.model_ok else "bad"),
        ]
        reasons = ident.fail_reasons()
        if reasons:
            kw = ident.reason_kw()
            ident_rows.append(
                (tr("ident.reason.head").rstrip("：: "),
                 "；".join(tr(k, **kw) for k in reasons), "bad"))

    cell_rows = [
        (tr("row.res.a"), f"{a:.5f} Å", None),
        (tr("row.res.b"), f"{b:.5f} Å", None),
        (tr("row.res.c"), f"{c:.5f} Å", None),
        (tr("row.res.alpha"), f"{al:.3f}°", None),
        (tr("row.res.beta"), f"{be:.3f}°", None),
        (tr("row.res.gamma"), f"{ga:.3f}°", None),
        (tr("row.res.volume"), f"{result.volume:.3f} Å³", None),
    ]
    sym_rows = [
        (tr("row.res.system"), sym.system_label(_lang()), None),
        (tr("row.res.sg"), f"{sym.space_group or '—'}"
         + (f" (No. {sym.number})" if sym.number else ""), None),
        (tr("row.res.point"), f"{sym.point_group or '—'}"
         + (f" / {sym.point_group_schoenflies}"
            if sym.point_group_schoenflies else ""), None),
        (tr("row.res.laue"), sym.laue_class or "—", None),
        (tr("row.res.bravais"), sym.bravais_label(_lang()), None),
    ]
    micro_rows = [
        (tr("row.res.size"), "—" if result.size_nm is None
         else f"{result.size_nm:.1f} nm", None),
        (tr("row.res.strain"), "—" if result.strain is None
         else f"{result.strain * 100:.3f} %", None),
        (tr("row.res.fwhm"), "—" if result.fwhm_at(35.6) is None
         else f"{result.fwhm_at(35.6):.4f}°", None),
        (tr("row.res.eta"), f"{result.eta_at(35.6):.3f}", None),
    ]

    from lfp.gui.verdict import gof_verdict, rwp_verdict
    vkey, vlevel = rwp_verdict(rf.rwp, result.gof)
    gkey, glevel = gof_verdict(result.gof)
    fit_rows = [
        (tr("row.res.rwp"), f"{rf.rwp:.2f} %", vlevel),
        (tr("row.res.rp"), f"{rf.rp:.2f} %", None),
        (tr("row.res.rexp"), f"{rf.rexp:.2f} %", None),
        (tr("row.res.chi2"), f"{rf.chi2:.3f}", None),
        (tr("row.res.gof"), f"{result.gof:.3f}", glevel),
        (tr("row.res.rb"), "—" if result.rbragg is None
         else f"{result.rbragg:.2f} %", None),
        (tr("row.res.verdict"), tr(vkey), vlevel),
    ]
    cfg_html = "".join(
        f"<tr><td class='k'>{html.escape(k)}</td>"
        f"<td class='v'>{html.escape(v)}</td></tr>" for k, v in cfg_rows)

    bragg_html = _bragg_table(result.bragg.as_rows()[:40] if result.bragg else [])
    img_html = (f"<img src='data:image/png;base64,{png_b64}' alt='Rietveld fit'>"
                if png_b64 else "")

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>{html.escape(tr('report.title'))} · {html.escape(sample)}</title>
<style>{_STYLE}</style></head><body><div class="page">
  <h1>{html.escape(tr('report.title'))}</h1>
  <div class="sub">{html.escape(APP_NAME)} v{__version__} ·
    {html.escape(tr('report.generated', ts=now))}</div>

  <h2>{html.escape(tr('report.sample'))}</h2>
  <table>
    <tr><td class="k">{html.escape(tr('report.sample_name'))}</td>
        <td class="v">{html.escape(sample)}</td></tr>
    <tr><td class="k">{html.escape(tr('report.file'))}</td>
        <td class="v">{html.escape(file_name)}</td></tr>
  </table>

  <h2>{html.escape(tr('report.identify'))}</h2>
  <table>{_rows_html(ident_rows)}</table>

  <h2>{html.escape(tr('report.cell'))}</h2>
  <div class="grid">
    <table>{_rows_html(cell_rows)}</table>
    <table>{_rows_html(sym_rows)}</table>
  </div>

  <h2>{html.escape(tr('report.micro'))}</h2>
  <table>{_rows_html(micro_rows)}</table>

  <h2>{html.escape(tr('report.fit'))}</h2>
  <table>{_rows_html(fit_rows)}</table>
  <div class="note">{html.escape(tr('report.rwp_note'))}</div>

  <h2>{html.escape(tr('report.params'))}</h2>
  <table>{cfg_html}</table>

  <h2>{html.escape(tr('report.figure'))}</h2>
  {img_html}

  <h2>{html.escape(tr('report.bragg'))}</h2>
  {bragg_html}

  <div class="note">{html.escape(tr('report.limit'))}</div>

  <div class="foot">© 2026 PolyXRD Team · {html.escape(APP_CONTACT_EMAIL)}<br>
    {html.escape(tr('report.footer'))}</div>
</div></body></html>"""


def _lang() -> str:
    from lfp.i18n import current_language
    return current_language()


def png_to_b64(path: str) -> str:
    """读取 PNG 并编码为 base64（报告内嵌用）。"""
    try:
        with open(path, "rb") as fh:
            return base64.b64encode(fh.read()).decode("ascii")
    except OSError:
        return ""
