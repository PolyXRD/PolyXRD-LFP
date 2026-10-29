"""PolyXRD LFP 主窗口（单界面）。

产品纪律
--------
本工具只服务一种材料：磷酸铁锂（LiFePO4，橄榄石型，Pnma）。因此界面上
**没有**多物相、多方法的选项卡，只有一条线性工作流::

    导入谱图 → 判定是否 LiFePO4 →（是）Rietveld 精修 → 结果与导出

导入后立即判定；判定不通过就弹出对话框并把精修按钮禁用——宁可让用户
换一条谱图，也不给出一个物理上无意义的晶胞参数。

布局
----
左侧谱图区（:class:`SpectrumCanvas`，占全部富余高度）+ 处理工具条；
右侧竖直堆叠的五个面板（样品 / 结构 / 判定 / 精修 / 结果），放在
``QScrollArea`` 里以便小屏也能看全。菜单：文件 / 谱图处理 / 视图 / 语言 / 帮助。

线程模型
--------
精修（数秒到数十秒）在 :class:`lfp.gui.tasks.Task` 里跑，前台 ``BusyDialog``
显示进度并可取消。判定与寻峰都是 1–3 s 量级（主要开销是逐个峰做 pseudo-Voigt
拟合），放在后台反而要多一层「任务进行中禁止操作」的状态机，因此同步执行，
期间显示等待光标并把状态栏切到「正在判定/寻峰」——用户能看到程序在干活。
界面层不重算任何数值：所有显示值都来自
:class:`lfp.core.refine.api.AnalysisResult`。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from lfp.core.io import read_pattern
from lfp.core.peaks import find_peaks
from lfp.core.processing import (
    KA1,
    crop,
    estimate_background,
    savgol,
    strip_kalpha2,
    subtract,
)
from lfp.core.profile.cif import parse_cif
from lfp.core.refine.api import NotLFPError, identify_pattern, run_analysis
from lfp.core.refine.nonlinear import RefineCanceled, RefineConfig
from lfp.gui import exports
from lfp.gui.canvas import SpectrumCanvas
from lfp.gui.dialogs import (
    AboutDialog,
    BackgroundDialog,
    BusyDialog,
    CopyrightDialog,
    Ka2Dialog,
    SmoothDialog,
    show_not_lfp,
)
from lfp.gui.panels import (
    RefinePanel,
    ResultPanel,
    SamplePanel,
    StructurePanel,
    VerdictPanel,
)
from lfp.gui.report import build_html_report, png_to_b64
from lfp.gui.resources import builtin_cif_path, resource_path
from lfp.gui.tasks import Task
from lfp.i18n import (
    available_languages,
    current_language,
    load_language,
    save_language,
    set_language,
    tr,
)
from lfp.version import APP_NAME, __version__

#: 语言菜单顺序（与 available_languages 的键一致）
LANG_ORDER = ("zh_CN", "en_US", "ja_JP")

#: 右侧面板最小宽度（两列结果卡片 + 滚动条的实际需要，再窄会挤压数值）
PANEL_MIN_WIDTH = 500

#: 默认窗口尺寸 / 最小窗口尺寸（最小尺寸按「画布仍可读 + 面板不裁字」定）
WINDOW_SIZE = (1420, 920)
MIN_WINDOW_SIZE = (1120, 720)

#: 导出拟合图时的 DPI（报告内嵌图，180 在 A4 打印下约 300 dpi 等效）
REPORT_FIG_DPI = 180


class MainWindow(QMainWindow):
    """单窗口主界面：一屏完成「导入 → 判定 → 精修 → 导出」。"""

    def __init__(self) -> None:
        super().__init__()
        load_language()

        # ---- 状态（界面唯一真相来源，面板只被喂数据）----
        self._pattern_raw = None        # 导入时的原始谱（精修始终用它）
        self._pattern = None            # 当前显示/寻峰用的谱（可被处理过）
        self._struct = None             # CifStructure
        self._struct_builtin = True
        self._ident = None              # IdentifyResult
        self._result = None             # AnalysisResult
        self._peaks = None              # list[ObservedPeak]
        self._background = None         # 当前谱的背景曲线（显示用）
        self._fit_png: str = ""         # 精修完成时快照的拟合图（报告用）
        self._file_name = ""
        self._last_dir = ""
        self._task: Task | None = None
        self._busy: BusyDialog | None = None
        self._reg = None                # RegistrationManager（仅注册版）
        self._reg_label = None          # 状态栏注册标签
        self._setup_registration()

        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_central()
        self._build_status()
        self.resize(*WINDOW_SIZE)
        self.setMinimumSize(*MIN_WINDOW_SIZE)
        self._load_builtin_structure()
        self.retranslateUi()
        self._update_actions()

    # ------------------------------------------------------------------ #
    # 构建
    # ------------------------------------------------------------------ #
    def _setup_registration(self) -> None:
        """注册版接入家族统一注册机制；内部评估版**不接入**。

        内部评估版的 spec 把本模块 ``excludes`` 掉，因此这里的 import 必须容错：
        少了注册模块也要能启动（这是版次差异，不是故障）。
        """
        from lfp.edition import is_internal

        if is_internal():
            return
        try:
            from lfp.gui.registration import (RegistrationManager,
                                              default_state_path)
        except Exception:                   # noqa: BLE001 - 内部版无此模块
            return
        self._reg = RegistrationManager(APP_NAME,
                                        default_state_path("PolyXRD-LFP"))
        self._sync_registration_language()

    def _sync_registration_language(self) -> None:
        """把界面语言同步给注册模块（它自带 zh/en/ja 三语，与本工程语言码不同）。"""
        if self._reg is None:
            return
        from lfp.gui import registration

        registration.set_language({"zh_CN": "zh", "en_US": "en",
                                  "ja_JP": "ja"}.get(current_language(), "en"))

    def registered_unit(self) -> str | None:
        """已注册的单位部门名称（未注册 / 内部评估版返回 None）。"""
        if self._reg is None or not self._reg.state.registered:
            return None
        return self._reg.state.unit

    def startup_registration_check(self) -> None:
        """启动后的未注册提示（由 __main__ 在主窗口 show 之后调用）。"""
        if self._reg is not None:
            self._reg.startup_check(self)

    def _on_enter_code(self) -> None:
        if self._reg is None:
            return
        from lfp.gui import registration

        state = registration.prompt_for_code(self, self._reg.state_path,
                                            self._reg.app_name)
        if state is not None and state.registered:
            self._reg.refresh()
            if self._reg_label is not None:
                registration.refresh_status_label(self._reg_label, state)
            self._set_status("status.registered", unit=state.unit)

    def _build_actions(self) -> None:
        """全部 QAction（文案统一在 retranslateUi 里设置）。"""
        self.act_open = QAction(self)
        self.act_open.setShortcut("Ctrl+O")
        self.act_open.triggered.connect(self._on_open)

        self.act_export_html = QAction(self)
        self.act_export_html.setShortcut("Ctrl+S")
        self.act_export_html.triggered.connect(self._on_export_html)
        self.act_export_csv = QAction(self)
        self.act_export_csv.triggered.connect(self._on_export_summary)
        self.act_export_pattern = QAction(self)
        self.act_export_pattern.triggered.connect(self._on_export_pattern)
        self.act_export_bragg = QAction(self)
        self.act_export_bragg.triggered.connect(self._on_export_bragg)
        self.act_export_peaks = QAction(self)
        self.act_export_peaks.triggered.connect(self._on_export_peaks)
        self.act_export_png = QAction(self)
        self.act_export_png.triggered.connect(self._on_export_png)
        self.act_exit = QAction(self)
        self.act_exit.triggered.connect(self.close)

        self.act_smooth = QAction(self)
        self.act_smooth.triggered.connect(self._on_smooth)
        self.act_bg = QAction(self)
        self.act_bg.triggered.connect(self._on_background)
        self.act_ka2 = QAction(self)
        self.act_ka2.triggered.connect(self._on_ka2)
        self.act_peaks = QAction(self)
        self.act_peaks.triggered.connect(self._on_find_peaks)
        self.act_reset = QAction(self)
        self.act_reset.triggered.connect(self._on_reset)

        self.act_show_fit = QAction(self)
        self.act_show_fit.triggered.connect(self._show_fit_view)
        self.act_show_spec = QAction(self)
        self.act_show_spec.triggered.connect(self._redraw_canvas)

        self.act_about = QAction(self)
        self.act_about.triggered.connect(
            lambda: AboutDialog(self, reg_unit=self.registered_unit()).exec())
        self.act_copyright = QAction(self)
        self.act_copyright.triggered.connect(
            lambda: CopyrightDialog(self).exec())
        # 输入注册码（仅注册版存在；内部评估版 self._reg 为 None）
        self.act_register = QAction(self)
        self.act_register.triggered.connect(self._on_enter_code)
        self.act_register.setVisible(self._reg is not None)

        self.lang_group = QActionGroup(self)
        self.lang_group.setExclusive(True)
        self.act_langs: dict[str, QAction] = {}
        for code in LANG_ORDER:
            act = QAction(self)
            act.setCheckable(True)
            act.triggered.connect(lambda _c=False, c=code: self._on_language(c))
            self.lang_group.addAction(act)
            self.act_langs[code] = act

    def _build_menus(self) -> None:
        self.menu_file = self.menuBar().addMenu("")
        self.menu_file.addAction(self.act_open)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.act_export_html)
        self.menu_file.addAction(self.act_export_csv)
        self.menu_file.addAction(self.act_export_pattern)
        self.menu_file.addAction(self.act_export_bragg)
        self.menu_file.addAction(self.act_export_peaks)
        self.menu_file.addAction(self.act_export_png)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.act_exit)

        self.menu_process = self.menuBar().addMenu("")
        self.menu_process.addAction(self.act_smooth)
        self.menu_process.addAction(self.act_bg)
        self.menu_process.addAction(self.act_ka2)
        self.menu_process.addSeparator()
        self.menu_process.addAction(self.act_peaks)
        self.menu_process.addAction(self.act_reset)

        self.menu_view = self.menuBar().addMenu("")
        self.menu_view.addAction(self.act_show_fit)
        self.menu_view.addAction(self.act_show_spec)

        self.menu_language = self.menuBar().addMenu("")
        for code in LANG_ORDER:
            self.menu_language.addAction(self.act_langs[code])

        self.menu_help = self.menuBar().addMenu("")
        self.menu_help.addAction(self.act_about)
        self.menu_help.addAction(self.act_copyright)
        if self._reg is not None:
            self.menu_help.addSeparator()
            self.menu_help.addAction(self.act_register)

    def _build_toolbar(self) -> None:
        """顶部工具条：一条工作流从左到右排列。"""
        bar = QToolBar(self)
        bar.setMovable(False)
        bar.setToolButtonStyle(Qt.ToolButtonTextOnly)
        bar.addAction(self.act_open)
        bar.addSeparator()
        bar.addAction(self.act_smooth)
        bar.addAction(self.act_bg)
        bar.addAction(self.act_ka2)
        bar.addAction(self.act_peaks)
        bar.addAction(self.act_reset)
        bar.addSeparator()
        bar.addAction(self.act_export_html)
        self.addToolBar(bar)
        self.toolbar = bar

    def _build_central(self) -> None:
        splitter = QSplitter(Qt.Horizontal, self)

        # 左：谱图区
        left = QWidget(self)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.canvas = SpectrumCanvas(left)
        lv.addWidget(self.canvas, 1)
        splitter.addWidget(left)

        # 右：面板栈（可滚动）
        right = QWidget(self)
        rv = QVBoxLayout(right)
        rv.setContentsMargins(8, 8, 8, 8)
        rv.setSpacing(8)
        self.panel_sample = SamplePanel(right)
        self.panel_structure = StructurePanel(right)
        self.panel_structure.import_requested.connect(self._on_import_cif)
        self.panel_verdict = VerdictPanel(right)
        self.panel_verdict.rerun_requested.connect(self._on_rerun_identify)
        self.panel_refine = RefinePanel(right)
        self.panel_refine.run_requested.connect(self._on_run_refine)
        self.panel_refine.cancel_requested.connect(self._on_cancel_refine)
        self.panel_result = ResultPanel(right)
        for w in (self.panel_sample, self.panel_structure, self.panel_verdict,
                  self.panel_refine, self.panel_result):
            rv.addWidget(w)
        rv.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(right)
        # 横向滚动条按需出现：值标签已做省略，正常情况下不该出现；
        # 一旦出现说明面板被压得比内容还窄，此时宁可让用户滚，也不要裁字
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMinimumWidth(PANEL_MIN_WIDTH)
        splitter.addWidget(scroll)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([820, PANEL_MIN_WIDTH])
        self.setCentralWidget(splitter)
        self.splitter = splitter
        self.right_scroll = scroll

        icon = resource_path("app-icon.png")
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

    def _build_status(self) -> None:
        self._status_key: str | None = None
        self._status_kw: dict = {}
        self._status_what_key: str | None = None
        self.lbl_status = QLabel(self)
        self.lbl_file = QLabel(self)
        self.lbl_file.setStyleSheet("color:#64748B;")
        self.statusBar().addWidget(self.lbl_status, 1)
        # 内部评估版标记（注册版不显示：状态栏右侧由注册标签承担）
        from lfp.edition import is_internal

        self.lbl_edition = QLabel(self)
        self.lbl_edition.setStyleSheet("color:#B45309; font-weight:600;")
        self.lbl_edition.setVisible(is_internal())
        self.statusBar().addPermanentWidget(self.lbl_edition, 0)
        self.statusBar().addPermanentWidget(self.lbl_file, 0)
        # 注册版：状态栏最右侧显示「已注册：XXX / 未注册」
        if self._reg is not None:
            self._reg_label = self._reg.attach_status_label(self.statusBar(), self)

    # ------------------------------------------------------------------ #
    # 结构模型
    # ------------------------------------------------------------------ #
    def _load_builtin_structure(self) -> None:
        """载入内置 LFP CIF；失败时不阻塞界面（只是没有结构可用）。"""
        path = builtin_cif_path("lfp")
        try:
            self._struct = parse_cif(path)
        except Exception as exc:                # noqa: BLE001 - 资源缺失也要能启动
            self._struct = None
            self.panel_structure.warn.setText(f"{path.name}: {exc}")
            self.panel_structure.warn.show()
            return
        self._struct_builtin = True
        self.panel_structure.set_structure(self._struct, builtin=True)

    def _on_import_cif(self) -> None:
        start = self._last_dir or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, tr("dlg.import_cif.title"), start, tr("filter.cif"))
        if not path:
            return
        try:
            struct = parse_cif(path)
        except Exception as exc:                # noqa: BLE001
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle(tr("err.cif.title"))
            box.setText(tr("err.cif.text", msg=exc))
            box.setStandardButtons(QMessageBox.Ok)
            box.button(QMessageBox.Ok).setText(tr("btn.ok"))
            box.exec()
            return
        self._struct = struct
        self._struct_builtin = False
        self._last_dir = str(Path(path).parent)
        self.panel_structure.set_structure(struct, builtin=False)
        self._set_status("status.struct_loaded",
                         name=struct.formula or struct.mineral or struct.name)
        # 结构变了，判定结论必须重算（否则会用旧模型的晶胞去精修）
        self._identify()
        self._update_actions()

    # ------------------------------------------------------------------ #
    # 导入与判定
    # ------------------------------------------------------------------ #
    def _on_open(self) -> None:
        start = self._last_dir or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, tr("dlg.open.title"), start, tr("filter.pattern"))
        if path:
            self._load_pattern(path)

    def _load_pattern(self, path: str) -> None:
        self._set_status("status.loading")
        QApplication.processEvents()
        try:
            pat = read_pattern(path)
        except Exception as exc:                # noqa: BLE001
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle(tr("err.open.title"))
            box.setText(tr("err.open.text", msg=exc))
            box.setDetailedText(tr("err.open.hint"))
            box.setStandardButtons(QMessageBox.Ok)
            box.button(QMessageBox.Ok).setText(tr("btn.ok"))
            box.exec()
            self._set_status("status.ready")
            return

        # 新数据到达：上一条谱的全部派生结果作废
        self._pattern_raw = pat
        self._pattern = pat
        self._background = None
        self._peaks = None
        self._result = None
        self._fit_png = ""
        self._file_name = Path(path).name
        self._last_dir = str(Path(path).parent)
        self.panel_result.clear()
        self.panel_refine.set_range(float(pat.two_theta[0]),
                                    float(pat.two_theta[-1]))
        meta = dict(pat.meta or {})
        meta.setdefault("points", int(pat.two_theta.size))
        meta.setdefault("range", (float(pat.two_theta[0]),
                                  float(pat.two_theta[-1])))
        meta.setdefault("step_hint", float(pat.step))
        self.panel_sample.set_metadata(meta, self._file_name)
        self._set_status("status.loaded", name=self._file_name,
                         n=int(pat.two_theta.size),
                         lo=float(pat.two_theta[0]),
                         hi=float(pat.two_theta[-1]))
        self._redraw_canvas()
        self._identify()          # 判定内部会按结论改写状态栏
        self._update_actions()

    def _identify(self) -> None:
        """对原始谱做 LiFePO4 判定；不是则弹窗并锁死精修。"""
        self._ident = None
        self.panel_verdict.clear()
        if self._pattern_raw is None or self._struct is None:
            self._update_actions()
            return
        self._set_status("status.identifying")
        self.panel_verdict.set_busy(True)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            res = identify_pattern(self._pattern_raw, self._struct)
        except Exception as exc:                # noqa: BLE001
            self.panel_verdict.set_busy(False)
            self._show_error(tr("err.refine.title"), tr("err.refine.text", msg=exc))
            self._update_actions()
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._ident = res
        self.panel_verdict.set_busy(False)
        self.panel_verdict.set_result(res)
        if res.is_lfp:
            self._set_status("status.lfp")
        else:
            self._set_status("status.non_lfp")
            show_not_lfp(self, res)             # 纪律：立即终止后续操作
        self._redraw_canvas()
        self._update_actions()

    def _on_rerun_identify(self) -> None:
        self._identify()

    # ------------------------------------------------------------------ #
    # 谱图处理
    # ------------------------------------------------------------------ #
    def _apply_processed(self, pat, what_key: str) -> None:
        self._pattern = pat
        self._peaks = None
        self._redraw_canvas()
        self._set_status("status.processed", what_key=what_key)
        self._update_actions()

    def _on_smooth(self) -> None:
        if self._pattern is None:
            self._show_error(tr("err.no_data.title"), tr("err.no_data.text"))
            return
        dlg = SmoothDialog(self)
        if dlg.exec() != SmoothDialog.Accepted:
            return
        window, order = dlg.values()
        if window % 2 == 0:
            window += 1                         # SG 窗口必须为奇数
        y = savgol(np.asarray(self._pattern.intensity), window, order)
        self._apply_processed(self._with_intensity(y, "smooth"), "menu.process.smooth")

    def _on_background(self) -> None:
        if self._pattern is None:
            self._show_error(tr("err.no_data.title"), tr("err.no_data.text"))
            return
        dlg = BackgroundDialog(self)
        if dlg.exec() != BackgroundDialog.Accepted:
            return
        method, iterations, order = dlg.values()
        bg = estimate_background(self._pattern, method, iterations=iterations,
                                 order=order)
        self._background = bg
        if method == "linear":
            # 端点线性背景只用于「看」，不改变强度分布
            self._redraw_canvas()
        else:
            self._pattern = subtract(self._pattern, bg)
            self._peaks = None
            self._redraw_canvas()
        self._set_status("status.processed", what_key=f"bg.{method}")
        self._update_actions()

    def _on_ka2(self) -> None:
        if self._pattern is None:
            self._show_error(tr("err.no_data.title"), tr("err.no_data.text"))
            return
        default_anode = str((self._pattern_raw.meta or {}).get("anode") or "Cu")
        if default_anode not in KA1:
            default_anode = "Cu"
        dlg = Ka2Dialog(self, anode=default_anode)
        if dlg.exec() != Ka2Dialog.Accepted:
            return
        anode, ratio = dlg.values()
        self._apply_processed(strip_kalpha2(self._pattern, anode, ratio),
                              "menu.process.ka2")

    def _on_find_peaks(self) -> None:
        if self._pattern is None:
            self._show_error(tr("err.no_data.title"), tr("err.no_data.text"))
            return
        self._set_status("menu.process.peaks")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            peaks = find_peaks(self._pattern, background=self._background)
        except Exception as exc:                # noqa: BLE001
            self._show_error(tr("err.refine.title"), tr("err.refine.text", msg=exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._peaks = list(peaks)
        if not peaks:
            self._set_status("err.peaks_empty")
        else:
            self._set_status("status.processed", what_key="menu.process.peaks")
            self.lbl_status.setText(f"{tr('menu.process.peaks')} · {len(peaks)}")
        self._redraw_canvas()
        self._update_actions()

    def _on_reset(self) -> None:
        if self._pattern_raw is None:
            return
        self._pattern = self._pattern_raw
        self._background = None
        self._peaks = None
        self._set_status("status.reset")
        self._redraw_canvas()
        self._update_actions()

    def _with_intensity(self, y, tag: str):
        """用新强度构造同一条谱（保留 2θ / meta，并记录处理标记）。"""
        from lfp.core.dtypes import Pattern
        meta = dict(self._pattern.meta or {})
        meta["processed"] = tag
        return Pattern(self._pattern.two_theta, np.asarray(y, dtype=np.float64),
                       meta)

    # ------------------------------------------------------------------ #
    # 精修
    # ------------------------------------------------------------------ #
    def _on_run_refine(self) -> None:
        if self._pattern_raw is None or self._struct is None:
            self._show_error(tr("err.no_data.title"), tr("err.no_data.text"))
            return
        if self._ident is None or not self._ident.is_lfp:
            # 纪律兜底：没通过判定绝不进精修（按钮本就禁用，这里再挡一次）
            if self._ident is not None:
                show_not_lfp(self, self._ident)
            return
        cfg_kw = self.panel_refine.config_dict()
        cfg = RefineConfig(**cfg_kw)
        # 精修范围：用户可在面板里收窄；始终对**原始谱**做，不用平滑谱
        pattern = crop(self._pattern_raw, cfg.tmin, cfg.tmax)
        struct = self._struct
        ident = self._ident

        def job(emit, is_canceled):
            return run_analysis(pattern, struct, cfg, ident=ident,
                                check_lfp=True, progress_cb=emit,
                                cancel_cb=is_canceled)

        self.panel_refine.set_busy(True)
        self.panel_refine.set_status(tr("status.refining"))
        self._set_status("status.refining")
        self._task = Task(job, self)
        self._task.progress.connect(self._on_task_progress)
        self._task.ok.connect(self._on_refine_ok)
        self._task.err.connect(self._on_refine_err)
        self._busy = BusyDialog(self, tr("status.refining"))
        self._busy.canceled = self._task.request_cancel
        self._task.start()
        self._busy.exec()

    def _on_cancel_refine(self) -> None:
        if self._task is not None:
            self._task.request_cancel()
            self.panel_refine.set_status(tr("busy.canceling"))

    def _on_task_progress(self, msg: str, pct) -> None:
        if self._busy is not None:
            self._busy.set_progress(msg, pct)
        self.panel_refine.set_status(msg)

    def _on_refine_ok(self, result) -> None:
        self._close_busy()
        self._result = result
        self.panel_refine.set_busy(False)
        self.panel_refine.set_status("")
        self.panel_result.set_result(result)
        self._show_fit_view(snapshot=True)
        self._set_status("status.refined", rwp=result.rwp, gof=result.gof,
                         sec=result.elapsed_s)
        self._update_actions()

    def _on_refine_err(self, exc) -> None:
        self._close_busy()
        self.panel_refine.set_busy(False)
        self.panel_refine.set_status("")
        if isinstance(exc, (RefineCanceled, NotLFPError)):
            self._set_status("status.canceled" if isinstance(exc, RefineCanceled)
                             else "status.non_lfp")
            return
        self._show_error(tr("err.refine.title"), tr("err.refine.text", msg=exc))
        self._set_status("status.ready")

    def _close_busy(self) -> None:
        if self._busy is not None:
            self._busy.accept()
            self._busy = None
        if self._task is not None:
            self._task.wait(2000)
            self._task = None

    # ------------------------------------------------------------------ #
    # 画布
    # ------------------------------------------------------------------ #
    def _redraw_canvas(self) -> None:
        """单谱态重绘：当前谱 + 背景 + 寻峰标记 + LFP 参考峰刻线。"""
        if self._pattern is None:
            self.canvas.clear()
            return
        markers = None
        if self._ident is not None and self._ident.ref_table is not None:
            table = self._ident.ref_table
            try:
                inten = np.asarray(table.intensity, dtype=np.float64)
                tt = np.asarray(table.two_theta, dtype=np.float64)
                if inten.size:
                    keep = inten >= 0.05 * float(np.max(inten))
                    markers = [(float(p), None) for p in tt[keep][:60]]
            except Exception:                   # noqa: BLE001 - 标记画不出也无妨
                markers = None
        title = self._file_name or None
        self.canvas.show_spectrum(
            self._pattern.two_theta, self._pattern.intensity,
            background=self._background, title=title, peaks=self._peaks,
            markers=markers)

    def _show_fit_view(self, snapshot: bool = False) -> None:
        """拟合态重绘（obs / calc / 差值 + 布拉格刻线）。"""
        if self._result is None:
            self._redraw_canvas()
            return
        res = self._result
        bragg = None
        if res.bragg is not None and len(res.bragg.two_theta):
            bragg = np.asarray(res.bragg.two_theta, dtype=np.float64)
        self.canvas.show_fit(res.two_theta, res.yobs, res.ycalc, res.diff,
                             background=res.background, bragg=bragg,
                             title=self._file_name or None)
        if snapshot:
            # 报告用的拟合图在此刻定格：之后用户再处理谱图也不会污染报告
            tmp = Path(tempfile.gettempdir()) / "polyxrd-lfp-fit.png"
            try:
                self.canvas.save_png(str(tmp), dpi=REPORT_FIG_DPI)
                self._fit_png = str(tmp)
            except Exception:                   # noqa: BLE001
                self._fit_png = ""

    # ------------------------------------------------------------------ #
    # 导出
    # ------------------------------------------------------------------ #
    def _sample_name(self) -> str:
        name = self.panel_sample.sample_name()
        if name:
            return name
        return Path(self._file_name).stem if self._file_name else "sample"

    def _on_export_html(self) -> None:
        if self._result is None:
            self._show_error(tr("err.no_data.title"), tr("err.no_result.text"))
            return
        default = str(Path(self._last_dir or Path.home())
                      / f"{self._sample_name()}_LFP_report.html")
        path, _ = QFileDialog.getSaveFileName(
            self, tr("dlg.save.report"), default, tr("filter.html"))
        if not path:
            return
        png = png_to_b64(self._fit_png) if self._fit_png else ""
        html = build_html_report(
            result=self._result, sample=self._sample_name(),
            file_name=self._file_name,
            cfg_rows=self.panel_refine.config_rows(), png_b64=png)
        exports.write_text(path, html)
        self._set_status("status.exported", path=path)

    def _on_export_summary(self) -> None:
        if self._result is None:
            self._show_error(tr("err.no_data.title"), tr("err.no_result.text"))
            return
        default = str(Path(self._last_dir or Path.home())
                      / f"{self._sample_name()}_LFP_summary.csv")
        path, _ = QFileDialog.getSaveFileName(
            self, tr("dlg.save.csv"), default, tr("filter.csv"))
        if not path:
            return
        meta = dict(getattr(self._pattern_raw, "meta", {}) or {})
        rows = exports.summary_rows(self._result, self._sample_name(),
                                    self._file_name, meta)
        exports.write_summary_csv(path, rows)
        self._set_status("status.exported", path=path)

    def _on_export_pattern(self) -> None:
        if self._result is None:
            self._show_error(tr("err.no_data.title"), tr("err.no_result.text"))
            return
        default = str(Path(self._last_dir or Path.home())
                      / f"{self._sample_name()}_LFP_fit.csv")
        path, _ = QFileDialog.getSaveFileName(
            self, tr("dlg.save.csv"), default, tr("filter.csv"))
        if not path:
            return
        exports.write_pattern_csv(path, self._result)
        self._set_status("status.exported", path=path)

    def _on_export_bragg(self) -> None:
        if self._result is None:
            self._show_error(tr("err.no_data.title"), tr("err.no_result.text"))
            return
        default = str(Path(self._last_dir or Path.home())
                      / f"{self._sample_name()}_LFP_bragg.csv")
        path, _ = QFileDialog.getSaveFileName(
            self, tr("dlg.save.csv"), default, tr("filter.csv"))
        if not path:
            return
        exports.write_bragg_csv(path, self._result)
        self._set_status("status.exported", path=path)

    def _on_export_peaks(self) -> None:
        if not self._peaks:
            self._show_error(tr("err.no_data.title"), tr("err.peaks_empty"))
            return
        default = str(Path(self._last_dir or Path.home())
                      / f"{self._sample_name()}_peaks.csv")
        path, _ = QFileDialog.getSaveFileName(
            self, tr("dlg.save.csv"), default, tr("filter.csv"))
        if not path:
            return
        exports.write_peaks_csv(path, self._peaks)
        self._set_status("status.exported", path=path)

    def _on_export_png(self) -> None:
        if self._pattern is None and self._result is None:
            self._show_error(tr("err.no_data.title"), tr("err.no_data.text"))
            return
        default = str(Path(self._last_dir or Path.home())
                      / f"{self._sample_name()}.png")
        path, _ = QFileDialog.getSaveFileName(
            self, tr("dlg.save.png"), default, tr("filter.png"))
        if not path:
            return
        self.canvas.save_png(path)
        self._set_status("status.exported", path=path)

    # ------------------------------------------------------------------ #
    # 语言与文案
    # ------------------------------------------------------------------ #
    def _on_language(self, code: str) -> None:
        if code == current_language():
            return
        set_language(code)
        save_language(code)
        # Qt 标准按钮（Show Details… 等）跟随语言重装翻译
        from lfp.gui.qt_translations import install as install_qt_translations

        install_qt_translations(QApplication.instance())
        # 注册模块自带三语文案，语言切换后同步并刷新状态栏标签
        self._sync_registration_language()
        if self._reg is not None and self._reg_label is not None:
            from lfp.gui import registration

            registration.refresh_status_label(self._reg_label,
                                              self._reg.state)
        self.retranslateUi()
        # 已算出的结果按新语言重新贴一遍（数值不变，标签/晶系名要换语言）
        if self._struct is not None:
            self.panel_structure.set_structure(self._struct,
                                               builtin=self._struct_builtin)
        if self._ident is not None:
            self.panel_verdict.set_result(self._ident)
        if self._result is not None:
            self.panel_result.set_result(self._result)
        self._redraw_canvas()

    def retranslateUi(self) -> None:
        """刷新全部文案（菜单、工具条、面板、画布、状态栏）。"""
        self.setWindowTitle(f"{APP_NAME} v{__version__} · {tr('app.title')}")
        self.menu_file.setTitle(tr("menu.file"))
        self.menu_process.setTitle(tr("menu.process"))
        self.menu_view.setTitle(tr("menu.view"))
        self.menu_language.setTitle(tr("menu.language"))
        self.menu_help.setTitle(tr("menu.help"))

        self.act_open.setText(tr("menu.file.open"))
        self.act_export_html.setText(tr("menu.file.export_html"))
        self.act_export_csv.setText(tr("menu.file.export_csv"))
        self.act_export_pattern.setText(tr("menu.file.export_pattern"))
        self.act_export_bragg.setText(tr("menu.file.export_bragg"))
        self.act_export_peaks.setText(tr("menu.file.export_peaks"))
        self.act_export_png.setText(tr("menu.file.export_png"))
        self.act_exit.setText(tr("menu.file.exit"))

        self.act_smooth.setText(tr("menu.process.smooth"))
        self.act_bg.setText(tr("menu.process.background"))
        self.act_ka2.setText(tr("menu.process.ka2"))
        self.act_peaks.setText(tr("menu.process.peaks"))
        self.act_reset.setText(tr("menu.process.reset"))

        self.act_show_fit.setText(tr("menu.view.fit"))
        self.act_show_spec.setText(tr("menu.view.spectrum"))
        self.act_about.setText(tr("menu.help.about"))
        self.act_copyright.setText(tr("menu.help.copyright"))
        # 注册码菜单项文案由注册模块自己的三语表提供（家族统一措辞）。
        # 内部评估版的 spec 排除了该模块，故只在注册版（_reg 已创建）里导入。
        if self._reg is not None:
            from lfp.gui import registration

            self.act_register.setText(registration.tr("输入注册码 (&R)…"))
        self.act_register.setVisible(self._reg is not None)
        from lfp.edition import edition_key

        self.lbl_edition.setText(tr(edition_key()))

        # 工具条上重复出现的动作换用短文案
        self.act_open.setIconText(tr("toolbar.open"))
        self.act_export_html.setIconText(tr("toolbar.export"))

        names = available_languages()
        for code, act in self.act_langs.items():
            act.setText(names.get(code, code))
            act.setChecked(code == current_language())

        for panel in (self.panel_sample, self.panel_structure,
                      self.panel_verdict, self.panel_refine, self.panel_result):
            panel.retranslate()
        self.canvas.retranslate()
        self.lbl_file.setText(self._file_name or "")
        self.lbl_status.setText(self._status_text())

    # ------------------------------------------------------------------ #
    # 状态与动作可用性
    # ------------------------------------------------------------------ #
    def _set_status(self, key: str, *, what_key: str | None = None, **kw) -> None:
        """设置状态栏消息。

        存的是 **i18n 键**（不是成品文本），语言切换时 :meth:`retranslateUi`
        才能把状态栏一起重刷——否则切到英文后状态栏还留着中文，看起来像漏译。
        ``what_key`` 用于「已应用：<动作名>」这类需要二次翻译的嵌套文案。
        """
        self._status_key = key
        self._status_kw = dict(kw)
        self._status_what_key = what_key
        self.lbl_status.setText(self._status_text())

    def _status_text(self) -> str:
        if self._status_key is None:
            return tr("status.ready")
        kw = dict(self._status_kw)
        if self._status_what_key:
            kw["what"] = tr(self._status_what_key)
        return tr(self._status_key, **kw)

    def _show_error(self, title: str, text: str) -> None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(title)
        box.setText(text)
        box.setStandardButtons(QMessageBox.Ok)
        box.button(QMessageBox.Ok).setText(tr("btn.ok"))
        box.exec()

    def _update_actions(self) -> None:
        """按当前状态启用/禁用动作（唯一入口，避免各处各改一半）。"""
        has_pattern = self._pattern is not None
        has_result = self._result is not None
        is_lfp = bool(self._ident is not None and self._ident.is_lfp)
        busy = self._task is not None

        for act in (self.act_smooth, self.act_bg, self.act_ka2,
                    self.act_peaks, self.act_reset, self.act_export_png):
            act.setEnabled(has_pattern and not busy)
        self.act_export_peaks.setEnabled(bool(self._peaks) and not busy)
        for act in (self.act_export_html, self.act_export_csv,
                    self.act_export_pattern, self.act_export_bragg):
            act.setEnabled(has_result and not busy)
        self.act_show_fit.setEnabled(has_result)
        self.act_show_spec.setEnabled(has_pattern)
        self.panel_refine.set_runnable(has_pattern and is_lfp and not busy)
        self.lbl_file.setText(self._file_name or "")

    # ------------------------------------------------------------------ #
    def closeEvent(self, event) -> None:        # noqa: N802 - Qt 回调
        """关窗前停掉后台精修，避免线程在解释器退出时被打断。"""
        if self._task is not None:
            self._task.request_cancel()
            self._task.wait(2000)
        super().closeEvent(event)
