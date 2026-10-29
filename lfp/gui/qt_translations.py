"""Qt 标准控件文案的翻译（QMessageBox 的 Show Details…、QFileDialog 按钮等）。

软件自己的文案全部收口于 ``lfp.i18n``；但 Qt 库内置的标准按钮文字由 Qt 自带的
``.qm`` 翻译文件提供，必须在 app 级安装 :class:`QTranslator` 才会生效。语言切换时
卸载旧的、装新的（en_US 为 Qt 默认英文，无需安装）。

打包注意：PySide6 的 ``translations/`` 目录不一定被 PyInstaller 自动收集，
spec 的 datas 需要显式带上（见 PolyXRD-LFP.spec）。
"""

from __future__ import annotations

from PySide6.QtCore import QLibraryInfo, QTranslator
from PySide6.QtWidgets import QApplication

from lfp.i18n.i18n_manager import current_language

#: 当前已安装的翻译器（语言切换时卸载）
_translators: list[QTranslator] = []

#: 语言代码 -> Qt 自带 .qm 基名（en_US 是 Qt 默认语言，不需要装）
_QT_TRANSLATIONS: dict[str, tuple[str, ...]] = {
    "zh_CN": ("qtbase_zh_CN", "qt_zh_CN"),
}


def install(app: QApplication) -> None:
    """按当前语言安装/卸载 Qt 自带翻译。语言切换后需再次调用。"""
    global _translators
    for t in _translators:
        app.removeTranslator(t)
    _translators = []
    base = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    for name in _QT_TRANSLATIONS.get(current_language(), ()):
        t = QTranslator(app)
        if t.load(name, base):
            app.installTranslator(t)
            _translators.append(t)
