"""版次标识：``registered`` = 注册版（安装包）｜``internal`` = 内部评估版（单文件 exe）。

默认 ``registered``：源码运行即注册版行为（帮助菜单含「输入注册码」、状态栏显示
注册单位、未注册时启动提示）。

打包内部评估版时，由 PyInstaller runtime_hook（``installer/rthook_internal.py``）
在应用代码运行前把 ``EDITION`` / ``IS_INTERNAL`` 覆写为 internal：不含注册模块
（spec ``excludes``）、状态栏与「关于」显示「内部评估版」。

为什么把版次做成**运行期可覆写**而不是编译期常量：hook 只能改模块属性，改不了
已展开到调用点的常量；因此除两个标识外，其它一切都要**通过函数读取**当前值，
不要 ``from lfp.edition import IS_INTERNAL`` 后当成常量用。
"""

from __future__ import annotations

#: "registered" | "internal"
EDITION = "registered"
IS_INTERNAL = EDITION == "internal"


def is_internal() -> bool:
    """当前是否为内部评估版（供运行期判断，勿缓存）。"""
    return EDITION == "internal"


def edition_key() -> str:
    """版次的 i18n 键（状态栏与「关于」共用）。"""
    return "about.edition.internal" if EDITION == "internal" else "about.edition.registered"
