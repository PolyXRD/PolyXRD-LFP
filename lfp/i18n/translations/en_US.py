"""English translation table.

Key set is kept **identical** to :mod:`lfp.i18n.translations.zh_CN`
(``tests/test_i18n.py`` asserts set equality, so a missing key fails CI
instead of silently rendering ``⟪key⟫``).
"""

from __future__ import annotations

TRANSLATIONS: dict[str, str] = {
    # ------------------------------------------------------------------ #
    # Generic
    # ------------------------------------------------------------------ #
    "app.title": "LiFePO4 phase identification and Rietveld refinement",
    "btn.ok": "OK",
    "btn.cancel": "Cancel",
    "btn.close": "Close",
    "btn.browse": "Browse…",
    "state.on": "on",
    "state.off": "off",

    # ------------------------------------------------------------------ #
    # Menus
    # ------------------------------------------------------------------ #
    "menu.file": "&File",
    "menu.file.open": "Import XRD pattern…",
    "menu.file.export_html": "Export report (HTML)…",
    "menu.file.export_csv": "Export summary (CSV)…",
    "menu.file.export_pattern": "Export fit profile (CSV)…",
    "menu.file.export_bragg": "Export Bragg reflections (CSV)…",
    "menu.file.export_peaks": "Export peak list (CSV)…",
    "menu.file.export_png": "Export figure (PNG)…",
    "menu.file.exit": "Exit",

    "menu.process": "&Processing",
    "menu.process.smooth": "Smooth (Savitzky–Golay)…",
    "menu.process.background": "Background subtraction…",
    "menu.process.ka2": "Strip Kα2…",
    "menu.process.peaks": "Find peaks",
    "menu.process.reset": "Restore raw pattern",
    "menu.process.export_peaks": "Export peak list (CSV)…",

    "menu.language": "&Language",

    "menu.view": "&View",
    "menu.view.fit": "Show refinement plot",
    "menu.view.spectrum": "Show processed pattern",

    "menu.help": "&Help",
    "menu.help.about": "About PolyXRD LFP",
    "menu.help.copyright": "Copyright and license",

    # ------------------------------------------------------------------ #
    # Toolbar
    # ------------------------------------------------------------------ #
    "toolbar.open": "Import",
    "toolbar.smooth": "Smooth",
    "toolbar.bg": "Background",
    "toolbar.ka2": "Strip Kα2",
    "toolbar.peaks": "Find peaks",
    "toolbar.reset": "Raw",
    "toolbar.export": "Export",

    # ------------------------------------------------------------------ #
    # Panel titles
    # ------------------------------------------------------------------ #
    "panel.sample": "Sample and measurement",
    "panel.conditions": "Measurement conditions",
    "panel.structure": "Structure model (CIF)",
    "panel.verdict": "LiFePO4 phase identification",
    "panel.refine": "Rietveld refinement",
    "panel.result": "Refinement results",

    "sample.name": "Sample",
    "sample.placeholder": "optional, defaults to file name",

    "meta.file": "File",
    "meta.anode": "Anode",
    "meta.wavelength": "Wavelength λ",
    "meta.range": "2θ range",
    "meta.step": "Step size",
    "meta.points": "Data points",
    "row.meta.file": "File",
    "row.meta.anode": "Anode",
    "row.meta.wavelength": "Wavelength λ",
    "row.meta.range": "2θ range",
    "row.meta.step": "Step",
    "row.meta.points": "Points",

    # ------------------------------------------------------------------ #
    # Structure model
    # ------------------------------------------------------------------ #
    "struct.import": "Import CIF…",
    "struct.builtin": "Built-in · {name}",
    "struct.imported": "User CIF · {name}",
    "struct.atoms.value": "{asym} sites / {sym} ops / {total} atoms",
    "struct.not_lfp_warn": (
        "This structure contains no Li–Fe–P–O set, so it is not a lithium "
        "iron phosphate model. Refinement results would lose physical "
        "meaning — please import a LiFePO4 CIF."),
    "row.struct.formula": "Formula",
    "row.struct.sg": "Space group",
    "row.struct.system": "Crystal system",
    "row.struct.point": "Point group",
    "row.struct.laue": "Laue class",
    "row.struct.bravais": "Bravais lattice",
    "row.struct.atoms": "Asymmetric unit",

    # ------------------------------------------------------------------ #
    # Identification
    # ------------------------------------------------------------------ #
    "ident.rerun": "Identify again",
    "ident.running": "Identifying…",
    "ident.top3.value": "{n} / 3",
    "ident.note": (
        "Criteria: observed intensity explained by LiFePO4 reference peaks "
        "(coverage) ≥ 70 %, all three strongest lines matched, and "
        "unexplained intensity ≤ 35 %. All three must pass."),
    "ident.note.pass": (
        "All criteria passed — the pattern matches LiFePO4 (Pnma) reference "
        "peaks and can be refined structurally."),
    "ident.note.partial": (
        "Some criteria failed: this pattern cannot be confirmed as LiFePO4, "
        "so refinement is blocked by design. The criteria that failed are "
        "listed below — resolve them before identifying again."),
    "ident.note.fail": (
        "The criteria clearly fail: this pattern does not match the LiFePO4 "
        "reference peaks, so refinement has been terminated."),
    "row.ident.verdict": "Verdict",
    "row.ident.coverage": "Coverage",
    "row.ident.top3": "Top three lines",
    "row.ident.unexplained": "Unexplained",
    "row.ident.shift": "Zero shift",
    "row.ident.resid": "Peak residual",
    "row.ident.cell": "Prefit a / b / c",
    "ident.verdict.pass": "LiFePO4",
    "ident.verdict.partial": "Possible second phase",
    "ident.verdict.fail": "Not LiFePO4",
    "ident.resid.value": "{rms:.3f}° (tolerance {tol:.3f}°)",
    "ident.reason.head": "Failed criteria: ",
    "ident.reason.coverage": "coverage {cov:.1f} % < 70 %",
    "ident.reason.top3": "only {n} / 3 strongest lines matched",
    "ident.reason.unexplained": "unexplained intensity {unexp:.1f} % > 35 %",
    "ident.reason.model": (
        "peak residual {rms:.3f}° is {ratio:.0%} of the tolerance "
        "{tol:.3f}° (limit 45 %): the peak positions cannot be described by "
        "zero shift plus isotropic strain, indicating anisotropic distortion "
        "or an overlapping second phase"),
    "dlg.notlfp.resid": "\n\nPeak residual RMS = {rms:.4f}° "\
                        "({ratio:.0%} of tolerance)",
    "ident.note.gate": (
        "All criteria above count peaks and intensities and are insensitive to "
        "systematic position misfit. A separate gate therefore requires the "
        "residual of matched peaks, after removing zero shift and isotropic "
        "strain, to stay below 45 % of the position tolerance. Exceeding it "
        "means those two parameters cannot explain the observed positions "
        "(e.g. anisotropic cell distortion), so refinement is not entered."),

    # ------------------------------------------------------------------ #
    # Refinement progress (core progress_cb shows up in the busy dialog)
    # ------------------------------------------------------------------ #
    "stage.identify": "Identifying LiFePO4…",
    "stage.progress": "Refinement stage {i}/{n}: {label}",
    "stage.linear": "Linear layer (scale + background)",
    "stage.shape": "Peak shape (zero + size/strain + asymmetry)",
    "stage.cell": "Unit cell (a / b / c)",
    "stage.full": "Full model",
    "stage.build": "Building refinement model…",
    "stage.eval": "Evaluated {n} times · current Rwp = {rwp:.2f}%",
    "stage.final": "Synthesizing final calculated pattern…",
    "stage.rbragg": "Computing R_Bragg…",
    "stage.done": "Done",

    # ------------------------------------------------------------------ #
    # Refinement panel
    # ------------------------------------------------------------------ #
    "refine.bg": "Background",
    "refine.bg.cheb": "Chebyshev polynomial",
    "refine.bg.tent": "Linear interpolation (tent)",
    "refine.nbg": "Terms",
    "refine.range": "2θ range",
    "refine.run": "Start refinement",
    "refine.cancel": "Cancel refinement",

    "opt.cell": "Cell a / b / c",
    "opt.cell.tip": "All three orthorhombic edges, starting from the prefitted cell.",
    "opt.zero": "Zero offset",
    "opt.zero.tip": "Global 2θ shift from sample displacement or instrument zero (°).",
    "opt.size": "Crystallite size",
    "opt.size.tip": "Scherrer size (Lorentzian broadening) in nm.",
    "opt.strain": "Microstrain",
    "opt.strain.tip": "Wilson microstrain (β = 4ε·tanθ), dimensionless.",
    "opt.asym": "Asymmetry",
    "opt.asym.tip": "Low-angle tailing from axial divergence / sample penetration.",
    "opt.po": "Preferred orientation",
    "opt.po.tip": "March–Dollase preferred orientation (020), common in pressed pellets.",
    "opt.uvw": "Instrument U V W",
    "opt.uvw.tip": "Caglioti FWHM parameters; refine when a standard is available.",
    "opt.bfactor": "Temperature factor B",
    "opt.bfactor.tip": "Overall isotropic B (Å²); strongly correlated with size, may diverge.",

    # ------------------------------------------------------------------ #
    # Results
    # ------------------------------------------------------------------ #
    "res.group.cell": "Lattice parameters",
    "res.group.sym": "Symmetry",
    "res.group.micro": "Microstructure",
    "res.group.fit": "Goodness of fit",
    "res.note": (
        "The absolute Rwp is limited by counting statistics: a fast, low-count "
        "scan has a high Rexp, so Rwp cannot become very small. Read "
        "GOF = Rwp/Rexp as well (best near 1; below 1 means σ is "
        "overestimated, not a better fit). R_B: {rb_verdict}."),
    "row.res.a": "a",
    "row.res.b": "b",
    "row.res.c": "c",
    "row.res.alpha": "α",
    "row.res.beta": "β",
    "row.res.gamma": "γ",
    "row.res.volume": "Cell volume V",
    "row.res.system": "Crystal system",
    "row.res.sg": "Space group",
    "row.res.point": "Point group",
    "row.res.laue": "Laue class",
    "row.res.bravais": "Bravais lattice",
    "row.res.size": "Crystallite size D",
    "row.res.strain": "Microstrain ε",
    "row.res.fwhm": "FWHM (35.6°)",
    "row.res.eta": "η (35.6°)",
    "row.res.rwp": "Rwp",
    "row.res.rp": "Rp",
    "row.res.rexp": "Rexp",
    "row.res.chi2": "χ²",
    "row.res.gof": "GOF",
    "row.res.rb": "R_Bragg",
    "row.res.verdict": "Reading",

    "verdict.rwp.excellent": "Excellent",
    "verdict.rwp.good": "Good",
    "verdict.rwp.consistent": "Adequately fitted",
    "verdict.rwp.acceptable": "Acceptable",
    "verdict.rwp.poor": "Low, check the model",
    "verdict.gof.good": "Near 1",
    "verdict.gof.fair": "Slightly high",
    "verdict.gof.poor": "Clearly high",
    "verdict.gof.low": "Below 1 (σ too large)",
    "verdict.rb.good": "Structural model matches observed intensities",
    "verdict.rb.fair": "Acceptable, weak peaks may be less accurate",
    "verdict.rb.poor": "Low, review the structural model",
    "verdict.rb.unknown": "not computed",

    # ------------------------------------------------------------------ #
    # Canvas
    # ------------------------------------------------------------------ #
    "canvas.x_label": "2θ (°)",
    "canvas.y_label": "Intensity (counts)",
    "canvas.y_diff": "Difference",
    "canvas.empty": "Import an XRD pattern to plot it here",
    "canvas.bragg": "Bragg positions",
    "canvas.legend.obs": "Observed",
    "canvas.legend.calc": "Calculated",
    "canvas.legend.bg": "Background",
    "canvas.legend.err": "Observed − calculated",
    "canvas.legend.peaks": "Peaks",

    # ------------------------------------------------------------------ #
    # Dialogs
    # ------------------------------------------------------------------ #
    "dialog.about.title": "About PolyXRD LFP",
    "dialog.copyright.title": "Copyright and license",
    "about.features": (
        "A dedicated tool for lithium iron phosphate (LiFePO4, olivine, "
        "Pnma) cathode materials: after import the pattern is first checked "
        "for LiFePO4, and only a positive identification proceeds to "
        "whole-pattern Rietveld refinement, which reports lattice "
        "parameters, crystal system / point group / space group / Laue "
        "class, crystallite size and microstrain, plus Rwp / Rp / Rexp / χ² "
        "/ GOF / R_Bragg."),
    "about.contact": "Contact",
    "about.rights": "All rights reserved",
    "copyright.head": "PolyXRD LFP · copyright and license",

    "dlg.smooth.title": "Smoothing (Savitzky–Golay)",
    "dlg.smooth.window": "Window points",
    "dlg.smooth.order": "Polynomial order",
    "dlg.smooth.hint": (
        "A larger window smooths more but lowers peak height and broadens "
        "the profile; a higher order preserves shape better. Suggested: "
        "window 9–21 (odd), order 2–4. Smoothing affects display and peak "
        "searching only — refinement always uses the raw pattern."),
    "dlg.bg.title": "Background subtraction",
    "dlg.bg.method": "Method",
    "dlg.bg.iter": "SNIP iterations",
    "dlg.bg.order": "Polynomial order",
    "dlg.bg.hint": (
        "SNIP suits stepped backgrounds (more iterations give a lower "
        "background); a polynomial suits smooth backgrounds; linear joins "
        "the two end points. The result affects display and peak searching "
        "only — refinement uses a modelled background."),
    "bg.snip": "SNIP clipping",
    "bg.poly": "Polynomial",
    "bg.linear": "Linear (end points)",
    "dlg.ka2.title": "Strip Kα2",
    "dlg.ka2.anode": "Anode",
    "dlg.ka2.ratio": "I(Kα2)/I(Kα1)",
    "dlg.ka2.hint": (
        "Rachinger recursion, stripping Kα2 point by point from high to low "
        "angle. Use 0.50 for a Cu tube. The stripped pattern is for display "
        "and peak searching; refinement handles the Kα1/Kα2 doublet "
        "explicitly in the forward model."),
    "busy.title": "Please wait",
    "busy.starting": "Preparing…",
    "busy.canceling": "Cancelling…",
    "dlg.notlfp.title": "Verdict: not LiFePO4",
    "dlg.notlfp.text": "This pattern was not identified as LiFePO4; refinement has been stopped.",
    "dlg.notlfp.info": (
        "Coverage {cov:.1f} %, top three lines matched {top} / 3, "
        "unexplained intensity {unexp:.1f} %."),
    "dlg.notlfp.detail": (
        "{n} observed peaks; {refs} LiFePO4 reference peaks, {matched} "
        "matched within ±{tol:.3f}°; fitted zero shift {dz:+.3f}°, "
        "strain scale {e:+.2f} %."),

    # ------------------------------------------------------------------ #
    # File dialogs
    # ------------------------------------------------------------------ #
    "filter.pattern": "XRD patterns (*.txt *.xy *.xye *.dat *.csv *.asc *.prn);;All files (*)",
    "filter.cif": "CIF structure files (*.cif);;All files (*)",
    "filter.html": "HTML report (*.html)",
    "filter.csv": "CSV table (*.csv)",
    "filter.png": "PNG image (*.png)",
    "dlg.open.title": "Import XRD pattern",
    "dlg.save.report": "Save analysis report",
    "dlg.save.csv": "Save CSV",
    "dlg.save.png": "Save figure",
    "dlg.import_cif.title": "Import CIF structure file",

    # ------------------------------------------------------------------ #
    # Status bar and messages
    # ------------------------------------------------------------------ #
    "status.ready": "Ready · import an XRD pattern",
    "status.loading": "Reading pattern…",
    "status.loaded": "Imported {name} ({n} points, {lo:.2f}–{hi:.2f}°)",
    "status.identifying": "Checking whether this is LiFePO4…",
    "status.non_lfp": "Not LiFePO4 — further processing stopped",
    "status.lfp": "Identified as LiFePO4 — structure refinement is available",
    "status.refining": "Refining…",
    "status.refined": "Refinement finished: Rwp = {rwp:.2f} %, GOF = {gof:.3f}, {sec:.1f} s",
    "status.canceled": "Cancelled",
    "status.processed": "Applied: {what}",
    "status.reset": "Raw pattern restored",
    "status.exported": "Saved {path}",
    "status.struct_loaded": "Structure model loaded: {name}",

    "err.open.title": "Cannot read pattern",
    "err.open.text": "Failed to read the file:\n{msg}",
    "err.open.hint": (
        "Two-column text (2θ intensity) or three-column (2θ intensity "
        "weight/σ) is supported. For proprietary binary formats, export to "
        "text first."),
    "err.cif.title": "Cannot read CIF",
    "err.cif.text": "CIF parsing failed:\n{msg}",
    "err.refine.title": "Refinement failed",
    "err.refine.text": "An error occurred during refinement:\n{msg}",
    "err.no_data.title": "No data",
    "err.no_data.text": "Please import an XRD pattern first.",
    "err.no_result.text": "Please finish a refinement before exporting results.",
    "err.peaks_empty": "No significant peaks found (lower the threshold or smooth first).",
    "confirm.cancel_refine": "Refinement cancelled.",

    # ------------------------------------------------------------------ #
    # Report
    # ------------------------------------------------------------------ #
    "report.title": "LiFePO4 phase identification and Rietveld refinement report",
    "report.generated": "generated {ts}",
    "report.sample": "Sample and data",
    "report.sample_name": "Sample",
    "report.file": "Data file",
    "report.identify": "Phase identification",
    "report.cell": "Lattice and symmetry",
    "report.micro": "Microstructure",
    "report.fit": "Goodness of fit",
    "report.params": "Refinement parameters",
    "report.figure": "Observed / calculated / difference",
    "report.bragg": "Bragg reflections (top 40 by calculated intensity)",
    "report.col.2th": "2θ (°)",
    "report.col.hkl": "h k l",
    "report.col.icalc": "I_calc",
    "report.col.iobs": "I_obs",
    "report.rwp_note": (
        "Rwp depends strongly on counting statistics: fast, low-count scans "
        "have a high Rexp, so Rwp cannot become very small. Read it together "
        "with GOF = Rwp/Rexp (best near 1)."),
    "report.limit": (
        "Method note: this is a single-phase whole-pattern Rietveld "
        "refinement. Peak shapes are pseudo-Voigt (Thompson–Cox–Hastings "
        "synthesis); crystallite size follows Scherrer (K = 0.9) and "
        "microstrain the Wilson formula, without instrumental broadening "
        "correction. R_Bragg uses the profile-partitioned definition: "
        "observed intensity of overlapping peaks is apportioned by "
        "calculated peak amplitudes, and unmodelled second phases are not "
        "counted, so R_B is biased low for heavily overlapping samples. "
        "Structural and symmetry data come from the built-in CIF (Yamada "
        "et al., J. Electrochem. Soc. 148 (2001) A224). A carbon coating or "
        "amorphous fraction contributes to the background only and does not "
        "enter the structure factor."),
    "report.footer": "Generated automatically by PolyXRD LFP; all values trace back to the exported CSV files.",

    # ------------------------------------------------------------------ #
    # Edition and registration
    # ------------------------------------------------------------------ #
    "about.edition": "Edition",
    "about.edition.internal": "Internal evaluation build",
    "about.edition.registered": "Registered edition",
    "about.registered_to": "Licensed to: {unit}",
    "about.unregistered": "Unregistered (evaluation use; commercial use requires registration)",
    "status.registered": "Registration successful: {unit}",

    # ------------------------------------------------------------------ #
    # CSV columns
    # ------------------------------------------------------------------ #
    "csv.col.item": "Item",
    "csv.col.value": "Value",
    "csv.col.2th": "2θ(°)",
    "csv.col.obs": "Observed",
    "csv.col.calc": "Calculated",
    "csv.col.diff": "Difference",
    "csv.col.bg": "Background",
    "csv.col.hkl": "hkl",
    "csv.col.iobs": "I_obs",
    "csv.col.icalc": "I_calc",
    "csv.col.height": "Net height",
    "csv.col.fwhm": "FWHM(°)",
    "csv.col.eta": "η",
    "csv.col.area": "Net area",
    "csv.col.snr": "SNR",
    "csv.col.r2": "Fit R²",
    "csv.sample": "Sample",
    "csv.file": "Data file",
    "csv.anode": "Anode",
    "csv.wavelength": "Wavelength(Å)",
    "csv.range": "2θ range(°)",
    "csv.step": "Step(°)",
    "csv.ident": "Identification",
    "csv.coverage": "Coverage",
    "csv.unexplained": "Unexplained intensity",
    "csv.resid": "Peak residual RMS (deg)",
    "csv.resid_ratio": "Peak residual / tolerance",
    "csv.reason": "Failed criteria",
    "csv.a": "a(Å)",
    "csv.b": "b(Å)",
    "csv.c": "c(Å)",
    "csv.alpha": "α(°)",
    "csv.beta": "β(°)",
    "csv.gamma": "γ(°)",
    "csv.volume": "V(Å³)",
    "csv.system": "Crystal system",
    "csv.spacegroup": "Space group",
    "csv.sg_number": "Space-group number",
    "csv.pointgroup": "Point group",
    "csv.laue": "Laue class",
    "csv.bravais": "Bravais lattice",
    "csv.size": "Crystallite size(nm)",
    "csv.strain": "Microstrain(%)",
    "csv.zero": "Zero offset(°)",
    "csv.rwp": "Rwp(%)",
    "csv.rp": "Rp(%)",
    "csv.rexp": "Rexp(%)",
    "csv.chi2": "chi2",
    "csv.gof": "GOF",
    "csv.rb": "R_Bragg(%)",
    "csv.nparams": "Parameters",
    "csv.points": "Data points",
    "csv.elapsed": "Elapsed(s)",
}
