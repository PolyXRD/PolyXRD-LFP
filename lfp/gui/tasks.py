"""后台任务线程：把耗时的判定与精修挪出界面线程。

PySide6 的约定：QThread 里跑 Python 重计算会让 GIL 周期性释放，界面仍可响应；
本模块只做「调用 core + 转发信号」，不含任何算法。取消通过 ``cancel_cb``
注入 core，core 在残差评估循环里检查（见 :mod:`lfp.core.refine.nonlinear`）。
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThread, Signal


class Task(QThread):
    """一次后台计算。信号：

    - ``progress(str, object)``  消息 + 进度（0..1 或 None）
    - ``ok(object)``             成功，携带结果对象
    - ``err(object)``            失败，携带异常对象（含 NotLFPError）
    """

    progress = Signal(str, object)
    ok = Signal(object)
    err = Signal(object)

    def __init__(self, fn: Callable[[Callable, Callable], object],
                 parent=None) -> None:
        super().__init__(parent)
        self._fn = fn
        self._canceled = False

    # ------------------------------------------------------------------ #
    def request_cancel(self) -> None:
        self._canceled = True

    def is_canceled(self) -> bool:
        return self._canceled

    def _emit_progress(self, msg: str, pct) -> None:
        self.progress.emit(msg, pct)

    def run(self) -> None:                      # noqa: D401 - Qt 回调
        try:
            result = self._fn(self._emit_progress, self.is_canceled)
        except Exception as exc:                # noqa: BLE001 - 统一转给界面
            self.err.emit(exc)
            return
        self.ok.emit(result)
