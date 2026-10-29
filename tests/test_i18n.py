"""三语文案一致性：键集、占位符、以及「界面不出现 ⟪key⟫」。

为什么值得单独测：文案是最容易悄悄坏掉的地方——新增一条 ``tr("...")`` 却忘了
补另外两种语言，界面只在切到那种语言时才露出 ``⟪key⟫``，而日常开发几乎不会切。
"""

from __future__ import annotations

import string

import pytest

from lfp.i18n import i18n_manager as im
from lfp.i18n.translations import en_US, ja_JP, zh_CN

LANGS = {"zh_CN": zh_CN.TRANSLATIONS, "en_US": en_US.TRANSLATIONS,
         "ja_JP": ja_JP.TRANSLATIONS}


def _fields(text: str) -> set[tuple[str, str]]:
    """抽出 ``{name:spec}`` 的 (字段名, 格式规格) 集合。"""
    out: set[tuple[str, str]] = set()
    for _literal, name, spec, _conv in string.Formatter().parse(text):
        if name:
            out.add((name, spec))
    return out


@pytest.mark.parametrize("lang", sorted(LANGS))
def test_key_sets_are_identical(lang):
    """每种语言的键集必须与 zh_CN 完全一致（多键少键都是缺陷）。"""
    base = set(LANGS["zh_CN"])
    assert set(LANGS[lang]) == base, (
        f"{lang} 缺 {sorted(base - set(LANGS[lang]))}；"
        f"多 {sorted(set(LANGS[lang]) - base)}")


@pytest.mark.parametrize("lang", ["en_US", "ja_JP"])
def test_placeholders_match_base(lang):
    """占位符（字段名 + 格式规格）必须与中文一致，否则运行时 .format 抛异常。"""
    bad = [
        key for key in LANGS["zh_CN"]
        if _fields(LANGS["zh_CN"][key]) != _fields(LANGS[lang][key])
    ]
    assert not bad, f"{lang} 占位符与中文不一致：{bad[:10]}"


@pytest.mark.parametrize("lang", sorted(LANGS))
def test_no_empty_translation(lang):
    assert all(v.strip() for v in LANGS[lang].values()), \
        f"{lang} 存在空文案：{[k for k, v in LANGS[lang].items() if not v.strip()]}"


@pytest.mark.parametrize("lang", sorted(LANGS))
def test_tr_never_leaks_key(lang, monkeypatch):
    """关键文案在三种语言下都必须能取到，不能返回 ⟪key⟫。"""
    monkeypatch.setattr(im, "_current", lang)
    keys = ("app.title", "panel.verdict", "row.ident.resid", "stage.full",
            "status.refined", "report.title", "csv.resid_ratio",
            "ident.reason.model", "ident.note.gate")
    for key in keys:
        text = im.tr(key, rms=0.031, tol=0.15, ratio=0.21, rwp=12.76,
                     gof=2.055, sec=3.9)
        assert "⟪" not in text, f"{lang}:{key} -> {text}"


def test_available_languages_are_all_translated():
    """语言菜单里列出的每种语言都要有文案表（否则是死菜单项）。"""
    for code in im.LANGUAGE_NAMES:
        assert code in im.TABLE, f"语言 {code} 没有文案表"
