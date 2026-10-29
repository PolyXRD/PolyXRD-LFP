"""PyInstaller runtime_hook：内部评估版（单文件 exe，PolyXRD-LFP-Internal.spec）。

在应用代码运行前把版次标识覆写为 internal；注册版（PolyXRD-LFP.spec / Setup）
不加本 hook，保持默认 registered。

为什么用 runtime_hook 而不是编译期常量：``is_internal()`` 在界面里被多处调用，
若在 import 时就把值取死，hook 改不动已展开的常量。因此 lfp/edition.py 只保留
两个模块属性，其余一律通过函数读取。
"""

import lfp.edition as _edition

_edition.EDITION = "internal"
_edition.IS_INTERNAL = True
