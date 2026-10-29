"""对话框：关于 / 版权与许可 / 处理参数 / 非 LFP 提示 / 忙碌进度。

「关于」「版权」两框的框架文案走 i18n，许可要点正文以**中英并列**常量化
（与家族 RutAna 同一写法：许可条款是中英双语法律文本，不随界面语言切换）。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from lfp.gui.resources import resource_path
from lfp.i18n import tr
from lfp.version import (
    APP_CONTACT_EMAIL,
    APP_CONTACT_URL,
    APP_NAME,
    APP_ROLE,
    __version__,
)

# --------------------------------------------------------------------------- #
# 版权要点（恒为中英双语并列，与界面语言无关）
# --------------------------------------------------------------------------- #
COPYRIGHT_BODY_ZH = (
    "<p>© 2026 PolyXRD Team。本软件采用<b>双许可</b>发布："
    "<b>学术许可</b>（仅限非商业学术研究与教学，免费）或向版权持有人另行申请的"
    "<b>商业许可</b>。学术许可下可自由使用、复制、修改与分发，"
    "<b>不允许任何商业用途</b>；商用前必须联系版权持有人取得书面商业授权。</p>"
)
COPYRIGHT_BODY_EN = (
    "<p>Copyright © 2026 PolyXRD Team. This software is released under a "
    "<b>dual license</b>: the free <b>Academic License</b> (non-commercial "
    "academic research and education only) or a separately obtained "
    "<b>Commercial License</b>. The Academic License permits use, copying, "
    "modification and distribution <b>for non-commercial purposes only</b>; "
    "commercial use requires a separate written Commercial License.</p>"
)
COPYRIGHT_NOTE = (
    "完整许可文本见随附 LICENSE 与 LICENSE-CN 文件 / "
    "See the accompanying LICENSE and LICENSE-CN files for the full text."
)

#: 结构数据来源声明（About 与报告共用同一措辞，避免两处口径不一）
STRUCT_SOURCE_ZH = (
    "内置 LiFePO4 结构模型取自公开文献（Yamada et al., J. Electrochem. Soc. "
    "148 (2001) A224）：空间群 Pnma（No. 62），Z = 4，a ≈ 10.329 Å。"
)
STRUCT_SOURCE_EN = (
    "The built-in LiFePO4 model follows the published structure "
    "(Yamada et al., J. Electrochem. Soc. 148 (2001) A224): space group "
    "Pnma (No. 62), Z = 4, a ≈ 10.329 Å."
)


class AboutDialog(QDialog):
    """关于：logo、版本与版次、定位、数据来源与联系方式。"""

    def __init__(self, parent: QWidget | None = None,
                 reg_unit: str | None = None) -> None:
        """reg_unit：已注册的单位部门名称；None 表示未注册或内部评估版。"""
        super().__init__(parent)
        self.setWindowTitle(tr("dialog.about.title"))
        self.setMinimumWidth(480)
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignHCenter)

        logo_path = resource_path("logo-horizontal.png")
        if logo_path.exists():
            logo = QLabel(self)
            logo.setPixmap(QPixmap(str(logo_path)).scaledToWidth(320,
                                                                Qt.SmoothTransformation))
            logo.setAlignment(Qt.AlignHCenter)
            root.addWidget(logo)
        else:
            name = QLabel(APP_NAME, self)
            name.setStyleSheet("font-size:22px; font-weight:700; color:#0284C7;")
            name.setAlignment(Qt.AlignHCenter)
            root.addWidget(name)

        # 版本 + 版次（内部评估版 / 注册版），注册版再标出注册单位
        from lfp.edition import edition_key, is_internal

        line = f"v{__version__} · {tr(edition_key())}"
        if not is_internal():
            line += " · " + (tr("about.registered_to", unit=reg_unit)
                             if reg_unit else tr("about.unregistered"))
        ver = QLabel(line, self)
        ver.setAlignment(Qt.AlignHCenter)
        ver.setWordWrap(True)
        ver.setStyleSheet("color:#64748B; font-size:12px;")
        root.addWidget(ver)

        role = QLabel(APP_ROLE, self)
        role.setAlignment(Qt.AlignHCenter)
        role.setWordWrap(True)
        root.addWidget(role)

        body = QTextBrowser(self)
        body.setOpenExternalLinks(True)
        body.setFrameShape(QTextBrowser.NoFrame)
        body.setMaximumHeight(210)
        body.setHtml(
            f"<p style='color:#334155'>{tr('about.features')}</p>"
            f"<p style='color:#64748B;font-size:12px'>{STRUCT_SOURCE_ZH}<br>"
            f"{STRUCT_SOURCE_EN}</p>"
            f"<p style='color:#334155'>{tr('about.contact')}<br>"
            f"<a href='mailto:{APP_CONTACT_EMAIL}'>{APP_CONTACT_EMAIL}</a><br>"
            f"<a href='{APP_CONTACT_URL}'>{APP_CONTACT_URL}</a></p>"
            f"<p style='color:#94A3B8;font-size:12px'>© 2026 PolyXRD Team · "
            f"{tr('about.rights')}</p>")
        root.addWidget(body)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok, self)
        buttons.button(QDialogButtonBox.Ok).setText(tr("btn.ok"))
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)


class CopyrightDialog(QDialog):
    """版权与许可（中英要点 + 完整文本指向）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("dialog.copyright.title"))
        self.setMinimumWidth(560)
        root = QVBoxLayout(self)
        view = QTextBrowser(self)
        view.setFrameShape(QTextBrowser.NoFrame)
        view.setHtml(
            f"<h3 style='color:#0F172A'>{tr('copyright.head')}</h3>"
            f"{COPYRIGHT_BODY_ZH}{COPYRIGHT_BODY_EN}"
            f"<p style='color:#64748B'>{COPYRIGHT_NOTE}</p>"
            f"<p style='color:#334155'>{tr('copyright.contact')}<br>"
            f"<a href='mailto:{APP_CONTACT_EMAIL}'>{APP_CONTACT_EMAIL}</a></p>")
        root.addWidget(view)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok, self)
        buttons.button(QDialogButtonBox.Ok).setText(tr("btn.ok"))
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)


class SmoothDialog(QDialog):
    """平滑参数：窗口点数 + 多项式阶数。"""

    def __init__(self, parent=None, window: int = 11, order: int = 3) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.smooth.title"))
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.sp_window = QSpinBox(self)
        self.sp_window.setRange(3, 101)
        self.sp_window.setSingleStep(2)
        self.sp_window.setValue(window)
        self.sp_order = QSpinBox(self)
        self.sp_order.setRange(1, 7)
        self.sp_order.setValue(order)
        form.addRow(tr("dlg.smooth.window"), self.sp_window)
        form.addRow(tr("dlg.smooth.order"), self.sp_order)
        lay.addLayout(form)
        hint = QLabel(tr("dlg.smooth.hint"), self)
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#64748B; font-size:11px;")
        lay.addWidget(hint)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        bb.button(QDialogButtonBox.Ok).setText(tr("btn.ok"))
        bb.button(QDialogButtonBox.Cancel).setText(tr("btn.cancel"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def values(self) -> tuple[int, int]:
        return int(self.sp_window.value()), int(self.sp_order.value())


class BackgroundDialog(QDialog):
    """扣背景参数（SNIP 迭代次数 / 多项式阶数 / 端点比例）。"""

    def __init__(self, parent=None, method: str = "snip",
                 iterations: int = 20, order: int = 4) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.bg.title"))
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.cmb_method = QComboBox(self)
        self.cmb_method.addItem(tr("bg.snip"), "snip")
        self.cmb_method.addItem(tr("bg.poly"), "poly")
        self.cmb_method.addItem(tr("bg.linear"), "linear")
        idx = {"snip": 0, "poly": 1, "linear": 2}.get(method, 0)
        self.cmb_method.setCurrentIndex(idx)
        self.sp_iter = QSpinBox(self)
        self.sp_iter.setRange(4, 200)
        self.sp_iter.setValue(iterations)
        self.sp_order = QSpinBox(self)
        self.sp_order.setRange(1, 12)
        self.sp_order.setValue(order)
        form.addRow(tr("dlg.bg.method"), self.cmb_method)
        form.addRow(tr("dlg.bg.iter"), self.sp_iter)
        form.addRow(tr("dlg.bg.order"), self.sp_order)
        lay.addLayout(form)
        hint = QLabel(tr("dlg.bg.hint"), self)
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#64748B; font-size:11px;")
        lay.addWidget(hint)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        bb.button(QDialogButtonBox.Ok).setText(tr("btn.ok"))
        bb.button(QDialogButtonBox.Cancel).setText(tr("btn.cancel"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def values(self) -> tuple[str, int, int]:
        return (str(self.cmb_method.currentData()),
                int(self.sp_iter.value()), int(self.sp_order.value()))


class Ka2Dialog(QDialog):
    """去 Kα2 参数：靶材 + Iα2/Iα1。"""

    def __init__(self, parent=None, anode: str = "Cu", ratio: float = 0.5) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.ka2.title"))
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.cmb_anode = QComboBox(self)
        for key in ("Cu", "Co", "Cr", "Fe", "Mo", "Ag"):
            self.cmb_anode.addItem(key, key)
        i = self.cmb_anode.findData(anode)
        self.cmb_anode.setCurrentIndex(max(i, 0))
        self.sp_ratio = QDoubleSpinBox(self)
        self.sp_ratio.setRange(0.0, 1.0)
        self.sp_ratio.setSingleStep(0.05)
        self.sp_ratio.setDecimals(2)
        self.sp_ratio.setValue(ratio)
        form.addRow(tr("dlg.ka2.anode"), self.cmb_anode)
        form.addRow(tr("dlg.ka2.ratio"), self.sp_ratio)
        lay.addLayout(form)
        hint = QLabel(tr("dlg.ka2.hint"), self)
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#64748B; font-size:11px;")
        lay.addWidget(hint)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        bb.button(QDialogButtonBox.Ok).setText(tr("btn.ok"))
        bb.button(QDialogButtonBox.Cancel).setText(tr("btn.cancel"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def values(self) -> tuple[str, float]:
        return str(self.cmb_anode.currentData()), float(self.sp_ratio.value())


class BusyDialog(QDialog):
    """忙碌进度（可取消）。非模态由调用方决定，这里自带取消按钮。"""

    canceled = None    # 由外部赋值为可调用对象

    def __init__(self, parent=None, title: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle(title or tr("busy.title"))
        self.setWindowModality(Qt.ApplicationModal)
        self.setMinimumWidth(380)
        lay = QVBoxLayout(self)
        self.lbl = QLabel(tr("busy.starting"), self)
        self.lbl.setWordWrap(True)
        lay.addWidget(self.lbl)
        self.bar = QProgressBar(self)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        lay.addWidget(self.bar)
        self.btn_cancel = QPushButton(tr("btn.cancel"), self)
        self.btn_cancel.clicked.connect(self._on_cancel)
        lay.addWidget(self.btn_cancel)

    def _on_cancel(self) -> None:
        self.btn_cancel.setEnabled(False)
        self.lbl.setText(tr("busy.canceling"))
        if callable(self.canceled):
            self.canceled()

    def set_progress(self, msg: str, pct) -> None:
        self.lbl.setText(msg)
        if pct is None:
            self.bar.setRange(0, 0)
        else:
            self.bar.setRange(0, 100)
            self.bar.setValue(int(max(0.0, min(1.0, float(pct))) * 100))


def show_not_lfp(parent: QWidget, result) -> None:
    """非 LFP 提示：结论 + 证据 + 未通过的判据 + 终止说明（模态）。

    「未通过的判据」是必需项而非锦上添花：判定被残差闸门拦下时，
    覆盖率/前三强/未解释强度三个数都合格，只报这三个数会让人以为软件算错。
    """
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Critical)
    box.setWindowTitle(tr("dlg.notlfp.title"))
    box.setText(tr("dlg.notlfp.text"))
    info = tr("dlg.notlfp.info", cov=result.coverage * 100,
              top=result.top_strong_matched, unexp=result.unexplained * 100)
    reasons = result.fail_reasons()
    if reasons:
        kw = result.reason_kw()
        info += "\n\n" + tr("ident.reason.head") + "\n· " + "\n· ".join(
            tr(k, **kw) for k in reasons)
    box.setInformativeText(info)
    box.setDetailedText(tr(
        "dlg.notlfp.detail", n=len(result.observed), refs=result.n_ref_used,
        matched=result.n_matched, tol=result.tolerance,
        dz=result.zero_shift, e=result.strain_scale * 100)
        + tr("dlg.notlfp.resid", rms=result.resid_rms,
             ratio=result.resid_ratio))
    box.setStandardButtons(QMessageBox.Ok)
    box.button(QMessageBox.Ok).setText(tr("btn.ok"))
    box.exec()
