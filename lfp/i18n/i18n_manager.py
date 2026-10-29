"""i18n 管理器（简体中文 / English / 日本語）。

- ``tr(key, **kw)``            查询当前语言文案；缺失返回 ``⟪key⟫``（**不回退**，
                               让漏译在界面与测试里直接暴露）。
- ``set_language(lang)``      运行时切换（未知代码忽略）。
- ``current_language()``      当前语言代码。
- ``available_languages()``   语言代码 -> 原生语言名。
- ``load_language() / save_language()``  持久化到
                               ``%USERPROFILE%/.polyxrd-lfp/config.json``。

界面文案全部收口于 ``lfp/i18n/translations/``，key 用点分命名。
"""

from __future__ import annotations

import json
from pathlib import Path

from lfp.i18n.translations import en_US, ja_JP, zh_CN

TABLE: dict[str, dict[str, str]] = {
    "zh_CN": zh_CN.TRANSLATIONS,
    "en_US": en_US.TRANSLATIONS,
    "ja_JP": ja_JP.TRANSLATIONS,
}

#: 语言代码 -> 原生语言名（语言菜单恒定用原生写法）
LANGUAGE_NAMES: dict[str, str] = {
    "zh_CN": "简体中文",
    "en_US": "English",
    "ja_JP": "日本語",
}

DEFAULT_LANGUAGE = "zh_CN"

#: 语言配置持久化路径（测试可 monkeypatch）
CONFIG_PATH: Path = Path.home() / ".polyxrd-lfp" / "config.json"

_current: str = DEFAULT_LANGUAGE


def available_languages() -> dict[str, str]:
    return dict(LANGUAGE_NAMES)


def current_language() -> str:
    return _current


def set_language(lang: str) -> None:
    global _current
    if lang in TABLE:
        _current = lang


def tr(key: str, **kw) -> str:
    """查询当前语言文案；缺失键返回 ⟪key⟫（不做语言回退）。"""
    text = TABLE.get(_current, {}).get(key)
    if text is None:
        return f"⟪{key}⟫"
    return text.format(**kw) if kw else text


def load_language() -> str:
    global _current
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        lang = str(data.get("language", ""))
    except (OSError, ValueError):
        lang = ""
    if lang in TABLE:
        _current = lang
    return _current


def save_language(lang: str | None = None) -> None:
    global _current
    target = lang if lang is not None else _current
    if target not in TABLE:
        return
    _current = target
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps({"language": target}, ensure_ascii=False, indent=2),
            encoding="utf-8")
    except OSError:
        pass      # 只读环境不影响界面运行
