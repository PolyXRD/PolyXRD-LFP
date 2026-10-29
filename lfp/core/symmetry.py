"""晶体对称性元数据：晶系 / 点群 / 劳厄群 / 布拉菲格子。

空间群编号 → 点群的对应按 International Tables for Crystallography (ITA)
第 A 卷的**编号分段规律**实现（每个晶系内的点群占据连续的编号区间），
而不是枚举 230 行表格——分段是 ITA 的既定排布，可逐段核对：

=====================================================================
晶系        编号范围    点群区间（ITA 顺序）
=====================================================================
三斜        1–2        1 (1) / -1 (2)
单斜        3–15       2 (3–5) / m (6–9) / 2/m (10–15)
正交        16–74      222 (16–24) / mm2 (25–46) / mmm (47–74)
四方        75–142     4 (75–80) / -4 (81–82) / 4/m (83–88) /
                       422 (89–98) / 4mm (99–110) / -42m (111–122) /
                       4/mmm (123–142)
三方        143–167    3 (143–146) / -3 (147–148) / 32 (149–155) /
                       3m (156–161) / -3m (162–167)
六方        168–194    6 (168–173) / -6 (174) / 6/m (175–176) /
                       622 (177–182) / 6mm (183–186) / -6m2 (187–190) /
                       6/mmm (191–194)
立方        195–230    23 (195–199) / m-3 (200–206) / 432 (207–214) /
                       -43m (215–220) / m-3m (221–230)
=====================================================================

劳厄群 = 点群加反演中心后的 11 个中心对称点群之一（粉末衍射的等价类），
由点群直接映射，见 :func:`laue_of_point_group`。

LiFePO4：空间群 Pnma（No. 62）→ 正交晶系 / 点群 mmm / 劳厄群 mmm /
布拉菲格子 oP（简单正交）。这一组结论与 ITA 及 PDF 卡片 40-1499 的
空间群编号 62 一致。
"""

from __future__ import annotations

from dataclasses import dataclass

#: 晶系名（中文 + 英文 + 三字母缩写）
#: 晶系名：(中文, English, 布拉维首字母)
SYSTEM_NAMES = {
    "triclinic": ("三斜", "Triclinic", "a"),
    "monoclinic": ("单斜", "Monoclinic", "m"),
    "orthorhombic": ("正交", "Orthorhombic", "o"),
    "tetragonal": ("四方", "Tetragonal", "t"),
    "trigonal": ("三方", "Trigonal", "h"),
    "hexagonal": ("六方", "Hexagonal", "h"),
    "cubic": ("立方", "Cubic", "c"),
}

#: 晶系的日文名（日本結晶学会の慣用表記）
SYSTEM_NAMES_JA = {
    "triclinic": "三斜晶系",
    "monoclinic": "単斜晶系",
    "orthorhombic": "斜方晶系",
    "tetragonal": "正方晶系",
    "trigonal": "三方晶系",
    "hexagonal": "六方晶系",
    "cubic": "立方晶系",
}

#: 编号分段：(起始, 终止, 晶系, 点群)
_RANGES: tuple[tuple[int, int, str, str], ...] = (
    (1, 1, "triclinic", "1"),
    (2, 2, "triclinic", "-1"),
    (3, 5, "monoclinic", "2"),
    (6, 9, "monoclinic", "m"),
    (10, 15, "monoclinic", "2/m"),
    (16, 24, "orthorhombic", "222"),
    (25, 46, "orthorhombic", "mm2"),
    (47, 74, "orthorhombic", "mmm"),
    (75, 80, "tetragonal", "4"),
    (81, 82, "tetragonal", "-4"),
    (83, 88, "tetragonal", "4/m"),
    (89, 98, "tetragonal", "422"),
    (99, 110, "tetragonal", "4mm"),
    (111, 122, "tetragonal", "-42m"),
    (123, 142, "tetragonal", "4/mmm"),
    (143, 146, "trigonal", "3"),
    (147, 148, "trigonal", "-3"),
    (149, 155, "trigonal", "32"),
    (156, 161, "trigonal", "3m"),
    (162, 167, "trigonal", "-3m"),
    (168, 173, "hexagonal", "6"),
    (174, 174, "hexagonal", "-6"),
    (175, 176, "hexagonal", "6/m"),
    (177, 182, "hexagonal", "622"),
    (183, 186, "hexagonal", "6mm"),
    (187, 190, "hexagonal", "-6m2"),
    (191, 194, "hexagonal", "6/mmm"),
    (195, 199, "cubic", "23"),
    (200, 206, "cubic", "m-3"),
    (207, 214, "cubic", "432"),
    (215, 220, "cubic", "-43m"),
    (221, 230, "cubic", "m-3m"),
)

#: 点群 → 劳厄群（加反演中心后的 11 个中心对称点群）
_POINT_TO_LAUE = {
    "1": "-1", "-1": "-1",
    "2": "2/m", "m": "2/m", "2/m": "2/m",
    "222": "mmm", "mm2": "mmm", "mmm": "mmm",
    "4": "4/m", "-4": "4/m", "4/m": "4/m",
    "422": "4/mmm", "4mm": "4/mmm", "-42m": "4/mmm", "4/mmm": "4/mmm",
    "3": "-3", "-3": "-3",
    "32": "-3m", "3m": "-3m", "-3m": "-3m",
    "6": "6/m", "-6": "6/m", "6/m": "6/m",
    "622": "6/mmm", "6mm": "6/mmm", "-6m2": "6/mmm", "6/mmm": "6/mmm",
    "23": "m-3", "m-3": "m-3",
    "432": "m-3m", "-43m": "m-3m", "m-3m": "m-3m",
}

#: 点群的 Schönflies 记号（报告里同时给出两种记号，便于与文献对照）
_POINT_SCHOENFLIES = {
    "1": "C1", "-1": "Ci",
    "2": "C2", "m": "Cs", "2/m": "C2h",
    "222": "D2", "mm2": "C2v", "mmm": "D2h",
    "4": "C4", "-4": "S4", "4/m": "C4h",
    "422": "D4", "4mm": "C4v", "-42m": "D2d", "4/mmm": "D4h",
    "3": "C3", "-3": "Ci3", "32": "D3", "3m": "C3v", "-3m": "D3d",
    "6": "C6", "-6": "C3h", "6/m": "C6h",
    "622": "D6", "6mm": "C6v", "-6m2": "D3h", "6/mmm": "D6h",
    "23": "T", "m-3": "Th", "432": "O", "-43m": "Td", "m-3m": "Oh",
}

#: 常见空间群 H-M 符号 → 编号（CIF 只给符号时兜底；覆盖粉末分析高频群）
_SYMBOL_TO_NUMBER = {
    "P1": 1, "P-1": 2, "P2": 3, "P21": 4, "C2": 5, "Pm": 6, "Pc": 7, "Cm": 8,
    "Cc": 9, "P2/m": 10, "P21/m": 11, "C2/m": 12, "P2/c": 13, "P21/c": 14,
    "C2/c": 15, "P222": 16, "P2221": 17, "P21212": 18, "P212121": 19,
    "C2221": 20, "C222": 21, "F222": 22, "I222": 23, "I212121": 24,
    "Pmm2": 25, "Pmc21": 26, "Pcc2": 27, "Pma2": 28, "Pca21": 29, "Pnc2": 30,
    "Pmn21": 31, "Pba2": 32, "Pna21": 33, "Pnn2": 34, "Cmm2": 35, "Cmc21": 36,
    "Ccc2": 37, "Amm2": 38, "Aem2": 39, "Ama2": 40, "Aea2": 41, "Fmm2": 42,
    "Fdd2": 43, "Imm2": 44, "Iba2": 45, "Ima2": 46,
    "Pmmm": 47, "Pnnn": 48, "Pccm": 49, "Pban": 50, "Pmma": 51, "Pnna": 52,
    "Pmna": 53, "Pcca": 54, "Pbam": 55, "Pccn": 56, "Pbcm": 57, "Pnnm": 58,
    "Pmmn": 59, "Pbcn": 60, "Pbca": 61, "Pnma": 62, "Cmcm": 63, "Cmce": 64,
    "Cmmm": 65, "Cccm": 66, "Cmme": 67, "Ccce": 68, "Fmmm": 69, "Fddd": 70,
    "Immm": 71, "Ibam": 72, "Ibca": 73, "Imma": 74,
    "P4": 75, "P41": 76, "P42": 77, "P43": 78, "I4": 79, "I41": 80,
    "P-4": 81, "I-4": 82, "P4/m": 83, "P42/m": 84, "P4/n": 85, "P42/n": 86,
    "I4/m": 87, "I41/a": 88, "P422": 89, "P4212": 90, "P4122": 91,
    "P41212": 92, "P4222": 93, "P42212": 94, "P4322": 95, "P43212": 96,
    "I422": 97, "I4122": 98, "P4mm": 99, "P4bm": 100, "P42cm": 101,
    "P42nm": 102, "P4cc": 103, "P4nc": 104, "P42mc": 105, "P42bc": 106,
    "I4mm": 107, "I4cm": 108, "I41md": 109, "I41cd": 110, "P-42m": 111,
    "P-42c": 112, "P-421m": 113, "P-421c": 114, "P-4m2": 115, "P-4c2": 116,
    "P-4b2": 117, "P-4n2": 118, "I-4m2": 119, "I-4c2": 120, "I-42m": 121,
    "I-42d": 122, "P4/mmm": 123, "P4/mcc": 124, "P4/nbm": 125, "P4/nnc": 126,
    "P4/mbm": 127, "P4/mnc": 128, "P4/nmm": 129, "P4/ncc": 130, "P42/mmc": 131,
    "P42/mcm": 132, "P42/nbc": 133, "P42/nnm": 134, "P42/mbc": 135,
    "P42/mnm": 136, "P42/nmc": 137, "P42/ncm": 138, "I4/mmm": 139,
    "I4/mcm": 140, "I41/amd": 141, "I41/acd": 142,
    "P3": 143, "P31": 144, "P32": 145, "R3": 146, "P-3": 147, "R-3": 148,
    "P312": 149, "P321": 150, "P3112": 151, "P3121": 152, "P3212": 153,
    "P3221": 154, "R32": 155, "P3m1": 156, "P31m": 157, "P3c1": 158,
    "P31c": 159, "R3m": 160, "R3c": 161, "P-31m": 162, "P-31c": 163,
    "P-3m1": 164, "P-3c1": 165, "R-3m": 166, "R-3c": 167,
    "P6": 168, "P61": 169, "P65": 170, "P62": 171, "P64": 172, "P63": 173,
    "P-6": 174, "P6/m": 175, "P63/m": 176, "P622": 177, "P6122": 178,
    "P6522": 179, "P6222": 180, "P6422": 181, "P6322": 182, "P6mm": 183,
    "P6cc": 184, "P63cm": 185, "P63mc": 186, "P-6m2": 187, "P-6c2": 188,
    "P-62m": 189, "P-62c": 190, "P6/mmm": 191, "P6/mcc": 192, "P63/mcm": 193,
    "P63/mmc": 194, "P23": 195, "F23": 196, "I23": 197, "P213": 198,
    "I213": 199, "Pm-3": 200, "Pn-3": 201, "Fm-3": 202, "Fd-3": 203,
    "Im-3": 204, "Pa-3": 205, "Ia-3": 206, "P432": 207, "P4232": 208,
    "F432": 209, "F4132": 210, "I432": 211, "P4332": 212, "P4132": 213,
    "I4132": 214, "P-43m": 215, "F-43m": 216, "I-43m": 217, "P-43n": 218,
    "F-43c": 219, "I-43d": 220, "Pm-3m": 221, "Pn-3n": 222, "Pm-3n": 223,
    "Pn-3m": 224, "Fm-3m": 225, "Fm-3c": 226, "Fd-3m": 227, "Fd-3c": 228,
    "Im-3m": 229, "Ia-3d": 230,
}

#: 等价设置别名（Pmnb 等轴置换写法直接映射到标准编号）
_SYMBOL_ALIASES = {
    "PMNB": "Pnma", "PNMA": "Pnma", "PMCN": "Pnma", "PNAM": "Pnma",
    "P21/NB": "P21/c", "P21/CN": "P21/c", "P21/NA": "P21/c",
}


@dataclass(frozen=True)
class SymmetryInfo:
    """一个物相的对称性描述（报告与界面直接使用）。"""

    space_group: str | None
    number: int | None
    crystal_system: str | None      # 键名，见 SYSTEM_NAMES
    point_group: str | None         # 国际（H-M）记号
    point_group_schoenflies: str | None
    laue_class: str | None
    bravais: str | None             # 如 "oP"
    centering: str | None           # P / A / B / C / I / F / R
    centrosymmetric: bool | None

    # -- 本地化/格式化辅助 -------------------------------------------------
    def system_label(self, lang: str = "zh") -> str:
        if self.crystal_system is None:
            return "—"
        zh, en, _abbr = SYSTEM_NAMES[self.crystal_system]
        if lang.startswith("zh"):
            return zh
        if lang.startswith("ja"):
            return SYSTEM_NAMES_JA[self.crystal_system]
        return en

    def bravais_label(self, lang: str = "zh") -> str:
        if self.crystal_system is None or self.centering is None:
            return "—"
        zh, en, abbr = SYSTEM_NAMES[self.crystal_system]
        if lang.startswith("zh"):
            return f"{zh}{self.centering}（{self.bravais}）"
        if lang.startswith("ja"):
            return f"{SYSTEM_NAMES_JA[self.crystal_system]}{self.centering}（{self.bravais}）"
        return f"{en} {self.centering} ({self.bravais})"


def _normalize_symbol(sym: str | None) -> str | None:
    """把 'P n m a' / 'P 21/c' 之类的写法压成 'Pnma' / 'P21/c'。"""
    if not sym:
        return None
    s = sym.strip().strip("'\"")
    s = "".join(s.split())
    if not s:
        return None
    alias = _SYMBOL_ALIASES.get(s.upper())
    if alias:
        return alias
    # 首字母大写、其余按 ITA 常规（字母小写、数字保留）
    core = s[0].upper() + s[1:]
    return core


def number_from_symbol(sym: str | None) -> int | None:
    """由 H-M 符号查空间群编号（未收录返回 None）。"""
    norm = _normalize_symbol(sym)
    if norm is None:
        return None
    if norm in _SYMBOL_TO_NUMBER:
        return _SYMBOL_TO_NUMBER[norm]
    # 尝试忽略空格/大小写差异
    low = {k.lower(): v for k, v in _SYMBOL_TO_NUMBER.items()}
    return low.get(norm.lower())


def point_group_of(number: int) -> tuple[str, str] | None:
    """空间群编号 -> (晶系, 点群)。"""
    if not (1 <= int(number) <= 230):
        return None
    n = int(number)
    for lo, hi, system, pg in _RANGES:
        if lo <= n <= hi:
            return system, pg
    return None


def laue_of_point_group(point_group: str | None) -> str | None:
    return _POINT_TO_LAUE.get(point_group) if point_group else None


def crystal_system_from_cell(cell, tol_deg: float = 0.5,
                             tol_len: float = 0.02) -> str:
    """由晶胞参数判定晶系（CIF 缺空间群时的兜底，基于度规约束）。

    判据（度规必要条件，非充分条件）：
      三斜：无 90° 约束；单斜：恰一个角 ≠ 90°；
      正交：三角皆 90°、三边不等；四方：三角 90° 且 a=b≠c；
      三方/六方：a=b、α=β=90°、γ=120°；立方：三角 90° 且 a=b=c。
    """
    a, b, c, al, be, ga = [float(x) for x in cell]

    def is90(x: float) -> bool:
        return abs(x - 90.0) <= tol_deg

    def eq(x: float, y: float) -> bool:
        return abs(x - y) <= tol_len * max(abs(x), abs(y), 1e-9)

    all90 = is90(al) and is90(be) and is90(ga)
    if all90:
        if eq(a, b) and eq(b, c):
            return "cubic"
        if eq(a, b) or eq(b, c) or eq(a, c):
            return "tetragonal"
        return "orthorhombic"
    if is90(al) and is90(be) and abs(ga - 120.0) <= tol_deg and eq(a, b):
        return "hexagonal"
    n90 = sum(is90(x) for x in (al, be, ga))
    if n90 == 2:
        return "monoclinic"
    return "triclinic"


def describe(space_group: str | None, number: int | None, cell=None) -> SymmetryInfo:
    """组装对称性描述。优先用编号；无编号时用符号反查；再退化为度规判据。"""
    num = int(number) if number is not None else number_from_symbol(space_group)
    norm = _normalize_symbol(space_group)
    if num is None:
        system = crystal_system_from_cell(cell) if cell is not None else None
        return SymmetryInfo(norm, None, system, None, None, None,
                            None, None, None)
    info = point_group_of(num)
    system, pg = info if info else (None, None)
    laue = laue_of_point_group(pg)
    centering = None
    if norm:
        first = norm[0].upper()
        centering = first if first in "PABCIFR" else None
    bravais = None
    if system and centering:
        zh_abbr = SYSTEM_NAMES[system][2]
        bravais = f"{zh_abbr}{centering}"
    centrosym = None
    if laue is not None and pg is not None:
        centrosym = (pg == laue)
    return SymmetryInfo(norm, num, system, pg,
                        _POINT_SCHOENFLIES.get(pg) if pg else None,
                        laue, bravais, centering, centrosym)


def describe_structure(struct) -> SymmetryInfo:
    """对 CifStructure 求对称性描述（读其空间群字段与晶胞）。"""
    return describe(getattr(struct, "space_group", None),
                    getattr(struct, "space_group_number", None),
                    getattr(struct, "cell", None))
