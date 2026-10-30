"""界面冒烟：版次差异（内部评估 / 注册）、注册标签、三语切换。

离屏运行（``QT_QPA_PLATFORM=offscreen``），不弹任何窗口，可在 CI 跑。
本文件只做「装配是否正确」的检查，不重复 core 的数值验证。
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# 注册模块在离屏/自动化环境本来就跳过启动提示，这里再显式关一次，防止未来改动
os.environ.setdefault("POLYXRD_REG_NO_PROMPT", "1")

from PySide6.QtWidgets import QApplication                      # noqa: E402

import lfp.edition as edition                                   # noqa: E402
import lfp.gui.main_window as mw                                # noqa: E402
from lfp.gui import registration                                # noqa: E402
from lfp.i18n import i18n_manager as im                         # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def isolated(tmp_path, monkeypatch):
    """隔离语言配置与注册状态，避免污染开发者本机。"""
    monkeypatch.setattr(im, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    im.set_language("zh_CN")
    yield tmp_path
    im.set_language("zh_CN")


@pytest.fixture()
def registered(qapp, isolated):
    monkeypatch_edition = pytest.MonkeyPatch()
    monkeypatch_edition.setattr(edition, "EDITION", "registered")
    monkeypatch_edition.setattr(edition, "IS_INTERNAL", False)
    yield
    monkeypatch_edition.undo()


@pytest.fixture()
def internal(qapp, isolated):
    monkeypatch_edition = pytest.MonkeyPatch()
    monkeypatch_edition.setattr(edition, "EDITION", "internal")
    monkeypatch_edition.setattr(edition, "IS_INTERNAL", True)
    yield
    monkeypatch_edition.undo()


def _window():
    w = mw.MainWindow()
    w.retranslateUi()
    return w


# --------------------------------------------------------------------------- #
# 基本装配
# --------------------------------------------------------------------------- #
def test_window_loads_builtin_structure(registered):
    w = _window()
    assert w._struct is not None
    assert w._struct.space_group == "Pnma"
    assert "PolyXRD LFP" in w.windowTitle()
    assert not w.panel_refine.btn_run.isEnabled()   # 没有谱图时不能精修
    w.close()


def test_language_switch_is_complete(registered):
    """三语切换后标题与关键控件都应换语言（不留中文残留）。"""
    w = _window()
    seen = {}
    for code, needle in (("zh_CN", "物相判定"), ("en_US", "phase identification"),
                         ("ja_JP", "相同定")):
        im.set_language(code)
        w.retranslateUi()
        title = w.windowTitle()
        assert needle in title, f"{code}: {title}"
        assert "⟪" not in title
        seen[code] = title
    assert len(set(seen.values())) == 3
    w.close()


# --------------------------------------------------------------------------- #
# 版次：内部评估版不接入注册
# --------------------------------------------------------------------------- #
def test_internal_edition_has_no_registration(internal):
    w = _window()
    assert w._reg is None
    assert w._reg_label is None
    assert w.act_register not in w.menu_help.actions()
    titles = [a.text() for a in w.menu_help.actions() if a.text()]
    assert not any("注册" in t or "Registration" in t for t in titles), titles
    # 状态栏版次标记应显示「内部评估版」
    assert not w.lbl_edition.isHidden()
    assert w.lbl_edition.text() == "内部评估版"
    w.close()


def test_registered_edition_shows_unregistered_then_unit(registered):
    w = _window()
    assert w._reg is not None
    assert w._reg_label is not None
    assert w.registered_unit() is None
    assert w._reg_label.text() == "未注册"
    assert any("注册" in a.text() for a in w.menu_help.actions() if a.text())

    code = registration.generate_code("测试单位")
    registration.save_state(w._reg.state_path, code)
    w._reg.refresh()
    registration.refresh_status_label(w._reg_label, w._reg.state)
    assert w.registered_unit() == "测试单位"
    assert "测试单位" in w._reg_label.text()
    w.close()


def test_registration_code_roundtrip():
    """出码 → 校验 → 归一化容错（与家族密钥一致）。"""
    unit = "岛津企业管理（中国）有限公司"
    code = registration.generate_code(unit)
    assert registration.verify_code(code) == unit
    # 小写/去连字符/无前缀都应能校验
    assert registration.verify_code(code.replace("-", "").lower()) == unit
    assert registration.verify_code("PXRD1-AAAA") is None


# --------------------------------------------------------------------------- #
# 布局：样品/结构在谱图下方（左栏），右栏只留判定/精修/结果
# --------------------------------------------------------------------------- #
def test_left_column_holds_sample_and_structure(registered):
    """1.1.0 起的布局契约：左栏是竖直分割（谱图 + 样品/结构一行），

    右栏（滚动区）只装判定 / 精修 / 结果，避免右侧横向拥挤。
    """
    w = _window()
    # 左栏两块面板的父级是「样品 + 结构」那一行的容器
    row = w.panel_sample.parentWidget()
    assert w.panel_structure.parentWidget() is row
    # 该行容器本身挂在左栏竖直分割器的第 2 格（第 1 格是谱图）
    assert w.left_split.indexOf(row) == 1
    assert w.left_split.widget(0) is w.canvas
    # 右栏滚动区里不应再出现样品/结构面板
    right = w.right_scroll.widget()
    assert w.panel_sample.parentWidget() is not right
    assert w.panel_structure.parentWidget() is not right
    for panel in (w.panel_verdict, w.panel_refine, w.panel_result):
        assert right.isAncestorOf(panel)
    w.close()
