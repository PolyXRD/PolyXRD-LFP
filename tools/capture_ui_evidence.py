"""生成界面证据截图与报告样本（离屏，无需人工操作）。

产物写入 ``docs/evidence/``：
    ui-spectrum.png   导入后的谱图视图（判定卡片 + 判据）
    ui-fit-view.png   精修后的拟合视图（实测/计算/背景/差值 + Bragg 刻度）
    ui-not-lfp.png    非 LiFePO4 拦截弹窗（含未通过判据）
    ui-english.png    英文界面
    ui-japanese.png   日文界面
    smoke-report.html HTML 报告样本（内嵌拟合图）

为什么要脚本化：界面截图是发布证据，必须**可复现**且与当前代码一致。
手工截图会在改动文案/布局后悄悄过期。
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# offscreen 平台默认字体库为空（中文全部渲染成豆腐块）；指向系统字体目录即可
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tests"))

from PySide6.QtWidgets import QApplication, QMessageBox          # noqa: E402

import lfp.gui.dialogs as dialogs                                 # noqa: E402
import lfp.gui.main_window as mw                                  # noqa: E402
from conftest import make_pattern                                 # noqa: E402
from lfp.core.profile.forward import scaled_cell                  # noqa: E402
from lfp.core.profile.cif import parse_cif                        # noqa: E402
from lfp.gui.report import build_html_report, png_to_b64          # noqa: E402
from lfp.gui import exports                                        # noqa: E402
from lfp.i18n import i18n_manager as im                            # noqa: E402

OUT = BASE / "docs" / "evidence"
SIZE = (1420, 920)


def _pump(app: QApplication, n: int = 6) -> None:
    for _ in range(n):
        app.processEvents()
        time.sleep(0.02)


def _shot(widget, path: Path) -> None:
    widget.grab().save(str(path))
    print(f"  -> {path.name} ({path.stat().st_size // 1024} KB)")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication([])

    # 与真实启动一致：安装 Qt 标准按钮翻译（Show Details… 等）
    from lfp.gui.qt_translations import install as install_qt_translations

    install_qt_translations(app)

    # 进度窗与消息框都是模态，离屏下会阻塞；替换掉 exec 才能把流程跑完
    from lfp.gui.dialogs import BusyDialog
    BusyDialog.exec = lambda self: 0                    # type: ignore[method-assign]

    im.set_language("zh_CN")
    w = mw.MainWindow()
    # MainWindow 构造时会 load_language() 恢复用户上次选择；证据截图统一
    # 用中文（英文有单独一张），故在构造后再设一次并重翻译。
    im.set_language("zh_CN")
    w.retranslateUi()
    w.resize(*SIZE)
    w.show()
    _pump(app)
    st = parse_cif(BASE / "lfp/data/lfp.cif")

    # ---- 1. 谱图视图（判定通过） -------------------------------------
    w._pattern_raw = make_pattern(st)
    w._pattern = w._pattern_raw
    w._identify()
    _pump(app)
    _shot(w, OUT / "ui-spectrum.png")

    # ---- 2. 拟合视图（真跑一次精修） ---------------------------------
    w._on_run_refine()
    for _ in range(900):
        app.processEvents()
        if w._result is not None:
            break
        time.sleep(0.02)
    if w._result is None:
        print("[失败] 精修未返回结果，无法生成拟合视图")
        return 1
    _pump(app, 10)
    _shot(w, OUT / "ui-fit-view.png")
    print(f"  精修: Rwp={w._result.rwp:.2f}  GOF={w._result.gof:.3f}")

    # ---- 3. HTML 报告样本 --------------------------------------------
    png = png_to_b64(w._fit_png) if w._fit_png else ""
    html = build_html_report(result=w._result, sample=w._sample_name(),
                             file_name=w._file_name,
                             cfg_rows=w.panel_refine.config_rows(),
                             png_b64=png)
    exports.write_text(str(OUT / "smoke-report.html"), html)
    print(f"  -> smoke-report.html ({(OUT / 'smoke-report.html').stat().st_size // 1024} KB)")

    # ---- 4. 非 LiFePO4 拦截弹窗 --------------------------------------
    shot_box = {"done": False}

    def fake_exec(self):                                # noqa: ANN001
        self.show()
        _pump(app, 8)
        _shot(self, OUT / "ui-not-lfp.png")
        self.close()
        shot_box["done"] = True
        return QMessageBox.Ok

    QMessageBox.exec = fake_exec                        # type: ignore[method-assign]
    w._pattern_raw = make_pattern(scaled_cell(st, 1.01, 1.0, 1.0), zero=0.05)
    w._pattern = w._pattern_raw
    w._identify()
    _pump(app)
    if not shot_box["done"]:
        print("[警告] 未捕获到非 LFP 弹窗")

    # ---- 5. 英文界面 --------------------------------------------------
    im.set_language("en_US")
    w._pattern_raw = make_pattern(st)
    w._pattern = w._pattern_raw
    w._identify()
    _pump(app)
    if w._result is not None:
        w._show_fit_view()
    w.retranslateUi()
    _pump(app, 10)
    _shot(w, OUT / "ui-english.png")

    # ---- 6. 日文界面 --------------------------------------------------
    im.set_language("ja_JP")
    w.retranslateUi()
    _pump(app, 10)
    _shot(w, OUT / "ui-japanese.png")

    im.set_language("zh_CN")
    w.close()
    print("完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
