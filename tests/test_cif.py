"""内置 CIF 的结构自洽性校验。

这些断言把「结构数据对不对」钉死在测试里：晶胞、Wyckoff 展开数、键长区间、
以及 d 值与 PDF 卡片的对应。任何一次误改 lfp.cif 都会在这里立刻红掉。
"""

from __future__ import annotations

import numpy as np
import pytest

from lfp.core.profile.cif import parse_cif
from lfp.core.profile.forward import reflection_table
from lfp.core.refine.nonlinear import initial_params


def test_cell_and_meta(struct):
    a, b, c, al, be, ga = struct.cell
    assert (a, b, c) == pytest.approx((10.329, 6.0065, 4.6908), abs=1e-4)
    assert (al, be, ga) == pytest.approx((90.0, 90.0, 90.0), abs=1e-9)
    assert struct.volume == pytest.approx(291.02, abs=0.1)
    # 元数据归一化：H-M 符号去空格、结构式优先用 _chemical_formula_structural
    assert struct.space_group == "Pnma"
    assert struct.space_group_number == 62
    assert struct.formula == "LiFePO4"
    assert struct.z_formula == 4


def test_symmetry_expansion(struct):
    """6 个不对称单位 + 8 条对称操作 -> 28 个原子（Z=4 的完整单胞）。"""
    assert struct.n_asym == 6
    assert struct.n_sym_ops == 8
    assert len(struct.atoms) == 28

    counts: dict[str, int] = {}
    for atom in struct.atoms:
        counts[atom[0]] = counts.get(atom[0], 0) + 1
    assert counts == {"Li": 4, "Fe": 4, "P": 4, "O": 16}


def _dist(struct, i: int, j: int) -> float:
    pi = np.asarray(struct.atoms[i][1:4], dtype=float)
    pj = np.asarray(struct.atoms[j][1:4], dtype=float)
    d = pi - pj
    d -= np.round(d)                       # 最小镜像
    cell = np.asarray(struct.cell[:3], dtype=float)
    return float(np.linalg.norm(d * cell))


def test_bond_lengths_are_olivine_like(struct):
    """P–O 与 Fe–O 键长必须落在橄榄石型的合理区间。

    这不是「抄卡片」，而是独立的结构合理性检查：原子坐标若抄错一位小数，
    d 值可能还勉强对得上，但 P–O 四面体会立刻变形到 1.7 Å 以上或 1.4 Å 以下。
    """
    idx = {a[0]: [] for a in struct.atoms}
    for i, atom in enumerate(struct.atoms):
        idx[atom[0]].append(i)

    p_o, fe_o = [], []
    for i in idx["P"]:
        d = sorted(_dist(struct, i, j) for j in idx["O"])[:4]
        p_o.extend(d)
    for i in idx["Fe"]:
        d = sorted(_dist(struct, i, j) for j in idx["O"])[:6]
        fe_o.extend(d)

    assert min(p_o) > 1.45 and max(p_o) < 1.65, f"P–O 键长越界: {min(p_o):.3f}–{max(p_o):.3f}"
    assert min(fe_o) > 1.95 and max(fe_o) < 2.35, f"Fe–O 键长越界: {min(fe_o):.3f}–{max(fe_o):.3f}"


def test_d_spacings_match_pdf_card(struct):
    """PDF 40-1499 卡片的前 5 条强线，必须能在计算出的反射里找到对应 d 值。

    反射表里 Kα1/Kα2 是两条独立记录（相同 d、不同 2θ），因此先取唯一 d；
    再用「卡片值 → 最近计算值」的判据而不是按顺序取前 5 条——卡片只列强线，
    而计算表列全部允许反射，顺序本来就不一致。
    """
    prm = initial_params(wavelength=1.54056)
    table = reflection_table(struct, prm, 5.0, 60.0)
    d = np.unique(np.round(np.asarray(table.d, dtype=float), 4))
    # 卡片值：5.1645 / 4.2710 / 3.4808 / 3.0061 / 2.5196
    expect = [5.1645, 4.2710, 3.4808, 3.0061, 2.5196]
    for want in expect:
        got = float(d[np.argmin(np.abs(d - want))])
        assert abs(got - want) < 2e-3, f"卡片 d={want} 在计算反射中无对应（最近 {got}）"


def test_parse_cif_string_roundtrip(struct, tmp_path):
    """字符串解析与文件解析必须得到同一结构（导出/内嵌路径用得到）。"""
    from lfp.core.profile.cif import parse_cif_string

    text = (tmp_path / "x.cif")
    text.write_text((__import__("pathlib").Path(__file__).parent.parent
                     / "lfp" / "data" / "lfp.cif").read_text(encoding="utf-8"),
                    encoding="utf-8")
    again = parse_cif_string(text.read_text(encoding="utf-8"))
    assert again.cell == pytest.approx(struct.cell, abs=1e-9)
    assert len(again.atoms) == len(struct.atoms)
