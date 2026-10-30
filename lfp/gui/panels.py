"""右侧参数与结果面板（单窗口布局：所有操作都在同一屏内完成）。

面板只负责「采集参数 / 显示结果」，所有计算都在 :mod:`lfp.gui.tasks`
的后台线程里跑，算法细节全在 :mod:`lfp.core`。面板之间不互相调用，
由 :mod:`lfp.gui.main_window` 统一编排（避免面板之间形成隐式耦合）。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from lfp.gui.widgets import (
    CARD_QSS_FLAT,
    CARD_QSS_TITLED,
    ResultCard,
    TextBlock,
)
from lfp.i18n import tr

MUTED = "#64748B"


def _muted(text: str, parent: QWidget | None = None, size: int = 11) -> QLabel:
    lbl = QLabel(text, parent)
    lbl.setStyleSheet(f"color:{MUTED}; font-size:{size}px;")
    return lbl


class SamplePanel(QGroupBox):
    """样品与测量条件（可编辑样品名；其余为只读元数据）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)
        row = QHBoxLayout()
        self.lbl_sample = QLabel(self)
        self.ed_sample = QLineEdit(self)
        self.ed_sample.setPlaceholderText(tr("sample.placeholder"))
        row.addWidget(self.lbl_sample)
        row.addWidget(self.ed_sample, 1)
        lay.addLayout(row)
        self.card = ResultCard(["meta.file", "meta.anode", "meta.wavelength",
                                "meta.range", "meta.step", "meta.points"],
                               self, columns=2)
        self.card.setStyleSheet(CARD_QSS_TITLED)
        lay.addWidget(self.card)

    def set_metadata(self, meta: dict, file_name: str) -> None:
        rng = meta.get("range") or (float("nan"), float("nan"))
        step = meta.get("step_hint")
        if step is None and meta.get("step"):
            step = meta["step"]
        self.card.set_value("meta.file", file_name)
        self.card.set_value("meta.anode", str(meta.get("anode") or "—"))
        self.card.set_value("meta.wavelength", f"{meta.get('wavelength', 0):.5f} Å")
        self.card.set_value("meta.range", f"{rng[0]:.2f} – {rng[1]:.2f}°")
        self.card.set_value("meta.step", "—" if not step else f"{float(step):.3f}°")
        self.card.set_value("meta.points", str(meta.get("points", "—")))

    def clear(self) -> None:
        self.card.clear()
        self.ed_sample.clear()

    def sample_name(self) -> str:
        return self.ed_sample.text().strip()

    def retranslate(self) -> None:
        self.setTitle(tr("panel.sample"))
        self.lbl_sample.setText(tr("sample.name"))
        self.ed_sample.setPlaceholderText(tr("sample.placeholder"))
        for key in ("meta.file", "meta.anode", "meta.wavelength", "meta.range",
                    "meta.step", "meta.points"):
            self.card.set_label(key, tr(f"row.{key}"))
        self.card.setTitle(tr("panel.conditions"))


class StructurePanel(QGroupBox):
    """结构模型（内置 LFP CIF / 用户导入 CIF）。"""

    import_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)
        top = QHBoxLayout()
        self.lbl_model = QLabel(self)
        self.lbl_model.setStyleSheet("font-weight:600;")
        self.btn_import = QPushButton(self)
        self.btn_import.clicked.connect(self.import_requested.emit)
        top.addWidget(self.lbl_model, 1)
        top.addWidget(self.btn_import)
        lay.addLayout(top)
        self.card = ResultCard(["struct.formula", "struct.sg", "struct.system",
                                "struct.point", "struct.laue", "struct.bravais",
                                "struct.atoms"], self, columns=1)
        self.card.setStyleSheet(CARD_QSS_FLAT)
        lay.addWidget(self.card)
        self.warn = _muted("", self)
        self.warn.setWordWrap(True)
        self.warn.hide()
        lay.addWidget(self.warn)

    def set_structure(self, struct, *, builtin: bool) -> None:
        self._last = (struct, builtin)      # 语言切换时按当前语言重渲染
        from lfp.core.symmetry import describe_structure
        sym = describe_structure(struct)
        name = struct.formula or struct.mineral or struct.name
        self.lbl_model.setText(
            tr("struct.builtin", name=str(name)) if builtin
            else tr("struct.imported", name=str(name)))
        self.card.set_value("struct.formula", str(struct.formula or "—"))
        self.card.set_value("struct.sg", f"{sym.space_group or '—'}"
                            + (f" (No. {sym.number})" if sym.number else ""))
        self.card.set_value("struct.system", sym.system_label(_lang()))
        self.card.set_value("struct.point", f"{sym.point_group or '—'}"
                            + (f" / {sym.point_group_schoenflies}"
                               if sym.point_group_schoenflies else ""))
        self.card.set_value("struct.laue", sym.laue_class or "—")
        self.card.set_value("struct.bravais", sym.bravais_label(_lang()))
        self.card.set_value("struct.atoms", tr("struct.atoms.value",
                                               asym=struct.n_asym,
                                               sym=struct.n_sym_ops,
                                               total=len(struct.atoms)))
        is_lfp = _looks_like_lfp(struct)
        self.warn.setVisible(not is_lfp)
        if not is_lfp:
            self.warn.setText(tr("struct.not_lfp_warn"))

    def retranslate(self) -> None:
        self.setTitle(tr("panel.structure"))
        self.btn_import.setText(tr("struct.import"))
        if getattr(self, "_last", None) is not None:
            _struct, _builtin = self._last
            self.set_structure(_struct, builtin=_builtin)
        for key in ("struct.formula", "struct.sg", "struct.system", "struct.point",
                    "struct.laue", "struct.bravais", "struct.atoms"):
            self.card.set_label(key, tr(f"row.{key}"))


class VerdictPanel(QGroupBox):
    """LiFePO4 判定（自动在导入后执行，可手动重跑）。"""

    rerun_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)
        self.card = ResultCard(["ident.verdict", "ident.coverage",
                                "ident.top3", "ident.unexplained",
                                "ident.shift", "ident.resid", "ident.cell"],
                               self, columns=1)
        self.card.setStyleSheet(CARD_QSS_FLAT)
        lay.addWidget(self.card)
        self.note = TextBlock(self)
        self.note.setStyleSheet(CARD_QSS_FLAT)
        lay.addWidget(self.note)
        self.btn_rerun = QPushButton(self)
        self.btn_rerun.clicked.connect(self.rerun_requested.emit)
        lay.addWidget(self.btn_rerun)

    def set_result(self, res) -> None:
        self._res = res                     # 语言切换时按当前语言重渲染
        key = res.summary_key()
        level = {"ident.verdict.pass": "good",
                 "ident.verdict.partial": "warn",
                 "ident.verdict.fail": "bad"}.get(key, "neutral")
        note_key = {"ident.verdict.pass": "ident.note.pass",
                    "ident.verdict.partial": "ident.note.partial",
                    "ident.verdict.fail": "ident.note.fail"}.get(
                        key, "ident.note")
        self.card.set_value("ident.verdict", tr(key), level)
        self.card.set_value("ident.coverage", f"{res.coverage * 100:.1f} %",
                            "good" if res.coverage >= 0.70 else "warn")
        self.card.set_value("ident.top3",
                            tr("ident.top3.value", n=res.top_strong_matched),
                            "good" if res.top_strong_matched >= 3 else "bad")
        self.card.set_value("ident.unexplained", f"{res.unexplained * 100:.1f} %",
                            "good" if res.unexplained <= 0.35 else "warn")
        self.card.set_value("ident.shift", f"{res.zero_shift:+.3f}°")
        self.card.set_value("ident.resid",
                            tr("ident.resid.value", rms=res.resid_rms,
                               tol=res.tolerance),
                            "good" if res.model_ok else "bad")
        cell = res.cell_scales
        self.card.set_value("ident.cell",
                            "—" if cell is None else
                            f"{cell[0]:.4f} / {cell[1]:.4f} / {cell[2]:.4f}")
        # 卡片 tooltip 常驻判据说明，正文只给「本次」的结论与理由
        self.card.setToolTip(tr("ident.note") + "\n\n" + tr("ident.note.gate"))
        text = tr(note_key)
        reasons = res.fail_reasons()
        if reasons:      # 把「没过哪条」直接写出来，别让用户对着一堆合格数字猜
            kw = res.reason_kw()
            text += "\n" + tr("ident.reason.head") + "；".join(
                tr(k, **kw) for k in reasons)
        self.note.set_text(text, level)

    def set_busy(self, busy: bool, text: str = "") -> None:
        self.card.set_value("ident.verdict",
                            tr("ident.running") if busy else self.card.value("ident.verdict"),
                            "neutral" if busy else None)
        self.btn_rerun.setEnabled(not busy)

    def clear(self) -> None:
        self.card.clear()
        self.note.set_text("")

    def set_enabled(self, on: bool) -> None:
        self.btn_rerun.setEnabled(on)

    def retranslate(self) -> None:
        self.setTitle(tr("panel.verdict"))
        self.btn_rerun.setText(tr("ident.rerun"))
        if getattr(self, "_res", None) is not None:
            self.set_result(self._res)
        for key in ("ident.verdict", "ident.coverage", "ident.top3",
                    "ident.unexplained", "ident.shift", "ident.resid",
                    "ident.cell"):
            self.card.set_label(key, tr(f"row.{key}"))


class RefinePanel(QGroupBox):
    """精修参数与运行按钮。"""

    run_requested = Signal()
    cancel_requested = Signal()

    #: (键, 默认勾选, 是否默认启用)
    OPTIONS = (
        ("opt.cell", True),
        ("opt.zero", True),
        ("opt.size", True),
        ("opt.strain", True),
        ("opt.asym", True),
        ("opt.po", False),
        ("opt.uvw", False),
        ("opt.bfactor", False),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from PySide6.QtWidgets import QCheckBox
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(3)
        grid = QGridLayout()
        grid.setVerticalSpacing(2)
        self._checks: dict[str, QCheckBox] = {}
        for i, (key, default) in enumerate(self.OPTIONS):
            chk = QCheckBox(self)
            chk.setChecked(default)
            grid.addWidget(chk, i // 2, i % 2)
            self._checks[key] = chk
        lay.addLayout(grid)

        row = QHBoxLayout()
        self.lbl_bg = QLabel(self)
        self.cmb_bg = QComboBox(self)
        self.lbl_nbg = QLabel(self)
        self.sp_nbg = QSpinBox(self)
        self.sp_nbg.setRange(3, 20)
        self.sp_nbg.setValue(8)
        row.addWidget(self.lbl_bg)
        row.addWidget(self.cmb_bg, 1)
        row.addWidget(self.lbl_nbg)
        row.addWidget(self.sp_nbg)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        self.lbl_range = QLabel(self)
        self.sp_tmin = QDoubleSpinBox(self)
        self.sp_tmax = QDoubleSpinBox(self)
        for sp in (self.sp_tmin, self.sp_tmax):
            sp.setRange(1.0, 160.0)
            sp.setDecimals(1)
            sp.setSingleStep(0.5)
            sp.setMinimumWidth(74)
        self.lbl_dash = _muted("–", self, 12)
        row2.addWidget(self.lbl_range)
        row2.addWidget(self.sp_tmin, 1)
        row2.addWidget(self.lbl_dash)
        row2.addWidget(self.sp_tmax, 1)
        lay.addLayout(row2)

        self.btn_run = QPushButton(self)
        self.btn_run.clicked.connect(self.run_requested.emit)
        lay.addWidget(self.btn_run)
        self.btn_cancel = QPushButton(self)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        self.btn_cancel.hide()
        lay.addWidget(self.btn_cancel)
        self.lbl_status = _muted("", self)
        self.lbl_status.setWordWrap(True)
        lay.addWidget(self.lbl_status)

        self.retranslate()

    # ------------------------------------------------------------------ #
    def config_dict(self) -> dict:
        """采集为 :class:`lfp.core.refine.nonlinear.RefineConfig` 的关键字。"""
        return {
            "refine_cell": self._checks["opt.cell"].isChecked(),
            "refine_zero": self._checks["opt.zero"].isChecked(),
            "refine_size": self._checks["opt.size"].isChecked(),
            "refine_strain": self._checks["opt.strain"].isChecked(),
            "refine_asym": self._checks["opt.asym"].isChecked(),
            "refine_po": self._checks["opt.po"].isChecked(),
            "refine_uvw": self._checks["opt.uvw"].isChecked(),
            "refine_bfactor": self._checks["opt.bfactor"].isChecked(),
            "refine_eta": True,
            "n_bg": int(self.sp_nbg.value()),
            "bg_mode": "tent" if self.cmb_bg.currentIndex() == 1 else "cheb",
            "tmin": float(self.sp_tmin.value()),
            "tmax": float(self.sp_tmax.value()),
        }

    def config_rows(self) -> list[tuple[str, str]]:
        """精修开关与背景设置的 (标签, 值) 列表（报告「精修参数」节用）。

        报告要能说明「这份结果是在什么开关下得到的」——Rietveld 报告清单
        （McCusker et al. 1999）明确要求列出被精修的参数集合，否则读者无法
        判断结果的可比性。
        """
        rows = [(tr(key), tr("state.on") if chk.isChecked() else tr("state.off"))
                for key, chk in self._checks.items()]
        rows += [
            (tr("refine.bg"), self.cmb_bg.currentText()),
            (tr("refine.nbg"), str(self.sp_nbg.value())),
            (tr("refine.range"),
             f"{self.sp_tmin.value():.2f} – {self.sp_tmax.value():.2f}°"),
        ]
        return rows

    def set_range(self, lo: float, hi: float) -> None:
        for sp in (self.sp_tmin, self.sp_tmax):
            sp.blockSignals(True)
        self.sp_tmin.setValue(max(1.0, lo))
        self.sp_tmax.setValue(min(160.0, hi))
        for sp in (self.sp_tmin, self.sp_tmax):
            sp.blockSignals(False)

    def set_busy(self, busy: bool) -> None:
        self.btn_run.setEnabled(not busy)
        self.btn_run.setVisible(not busy)
        self.btn_cancel.setVisible(busy)
        for chk in self._checks.values():
            chk.setEnabled(not busy)
        self.sp_nbg.setEnabled(not busy)
        self.cmb_bg.setEnabled(not busy)
        self.sp_tmin.setEnabled(not busy)
        self.sp_tmax.setEnabled(not busy)

    def set_status(self, text: str) -> None:
        self.lbl_status.setText(text)

    def set_runnable(self, on: bool) -> None:
        self.btn_run.setEnabled(on)

    def retranslate(self) -> None:
        self.setTitle(tr("panel.refine"))
        for key, chk in self._checks.items():
            chk.setText(tr(key))
            chk.setToolTip(tr(f"{key}.tip"))
        self.lbl_bg.setText(tr("refine.bg"))
        keep = self.cmb_bg.currentIndex()          # 语言切换不得重置用户选择
        self.cmb_bg.blockSignals(True)
        self.cmb_bg.clear()
        self.cmb_bg.addItem(tr("refine.bg.cheb"))
        self.cmb_bg.addItem(tr("refine.bg.tent"))
        self.cmb_bg.setCurrentIndex(max(0, keep))
        self.cmb_bg.blockSignals(False)
        self.lbl_nbg.setText(tr("refine.nbg"))
        self.lbl_range.setText(tr("refine.range"))
        self.btn_run.setText(tr("refine.run"))
        self.btn_cancel.setText(tr("refine.cancel"))


class ResultPanel(QWidget):
    """精修结果（晶胞 / 对称性 / 微结构 / 拟合优度）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.card_cell = ResultCard(
            ["res.a", "res.b", "res.c", "res.alpha", "res.beta", "res.gamma",
             "res.volume"], self, columns=2)
        self.card_cell.setStyleSheet(CARD_QSS_TITLED + "background:transparent;")
        self.card_sym = ResultCard(
            ["res.system", "res.sg", "res.point", "res.laue", "res.bravais"],
            self, columns=1)
        self.card_sym.setStyleSheet(CARD_QSS_TITLED + "background:transparent;")
        self.card_micro = ResultCard(
            ["res.size", "res.strain", "res.fwhm", "res.eta"], self, columns=2)
        self.card_micro.setStyleSheet(CARD_QSS_TITLED + "background:transparent;")
        self.card_fit = ResultCard(
            ["res.rwp", "res.rp", "res.rexp", "res.chi2", "res.gof", "res.rb",
             "res.verdict"], self, columns=2)
        self.card_fit.setStyleSheet(CARD_QSS_TITLED + "background:transparent;")
        for card in (self.card_cell, self.card_sym, self.card_micro, self.card_fit):
            lay.addWidget(card)
        self.note = TextBlock(self)
        self.note.setStyleSheet("QGroupBox{border:0; background:transparent;}")
        lay.addWidget(self.note)

    def set_result(self, res) -> None:
        from lfp.core.refine.rbragg import rbragg_verdict
        from lfp.gui.verdict import gof_verdict, rbragg_level, rwp_verdict
        a, b, c, al, be, ga = res.cell
        self.card_cell.set_value("res.a", f"{a:.5f} Å")
        self.card_cell.set_value("res.b", f"{b:.5f} Å")
        self.card_cell.set_value("res.c", f"{c:.5f} Å")
        self.card_cell.set_value("res.alpha", f"{al:.3f}°")
        self.card_cell.set_value("res.beta", f"{be:.3f}°")
        self.card_cell.set_value("res.gamma", f"{ga:.3f}°")
        self.card_cell.set_value("res.volume", f"{res.volume:.3f} Å³")

        sym = res.symmetry
        self.card_sym.set_value("res.system", sym.system_label(_lang()))
        self.card_sym.set_value("res.sg", (sym.space_group or "—")
                                + (f" (No. {sym.number})" if sym.number else ""))
        self.card_sym.set_value("res.point", (sym.point_group or "—")
                                + (f" / {sym.point_group_schoenflies}"
                                   if sym.point_group_schoenflies else ""))
        self.card_sym.set_value("res.laue", sym.laue_class or "—")
        self.card_sym.set_value("res.bravais", sym.bravais_label(_lang()))

        self.card_micro.set_value(
            "res.size", "—" if res.size_nm is None
            else f"{res.size_nm:.1f} nm")
        self.card_micro.set_value(
            "res.strain", "—" if res.strain is None
            else f"{res.strain * 100:.3f} %")
        fwhm = res.fwhm_at(min(35.6, float(res.two_theta[-1])))
        self.card_micro.set_value("res.fwhm", "—" if fwhm is None else f"{fwhm:.4f}°")
        eta = res.eta_at(min(35.6, float(res.two_theta[-1])))
        self.card_micro.set_value("res.eta", f"{eta:.3f}")

        rf = res.refinement.rf
        key, level = rwp_verdict(rf.rwp, res.gof)
        self.card_fit.set_value("res.rwp", f"{rf.rwp:.2f} %", level)
        self.card_fit.set_value("res.rp", f"{rf.rp:.2f} %")
        self.card_fit.set_value("res.rexp", f"{rf.rexp:.2f} %")
        self.card_fit.set_value("res.chi2", f"{rf.chi2:.3f}")
        gkey, glevel = gof_verdict(res.gof)
        self.card_fit.set_value("res.gof", f"{res.gof:.3f}", glevel)
        rb = res.rbragg
        self.card_fit.set_value("res.rb", "—" if rb is None else f"{rb:.2f} %",
                                rbragg_level(rb))
        self.card_fit.set_value("res.verdict", tr(key), level)
        self.note.set_text(tr("res.note", rb_verdict=tr(
            f"verdict.rb.{rbragg_verdict(rb) if rb is not None else 'unknown'}")),
            level)

    def clear(self) -> None:
        for card in (self.card_cell, self.card_sym, self.card_micro, self.card_fit):
            card.clear()
        self.note.set_text("")

    def retranslate(self) -> None:
        self.card_cell.setTitle(tr("res.group.cell"))
        self.card_sym.setTitle(tr("res.group.sym"))
        self.card_micro.setTitle(tr("res.group.micro"))
        self.card_fit.setTitle(tr("res.group.fit"))
        for card, keys in (
                (self.card_cell, ("res.a", "res.b", "res.c", "res.alpha",
                                  "res.beta", "res.gamma", "res.volume")),
                (self.card_sym, ("res.system", "res.sg", "res.point", "res.laue",
                                 "res.bravais")),
                (self.card_micro, ("res.size", "res.strain", "res.fwhm", "res.eta")),
                (self.card_fit, ("res.rwp", "res.rp", "res.rexp", "res.chi2",
                                 "res.gof", "res.rb", "res.verdict"))):
            for key in keys:
                card.set_label(key, tr(f"row.{key}"))


def _lang() -> str:
    from lfp.i18n import current_language
    return current_language()


def _looks_like_lfp(struct) -> bool:
    """结构里是否同时含 Li / Fe / P / O（用于提示「当前模型不是 LFP」）。"""
    elems = {a[0] for a in getattr(struct, "atoms", [])}
    return {"Li", "Fe", "P", "O"}.issubset(elems)
