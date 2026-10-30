"""结果卡片控件：键值行 + 语义色标（家族风格）。

只做「显示」，不做计算——所有数值来自 :mod:`lfp.core` 的结果对象，
界面层不重新算一遍，避免两处口径不一致。

宽度策略
--------
卡片的**值**标签用「可省略」实现：QLabel 的 minimumSizeHint 等于文本宽度，
一个长文件名（``LiFePO4#01##20250520-100220_100.txt``）就能把整个右侧面板
撑得比视口还宽，然后被滚动区裁掉——这不是排版问题而是可见性缺陷。
因此值标签把水平策略设为 ``Ignored``（不参与最小宽度计算），并在尺寸变化时
用 ``elidedText`` 中段省略；完整文本进 tooltip，鼠标悬停可查。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

#: 语义色（浅色主题下的可读对比度）
LEVEL_COLORS = {
    "good": "#15803D",      # 绿：达标
    "fair": "#1D4ED8",      # 蓝：良好
    "warn": "#B45309",      # 琥珀：尚可
    "bad": "#B91C1C",       # 红：不佳
    "neutral": "#0F172A",   # 墨：中性
}
VALUE_COLOR = "#0F172A"
KEY_COLOR = "#64748B"
NA_COLOR = "#94A3B8"

#: 值文本超过该长度才提示完整内容（短文本弹 tooltip 反而碍事）
_TOOLTIP_MIN_CHARS = 18

#: 内嵌卡片（QGroupBox）去边框的样式。
#: **只用 `border:0` 时 Qt 的 QStyleSheetStyle 不预留标题高度**，分组标题会
#: 直接压在第一行数据上（「晶胞参数」盖住 `a = …`、「测量条件」盖住「数据文件」）。
#: 带标题的卡片必须同时给 `margin-top` 并把 `::title` 定位到 margin 区。
CARD_QSS_FLAT = "QGroupBox{border:0;}"
CARD_QSS_TITLED = (
    "QGroupBox{border:0; margin-top:13px;}"
    "QGroupBox::title{subcontrol-origin:margin;"
    "subcontrol-position:top left; left:0px; padding:0 2px;}"
)


class ElidedValueLabel(QLabel):
    """右对齐、可中段省略的值标签（完整文本存 tooltip）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("—", parent)
        self._full = "—"
        self._level: str | None = None
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._apply_style()

    # ------------------------------------------------------------------ #
    def set_full_text(self, text: str, level: str | None = None) -> None:
        """设置完整文本（显示时按当前宽度省略）；level 取 LEVEL_COLORS 的键。"""
        self._full = str(text)
        self._level = level
        self.setToolTip(self._full if len(self._full) >= _TOOLTIP_MIN_CHARS else "")
        self._apply_style()
        self._relayout_text()

    def full_text(self) -> str:
        return self._full

    # ------------------------------------------------------------------ #
    def resizeEvent(self, event) -> None:       # noqa: N802 - Qt 回调
        super().resizeEvent(event)
        self._relayout_text()

    def _relayout_text(self) -> None:
        width = max(self.width() - 2, 24)
        super().setText(
            self.fontMetrics().elidedText(self._full, Qt.ElideMiddle, width))

    def _apply_style(self) -> None:
        color = LEVEL_COLORS.get(self._level or "", VALUE_COLOR)
        if self._full in ("", "—"):
            color = NA_COLOR
        self.setStyleSheet(f"color:{color}; font-weight:600;")


class ResultCard(QGroupBox):
    """一组「标签 → 值」结果行。

    行在构造时按 keys 顺序创建，值先填「—」；:meth:`set_value` 支持语义色。
    """

    def __init__(self, keys: list[str], parent: QWidget | None = None,
                 columns: int = 1) -> None:
        super().__init__(parent)
        self._keys = list(keys)
        self._labels: dict[str, QLabel] = {}
        self._values: dict[str, ElidedValueLabel] = {}
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(2)
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(3)
        for i, key in enumerate(self._keys):
            lbl = QLabel(self)
            lbl.setStyleSheet(f"color:{KEY_COLOR};")
            # 标签保持自然宽度（都是短词），但允许被压缩：长标签在窄面板下
            # 宁可截一点，也不能把整张卡片的宽度顶到视口之外
            lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            lbl.setMinimumWidth(0)
            val = ElidedValueLabel(self)
            r, c = divmod(i, max(columns, 1))
            grid.addWidget(lbl, r, c * 2)
            grid.addWidget(val, r, c * 2 + 1)
            grid.setColumnStretch(c * 2, 0)
            grid.setColumnStretch(c * 2 + 1, 1)
            self._labels[key] = lbl
            self._values[key] = val
        outer.addLayout(grid)
        # 富余高度留在卡片底部：否则网格行会被拉开，行数少的卡片看起来像
        # 排版散了架（样品与测量条件比结构模型少几行，最明显）
        outer.addStretch(1)

    # ------------------------------------------------------------------ #
    def set_value(self, key: str, text: str, level: str | None = None) -> None:
        """设置一行的值；level 取 :data:`LEVEL_COLORS` 的键。"""
        val = self._values.get(key)
        if val is not None:
            val.set_full_text(text, level)

    def value(self, key: str) -> str:
        val = self._values.get(key)
        return val.full_text() if val is not None else ""

    def set_label(self, key: str, text: str) -> None:
        lbl = self._labels.get(key)
        if lbl is not None:
            lbl.setText(text)
            lbl.setToolTip("")

    def clear(self) -> None:
        for val in self._values.values():
            val.set_full_text("—")


class TextBlock(QGroupBox):
    """一块可换行的说明文字（判定结论/提示/注意事项）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setStyleSheet(f"color:{VALUE_COLOR};")
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.label)

    def set_text(self, text: str, level: str | None = None) -> None:
        self.label.setText(text)
        color = LEVEL_COLORS.get(level or "", VALUE_COLOR)
        self.label.setStyleSheet(f"color:{color};")
