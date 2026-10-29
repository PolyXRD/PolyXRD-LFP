# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（PolyXRD 家族模板，参照 PolyXRD-RutAna.spec）。

产物：单文件（onefile）免安装 exe
- 入口 ``lfp/gui/__main__.py``，等价于 ``python -m lfp.gui``；
- ``datas`` 携带 ``resources/``（品牌资产）与 ``lfp/data/``（内置 LFP CIF）；
  两者缺一不可：缺 resources 则无图标/启动图，缺 lfp/data 则内置结构加载失败
  （``resources.data_dir()`` 在打包态解析到 ``sys._MEIPASS/lfp/data``）；
- bootloader Splash：onefile 解压阶段（数秒）即显示品牌启动图，主窗口就绪后
  由 ``__main__._close_boot_splash()`` 关闭；
- exe 名含版本号，版本从 ``lfp/version.py`` 读取，与 build_exe.bat 的副本逻辑对应。

**版次**：本 spec 产出**注册版**（安装包 payload）——注册机制在位（帮助菜单可输入
注册码、状态栏显示注册单位、未注册时启动提示）。内部评估版由
``PolyXRD-LFP-Internal.spec`` 产出（runtime_hook 覆写版次 + excludes 注册模块）。
"""

import re
from pathlib import Path

import PySide6

_ver = re.search(
    r'__version__\s*=\s*"([^"]+)"',
    Path("lfp/version.py").read_text(encoding="utf-8"),
).group(1)

datas = [("resources", "resources"), ("lfp/data", "lfp/data")]
# Qt 自带翻译（QMessageBox 的 Show Details… 等标准按钮文案）：lfp/gui/qt_translations.py
# 运行时按语言加载。PyInstaller 不保证收集它们，这里显式携带，相对路径保持
# PySide6/translations，使打包态 QLibraryInfo 的查找路径不变。
_pyside_dir = Path(PySide6.__file__).resolve().parent
for _qm in ("qtbase_zh_CN.qm", "qt_zh_CN.qm"):
    if (_pyside_dir / "translations" / _qm).exists():
        datas.append((str(_pyside_dir / "translations" / _qm),
                      "PySide6/translations"))

a = Analysis(
    ["lfp/gui/__main__.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "lfp",
        "lfp.version",
        "lfp.i18n",
        "lfp.i18n.i18n_manager",
        "lfp.i18n.translations.zh_CN",
        "lfp.i18n.translations.en_US",
        # core：衍射内核（与 lfp/core 下模块逐一核对，PyInstaller 静态分析
        # 对「字符串索引/条件 import」不可靠，这里显式补全）
        "lfp.core.dtypes",
        "lfp.core.io",
        "lfp.core.identify",
        "lfp.core.peaks",
        "lfp.core.processing",
        "lfp.core.symmetry",
        "lfp.core.profile.cif",
        "lfp.core.profile.forward",
        "lfp.core.profile.lattice",
        "lfp.core.profile.shape",
        "lfp.core.profile.struct",
        "lfp.core.refine.api",
        "lfp.core.refine.linear",
        "lfp.core.refine.lm",
        "lfp.core.refine.nonlinear",
        "lfp.core.refine.rbragg",
        "lfp.core.refine.rfactors",
        # gui
        "lfp.gui.resources",
        "lfp.gui.tasks",
        "lfp.gui.canvas",
        "lfp.gui.dialogs",
        "lfp.gui.exports",
        "lfp.gui.panels",
        "lfp.gui.report",
        "lfp.gui.verdict",
        "lfp.gui.widgets",
        "lfp.gui.qt_translations",
        "lfp.gui.registration",
        "lfp.gui.main_window",
        # 版次标识（注册版为默认 registered；内部版由 runtime_hook 覆写）
        "lfp.edition",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# bootloader 启动画面：图上已烙品牌与版本号，故不附加文本。
splash = Splash(
    "resources/splash-screen.png",
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    min_font_color="white",
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    splash,
    # splash.binaries 必须作为独立 TOC 传入（PyInstaller 官方模板要求）：
    # 内含 Tcl/Tk 运行时，缺它启动画面会在 onefile 解压期静默失败。
    splash.binaries,
    [],
    name=f"PolyXRD-LFP-v{_ver}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["resources/app-icon.ico"],
)
