"""对称性映射：空间群编号 -> 晶系 / 点群 / 劳厄群 / 布拉维格子。

判定链：ITA 编号分段（不枚举 230 行）→ 点群 → 劳厄群（加反演）→
布拉维格子（点群 7 类 × 带心）。LFP 落点必须是 正交 / mmm / oP。
"""

from __future__ import annotations

import pytest

from lfp.core.symmetry import (
    crystal_system_from_cell,
    describe,
    describe_structure,
    laue_of_point_group,
    number_from_symbol,
)


def test_lfp_symmetry(struct):
    info = describe_structure(struct)
    assert info.space_group == "Pnma"
    assert info.number == 62
    assert info.crystal_system == "orthorhombic"
    assert info.point_group == "mmm"
    assert info.point_group_schoenflies == "D2h"
    assert info.laue_class == "mmm"
    assert info.bravais == "oP"
    assert info.centering == "P"
    assert info.centrosymmetric is True
    assert info.system_label("zh") == "正交"
    assert info.system_label("en") == "Orthorhombic"
    assert "正交" in info.bravais_label("zh")


def test_label_switch_is_language_aware(struct):
    info = describe_structure(struct)
    assert info.system_label("zh_CN") == "正交"
    assert info.system_label("en_US") == "Orthorhombic"


@pytest.mark.parametrize("symbol,number", [
    ("Pnma", 62), ("P n m a", 62), ("Pmnb", 62),      # Pmnb 是等价轴置换设置
    ("P21/c", 14), ("Fm-3m", 225), ("R-3c", 167), ("I4/mmm", 139),
])
def test_symbol_to_number(symbol, number):
    assert number_from_symbol(symbol) == number


def test_point_group_to_laue():
    assert laue_of_point_group("mmm") == "mmm"
    assert laue_of_point_group("4mm") == "4/mmm"
    assert laue_of_point_group("-43m") == "m-3m"


def test_metric_fallback_when_no_symbol():
    """没有空间群信息时按晶胞度规猜晶系（导入的自制 CIF 常缺该字段）。"""
    info = describe(None, None, (10.3, 6.0, 4.69, 90.0, 90.0, 90.0))
    assert info.number is None
    assert info.crystal_system == "orthorhombic"
    assert info.point_group is None       # 不臆造点群
    assert crystal_system_from_cell((5.0, 5.0, 5.0, 90, 90, 90)) == "cubic"
