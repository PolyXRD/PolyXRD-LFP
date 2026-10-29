"""谱图画布（matplotlib）。

两种显示状态
------------
- **单谱态**：实测谱 + （可选）背景曲线 + （可选）寻峰标记；
- **拟合态**：上 2/3 实测散点 + 理论曲线 + 背景虚线 + 布拉格位置刻度，
  下 1/3 差值线（实测 − 理论），共用 x 轴。

配色与家族一致（RutAna v1.2.0 起冻结）：实测蓝、理论墨黑、差值红、
布拉格刻线青；网格浅灰、图例无边框。
"""

from __future__ import annotations

import warnings

import numpy as np
import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

matplotlib.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

from lfp.i18n import tr

INK = "#0F172A"       # 墨黑：理论曲线
OBS = "#0284C7"       # 蓝：实测
DIFF = "#DC2626"      # 红：差值
GRID = "#CBD5E1"      # 浅灰：网格
BKG = "#94A3B8"       # 灰：背景
TICK = "#22D3EE"      # 青：布拉格位置
PEAK = "#B45309"      # 琥珀：寻峰标记
EMPTY = "#64748B"


def _tight(fig: Figure) -> None:
    """尽力做紧凑布局，失败时静默（画布很窄时 matplotlib 会抛 UserWarning）。

    窗口刚创建、画布尺寸还是 0 时 ``tight_layout`` 无法分配到足够边距，
    matplotlib 只发一条 UserWarning 且布局仍可用；直接吞掉它，避免打包版
    在控制台/日志里刷无意义的告警。
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        try:
            fig.tight_layout()
        except Exception:
            pass


class SpectrumCanvas(FigureCanvasQTAgg):
    """谱图显示画布。"""

    def __init__(self, parent=None) -> None:
        self.figure = Figure(figsize=(6.4, 5.0), dpi=100)
        super().__init__(self.figure)
        self.setParent(parent)
        self.ax_main = self.figure.add_subplot(111)
        self.ax_diff = None
        self._state: tuple | None = None     # ("spectrum"|"fit", 数据...) 语言切换重绘
        self._show_empty()
        _tight(self.figure)

    # ------------------------------------------------------------------ #
    # 绘制
    # ------------------------------------------------------------------ #
    def show_spectrum(self, two_theta, intensity, *, background=None,
                      title: str | None = None, peaks=None,
                      markers=None, ylabel: str | None = None) -> None:
        """单谱显示。

        peaks   : 寻峰结果（ObservedPeak 列表），在峰顶标三角
        markers : [(2θ, 标签)]，用于标注物相参考峰（判定阶段）
        """
        self._state = ("spectrum", np.asarray(two_theta), np.asarray(intensity),
                       None if background is None else np.asarray(background),
                       title, peaks, markers, ylabel)
        self._draw_spectrum(*self._state[1:])

    def show_fit(self, two_theta, yobs, ycalc, diff, *, background=None,
                 bragg=None, title: str | None = None) -> None:
        """拟合叠加显示（obs/calc/bg + 布拉格刻线 + 差值）。"""
        self._state = ("fit", np.asarray(two_theta), np.asarray(yobs),
                       np.asarray(ycalc), np.asarray(diff),
                       None if background is None else np.asarray(background),
                       None if bragg is None else np.asarray(bragg), title)
        self._draw_fit(*self._state[1:])

    def clear(self) -> None:
        self._state = None
        self.figure.clf()
        self.ax_main = self.figure.add_subplot(111)
        self.ax_diff = None
        self._show_empty()
        _tight(self.figure)
        self.draw_idle()

    def save_png(self, path: str, dpi: int = 200) -> None:
        self.figure.savefig(path, dpi=dpi, facecolor="white", bbox_inches="tight")

    def retranslate(self) -> None:
        """语言切换后按缓存数据重绘（轴标签/图例换语言）。"""
        if self._state is None:
            self.clear()
            return
        kind = self._state[0]
        if kind == "spectrum":
            self._draw_spectrum(*self._state[1:])
        else:
            self._draw_fit(*self._state[1:])

    # ------------------------------------------------------------------ #
    # 内部
    # ------------------------------------------------------------------ #
    def _draw_spectrum(self, tt, y, background, title, peaks, markers, ylabel):
        self.figure.clf()
        self.ax_main = self.figure.add_subplot(111)
        self.ax_diff = None
        ax = self.ax_main
        ax.plot(tt, y, color=INK, lw=0.9, label=tr("canvas.legend.obs"))
        if background is not None:
            ax.plot(tt, background, color=BKG, lw=0.8, ls="--",
                    label=tr("canvas.legend.bg"))
        if peaks:
            xs = [p.two_theta for p in peaks]
            ys = [p.height + (float(np.interp(p.two_theta, tt, y))) * 0.0
                  for p in peaks]
            # 标记落在观测谱的峰顶：用插值取谱值更稳妥
            ys = [float(np.interp(p.two_theta, tt, y)) for p in peaks]
            ax.plot(xs, ys, linestyle="none", marker="v", ms=4.0,
                    color=PEAK, label=tr("canvas.legend.peaks"))
        if markers:
            ymax = float(np.nanmax(y)) if len(y) else 1.0
            for pos, label in markers:
                ax.axvline(pos, color=TICK, lw=0.7, alpha=0.55, ymax=0.16)
                if label:
                    ax.annotate(label, (pos, ymax * 0.02), rotation=90,
                                fontsize=6.5, color=TICK, ha="center",
                                va="bottom")
        ax.set_xlabel(tr("canvas.x_label"))
        ax.set_ylabel(ylabel or tr("canvas.y_label"))
        ax.grid(True, color=GRID, lw=0.4, alpha=0.5)
        if title:
            ax.set_title(title, fontsize=9, color=EMPTY)
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(loc="upper right", fontsize=8, frameon=False)
        ax.margins(x=0.01)
        _tight(self.figure)
        self.draw_idle()

    def _draw_fit(self, tt, yobs, ycalc, diff, background, bragg, title):
        self.figure.clf()
        self.ax_main, self.ax_diff = self.figure.subplots(
            2, 1, height_ratios=[3, 1], sharex=True)
        ax, axd = self.ax_main, self.ax_diff
        ax.plot(tt, yobs, linestyle="none", marker="x", color=OBS, ms=3.0,
                mew=0.6, label=tr("canvas.legend.obs"))
        ax.plot(tt, ycalc, color=INK, lw=1.0, label=tr("canvas.legend.calc"))
        if background is not None:
            ax.plot(tt, background, color=BKG, lw=0.8, ls="--",
                    label=tr("canvas.legend.bg"))
        if bragg is not None and bragg.size:
            ax_max = float(np.nanmax(np.r_[yobs, ycalc]))
            ax_min = float(np.nanmin(yobs))
            span = ax_max - ax_min if ax_max > ax_min else 1.0
            for pos in bragg:
                ax.plot([pos, pos], [ax_min - 0.035 * span, ax_min - 0.015 * span],
                        color=TICK, lw=0.8, solid_capstyle="butt")
            ax.annotate(tr("canvas.bragg"), (float(tt[0]), ax_min - 0.05 * span),
                        fontsize=7, color=TICK, va="top")
            ax.set_ylim(ax_min - 0.07 * span, ax_max + 0.04 * span)
        ax.set_ylabel(tr("canvas.y_label"))
        ax.grid(True, color=GRID, lw=0.4, alpha=0.5)
        if title:
            ax.set_title(title, fontsize=9, color=EMPTY)
        ax.legend(loc="upper right", fontsize=8, frameon=False)
        ax.tick_params(labelbottom=False)

        axd.plot(tt, diff, color=DIFF, lw=0.7, label=tr("canvas.legend.err"))
        axd.axhline(0.0, color=GRID, lw=0.6)
        axd.set_xlabel(tr("canvas.x_label"))
        axd.set_ylabel(tr("canvas.y_diff"))
        axd.grid(True, color=GRID, lw=0.4, alpha=0.5)
        axd.margins(x=0.01)
        _tight(self.figure)
        self.draw_idle()

    def _show_empty(self) -> None:
        ax = self.ax_main
        ax.set_facecolor("white")
        ax.text(0.5, 0.5, tr("canvas.empty"), ha="center", va="center",
                fontsize=11, color=EMPTY, transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
