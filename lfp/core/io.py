"""谱图文件读取（文本两列为主，兼顾常见仪器导出格式）。

设计原则
--------
1. **不改写数据**：只做「定位数值列 → 组装 Pattern」，不做重采样/裁切；
   文件里的 2θ 顺序若为降序，按升序翻转（Pattern 契约要求升序）。
2. **宽容但不猜测**：跳过表头/注释/仪器信息行；一旦进入数值区，遇到
   非数值行即认为数据区结束（仪器尾部常带统计信息）。若文件里出现多段
   数值（多扫描拼接），取最长连续段——不静默拼接，避免把两条谱叠成一条。
3. **元数据提取**：从文件头里读出靶材/波长/步长/扫描范围（Rigaku、
   Shimadzu、Bruker 的 ascii 导出均有明文），用于自动设定 Kα 双线与
   精修范围；读不到就用 Cu Kα1 默认值，并在元数据里标记来源。

支持扩展名：.txt .xy .xye .dat .csv .asc .prn .xrdml(文本) .raw(ASCII)
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from lfp.core.dtypes import Pattern
from lfp.core.processing import KA1, KA2

#: 支持的文件扩展名
SUPPORTED_EXTS = (".txt", ".xy", ".xye", ".dat", ".csv", ".asc", ".prn",
                  ".raw", ".xrdml", ".brml", ".uxd", ".ras", ".gsas")

#: 常见靶材的 Kα1 波长（Å），与 processing.KA1 保持一致
_ANODE_ALIASES = {
    "CU": "Cu", "CO": "Co", "CR": "Cr", "FE": "Fe", "MO": "Mo", "AG": "Ag",
}

_TARGET_PATTERNS = (
    re.compile(r"target\s*[=:]\s*([A-Za-z]{1,2})", re.I),
    re.compile(r"anode\s*[=:]\s*([A-Za-z]{1,2})", re.I),
    re.compile(r"\b(Cu|Co|Cr|Fe|Mo|Ag)\s*K\s*[\u03b1a]", re.I),
    re.compile(r"\b(Cu|Co|Cr|Fe|Mo|Ag)\s*ka1", re.I),
)
_WAVELENGTH_PATTERNS = (
    re.compile(r"wavelength\s*[=:]\s*([0-9.]+)", re.I),
    re.compile(r"lambda\s*[=:]\s*([0-9.]+)", re.I),
    re.compile(r"k\s*alpha\s*1?\s*[=:]\s*([0-9.]+)", re.I),
)
_STEP_PATTERNS = (
    re.compile(r"sampling\s*pitch\s*[=:]\s*([0-9.]+)", re.I),
    re.compile(r"step\s*size\s*[=:]\s*([0-9.]+)", re.I),
    re.compile(r"step\s*[=:]\s*([0-9.]+)", re.I),
    re.compile(r"2theta\s*step\s*[=:]\s*([0-9.]+)", re.I),
)


class PatternFormatError(ValueError):
    """文件内容无法解析为两列谱图。"""


def _read_text(path: Path) -> str:
    """按 utf-8-sig → gbk → latin-1 顺序解码（仪器导出常见 GBK 表头）。"""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def _split_numbers(line: str) -> list[float] | None:
    """把一行拆成浮点数列表；含非数值 token 时返回 None。

    兼容空格/制表/逗号/分号分隔；行尾注释（# 或 //）先切掉。
    """
    s = line.strip()
    if not s:
        return None
    for marker in ("#", "//", ";"):
        if marker == ";":
            continue          # 分号在部分导出里是分隔符，先不当注释
        idx = s.find(marker)
        if idx >= 0:
            s = s[:idx].strip()
    if not s:
        return None
    s = s.replace(",", " ").replace("\t", " ").replace(";", " ")
    out: list[float] = []
    for tok in s.split():
        t = tok.strip()
        if not t:
            continue
        try:
            out.append(float(t))
        except ValueError:
            return None
    return out or None


def _extract_number(patterns, text: str) -> float | None:
    for pat in patterns:
        m = pat.search(text)
        if m:
            try:
                return float(m.group(1))
            except (TypeError, ValueError):
                continue
    return None


def _detect_anode(head: str) -> str | None:
    for pat in _TARGET_PATTERNS:
        m = pat.search(head)
        if m:
            key = m.group(1).upper()
            if key in _ANODE_ALIASES:
                return _ANODE_ALIASES[key]
    return None


def read_pattern(path: str | Path, *, wavelength: float | None = None,
                 anode: str | None = None) -> Pattern:
    """读取一条谱图。

    path       : 文件路径
    wavelength : 显式指定波长（Å）；None 时先查文件头，再退 Cu Kα1
    anode      : 显式指定靶材；None 时从文件头识别
    """
    p = Path(path)
    if not p.exists():
        raise PatternFormatError(f"文件不存在: {p}")
    text = _read_text(p)
    lines = text.splitlines()

    # ---- 元数据（只看前 200 行，避免大文件全文扫描）----
    head = "\n".join(lines[:200])
    meta: dict = {"path": str(p), "name": p.name}
    anode_found = anode or _detect_anode(head)
    if anode_found:
        meta["anode"] = anode_found
    wl = wavelength
    if wl is None:
        wl = _extract_number(_WAVELENGTH_PATTERNS, head)
        if wl is None and anode_found in KA1:
            wl = KA1[anode_found]
        meta["wavelength_source"] = "file" if wl is not None else "default"
    if wl is None:
        wl = KA1["Cu"]
        meta["wavelength_source"] = "default"
    meta["wavelength"] = float(wl)
    if anode_found in KA2:
        meta["ka2"] = KA2[anode_found]
    step_hint = _extract_number(_STEP_PATTERNS, head)
    if step_hint:
        meta["step_hint"] = step_hint

    # ---- 数值区：取最长连续段 ----
    segments: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    for line in lines:
        nums = _split_numbers(line)
        if nums is None or len(nums) < 2:
            if current:
                segments.append(current)
                current = []
            continue
        current.append((nums[0], nums[1]))
    if current:
        segments.append(current)
    if not segments:
        raise PatternFormatError(
            f"未找到两列数值数据：{p.name}（请确认是 2θ-强度 文本格式）")
    seg = max(segments, key=len)
    if len(seg) < 10:
        raise PatternFormatError(
            f"可用数据点过少（{len(seg)} 点）：{p.name}")

    tt = np.array([s[0] for s in seg], dtype=np.float64)
    yy = np.array([s[1] for s in seg], dtype=np.float64)
    if tt.size > 1 and tt[0] > tt[-1]:
        tt = tt[::-1]
        yy = yy[::-1]
    # 去重复角度（部分导出在断点处重复一行）
    keep = np.r_[True, np.diff(tt) > 0]
    tt, yy = tt[keep], yy[keep]

    meta["points"] = int(tt.size)
    meta["range"] = (float(tt[0]), float(tt[-1]))
    meta["format"] = "text"
    return Pattern(tt, yy, meta)
