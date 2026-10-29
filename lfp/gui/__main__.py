"""GUI 入口：``python -m lfp.gui``。

启动流程：QSplashScreen（resources/splash-screen.png，1.2 s 后自动关闭）
→ 主窗口。资源缺失时优雅降级（不阻塞启动）。

打包态（PyInstaller onefile）下 bootloader 解压阶段由 spec 的 ``Splash``
显示同图启动画面（冷启动即显），主窗口 show 后由 :func:`_close_boot_splash`
关闭该下层启动图，与 QSplashScreen（上层）视觉连续；开发态无 ``pyi_splash``
模块，行为与家族其它工具一致。
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from lfp.gui.resources import resource_path
from lfp.version import APP_NAME

#: 启动图展示时长（毫秒）
SPLASH_MS = 1200


def _close_boot_splash() -> None:
    """关闭 PyInstaller bootloader 启动图（仅打包态存在 pyi_splash）。"""
    try:
        import pyi_splash       # type: ignore[import-not-found]

        pyi_splash.close()
    except Exception:
        pass                    # 开发态无该模块 —— 静默跳过


def main() -> int:
    """创建应用、启动图与主窗口，进入事件循环。"""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")

    # Qt 标准按钮文案（Show Details… 等）按语言安装 Qt 自带翻译
    from lfp.gui.qt_translations import install as install_qt_translations

    install_qt_translations(app)

    icon_path = resource_path("app-icon.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # 启动图（资源缺失时跳过）
    splash = None
    splash_path = resource_path("splash-screen.png")
    if splash_path.exists():
        pixmap = QPixmap(str(splash_path))
        if not pixmap.isNull():
            splash = QSplashScreen(pixmap)
            splash.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            splash.show()
            app.processEvents()

    # 延迟导入主窗口，让启动图先出现
    from lfp.gui.main_window import MainWindow

    window = MainWindow()
    window.show()
    _close_boot_splash()
    if splash is not None:
        QTimer.singleShot(SPLASH_MS, splash.close)
    # 注册版：窗口显示后再弹未注册提示（离屏/自动化环境自动跳过）
    QTimer.singleShot(0, window.startup_registration_check)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
