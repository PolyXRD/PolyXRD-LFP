"""衍射峰枚举（向量化实现）—— Rietveld 精修的性能关键路径。

背景
----
家族 vendor 的 :func:`lfp.core.profile.struct.compute_peaks` 是**逐 hkl 标量
循环**（三只嵌套 for + 每点一次 28 原子的 numpy 小数组运算）。在 RutAna 里
这够用，因为其精修只有 (zero, U, V, W, eta) 5 个非线性参数、晶胞只在末轮
缩放。本工具要为**正交晶系的三条边长 a/b/c 同时精修**，LM/trf 每轮要做
(参数数 + 1) 次残差评估，每个评估都要重算峰表；标量实现下单次评估约 0.2 s，
完整精修会到分钟级，交互式界面不可接受。

因此本模块把同一物理模型改写为**整批向量化**：

- 倒易点阵在矩形盒 h,k,l ∈ [-H, H] 上一并生成（自动含多重性）；
- |F|²、LP、Kα 双线均以 (N_hkl, N_atom) 数组一次算完；
- 结果与标量版本**逐项等价**（tests/test_lattice.py 用标量版对齐）。

数学口径与 vendor 版严格一致（禁止在此另立一套）::

    F(hkl) = Σ_j f_j(s)·occ_j·exp(-B_j s²)·exp(2πi(h x_j + k y_j + l z_j))
    f_j(s) = Z_j - 41.78214·s²·Σ_i a_i exp(-b_i s²)      s = sinθ/λ = g/2
    I(hkl) = |F|²·LP(θ)·w_α          LP = (1+cos²2θ)/(sin²θ·cosθ)
    d(hkl) = 1/g

同一 2θ（容差内）的多条反射合并为一条「衍射峰」，合并后强度求和，
与标量版 :func:`compute_peaks` 的合并规则（TWO_THETA_TOL）相同。
"""

from __future__ import annotations

import math

import numpy as np

from lfp.core.profile.cif import ATOMIC_SCATTERING, ATOMIC_Z, CifStructure
from lfp.core.profile.shape import march_dollase_weight
from lfp.core.profile.struct import TWO_THETA_TOL, reciprocal_basis

#: |F|² 相对阈值（相对 s=0 处最大可能值）。相消干涉的残差约 1e-32 量级，
#: 用 1e-9 滤掉数值噪声「假峰」，与 vendor 版取值一致。
_INTENSITY_REL_TOL = 1e-9


class ReflectionTable:
    """一批反射（已按 2θ 合并）的只读数组视图。

    属性均为等长一维数组，按 2θ 升序：
      two_theta : 峰位 (度)
      intensity : |F|²·LP·w_α（任意单位；标度由线性层给出）
      d         : 晶面间距 (Å)
      hkl       : (N, 3) int 数组，该峰贡献最大的那条反射（标定指数用）
      n_merged  : 该峰合并的反射条数（简并/重叠指示）
    """

    __slots__ = ("two_theta", "intensity", "d", "hkl", "n_merged")

    def __init__(self, two_theta, intensity, d, hkl, n_merged):
        self.two_theta = two_theta
        self.intensity = intensity
        self.d = d
        self.hkl = hkl
        self.n_merged = n_merged

    def __len__(self) -> int:
        return int(self.two_theta.size)

    def strongest(self) -> int:
        """最强峰的索引。"""
        return int(np.argmax(self.intensity))


def _atom_arrays(struct: CifStructure):
    """把原子表拆成向量化计算所需数组；返回 (Z, A, Bc, X, OCC, BW, skipped)。"""
    zs, coeff_a, coeff_b = [], [], []
    xs, ys, zs_, occs, bs = [], [], [], [], []
    skipped: list[str] = []
    for (elem, x, y, z, occ, B) in struct.atoms:
        coeff = ATOMIC_SCATTERING.get(elem)
        if coeff is None or elem not in ATOMIC_Z:
            skipped.append(elem)
            continue
        zs.append(ATOMIC_Z[elem])
        coeff_a.append([c[0] for c in coeff])
        coeff_b.append([c[1] for c in coeff])
        xs.append(x); ys.append(y); zs_.append(z)
        occs.append(occ); bs.append(B)
    if not zs:
        raise ValueError(f"无可用散射因子: {struct.name} (跳过 {skipped})")
    return (np.array(zs, float), np.array(coeff_a, float), np.array(coeff_b, float),
            np.array([xs, ys, zs_], float), np.array(occs, float),
            np.array(bs, float), skipped)


def hkl_box(cell, min_g: float, max_g: float) -> np.ndarray:
    """覆盖 g ∈ [min_g, max_g] 所需的最小 (h,k,l) 整数盒 -> (N,3) int 数组。"""
    a, b, c, al, be, ga = cell
    ast, bst, cst = reciprocal_basis(a, b, c, al, be, ga)
    min_recip = min(np.linalg.norm(ast), np.linalg.norm(bst), np.linalg.norm(cst))
    H = max(int(math.ceil(max_g / min_recip)) + 2, 6)
    rng = np.arange(-H, H + 1)
    H3, K3, L3 = np.meshgrid(rng, rng, rng, indexing="ij")
    hkl = np.stack([H3.ravel(), K3.ravel(), L3.ravel()], axis=1).astype(np.int64)
    # 去掉 (000)
    return hkl[np.any(hkl != 0, axis=1)]


def reciprocal_g(hkl: np.ndarray, cell) -> np.ndarray:
    """|g| 数组 (1/Å)，g = h·a* + k·b* + l·c*。"""
    a, b, c, al, be, ga = cell
    ast, bst, cst = reciprocal_basis(a, b, c, al, be, ga)
    G = (hkl[:, 0:1] * ast[None, :] + hkl[:, 1:2] * bst[None, :]
         + hkl[:, 2:3] * cst[None, :])
    return np.sqrt(np.einsum("ij,ij->i", G, G))


def structure_factors(struct: CifStructure, hkl: np.ndarray, s2: np.ndarray):
    """|F|² 与「未乘 PO 的强度核」|F|² 数组（不含 LP）。

    返回 (i_hkl, f_absmax²)：后者仅用于相对阈值筛峰。
    """
    Z, A, Bc, X, OCC, BW, _sk = _atom_arrays(struct)
    # f_j(s) = Z_j - 41.78214·s²·Σ_i a_i exp(-b_i s²)
    expo = np.exp(-Bc[None, :, :] * s2[:, None, None])          # (N, natom, 4)
    fs = Z[None, :] - 41.78214 * s2[:, None] * np.sum(A[None] * expo, axis=2)
    # 相位 h·x + k·y + l·z
    gdr = (hkl[:, 0:1] * X[0][None, :] + hkl[:, 1:2] * X[1][None, :]
           + hkl[:, 2:3] * X[2][None, :])
    phase = np.exp(2j * math.pi * gdr) * np.exp(-BW[None, :] * s2[:, None])
    F = np.sum(fs * OCC[None, :] * phase, axis=1)
    i_hkl = F.real ** 2 + F.imag ** 2
    f_ref_sq = float(np.sum(Z * OCC)) ** 2
    return i_hkl, max(f_ref_sq * _INTENSITY_REL_TOL, 1e-300)


def reflections(struct: CifStructure, wavelength: float = 1.54056,
                two_min: float = 5.0, two_max: float = 120.0,
                comps: list[tuple[float, float]] | None = None,
                po: tuple[int, int, int, float] | None = None) -> ReflectionTable:
    """计算并合并衍射峰表（向量化）。

    comps : [(波长, 权重)]，None 时按单色光 wavelength 计算。
    po    : (h,k,l,r) March–Dollase 择优取向；None 或 r=1 时不加权。
    返回 :class:`ReflectionTable`（按 2θ 升序、已合并）。
    """
    comps = comps if comps is not None else [(float(wavelength), 1.0)]
    max_g = 2 * math.sin(math.radians(two_max / 2)) / min(w for w, _ in comps)
    min_g = 2 * math.sin(math.radians(two_min / 2)) / max(w for w, _ in comps)
    hkl = hkl_box(struct.cell, min_g, max_g)
    g = reciprocal_g(hkl, struct.cell)
    keep = (g >= min_g - 1e-9) & (g <= max_g + 1e-9)
    hkl, g = hkl[keep], g[keep]

    s2 = (g / 2.0) ** 2
    i_hkl, tol_i = structure_factors(struct, hkl, s2)

    # 择优取向权重
    if po is not None:
        ph, pk, pl, pr = po
        a, b, c, al, be, ga = struct.cell
        ast, bst, cst = reciprocal_basis(a, b, c, al, be, ga)
        pv = int(ph) * ast + int(pk) * bst + int(pl) * cst
        nv = float(np.linalg.norm(pv))
        if nv > 0 and abs(float(pr) - 1.0) > 1e-12:
            ca = (hkl @ (pv / nv)) / np.maximum(g, 1e-12)
            ca = np.clip(ca, -1.0, 1.0)
            w = np.array([march_dollase_weight(float(x), float(pr)) for x in ca])
            i_hkl = i_hkl * w

    pos_all, int_all, d_all, hkl_all = [], [], [], []
    for wl, wgt in comps:
        s_arg = wl * g / 2.0
        ok = s_arg < 1.0
        theta = np.arcsin(s_arg[ok])
        tt = np.degrees(2 * theta)
        m = (tt >= two_min - 1e-9) & (tt <= two_max + 1e-9)
        if not np.any(m):
            continue
        th = theta[m]
        lp = (1.0 + np.cos(2 * th) ** 2) / (np.sin(th) ** 2 * np.cos(th))
        val = i_hkl[ok][m] * lp * wgt
        pos_all.append(tt[m]); int_all.append(val)
        d_all.append(1.0 / g[ok][m]); hkl_all.append(hkl[ok][m])

    if not pos_all:
        return ReflectionTable(np.zeros(0), np.zeros(0), np.zeros(0),
                               np.zeros((0, 3), np.int64), np.zeros(0, np.int64))
    pos = np.concatenate(pos_all)
    inten = np.concatenate(int_all)
    dsp = np.concatenate(d_all)
    hk = np.concatenate(hkl_all)
    good = inten > tol_i
    pos, inten, dsp, hk = pos[good], inten[good], dsp[good], hk[good]
    if pos.size == 0:
        return ReflectionTable(np.zeros(0), np.zeros(0), np.zeros(0),
                               np.zeros((0, 3), np.int64), np.zeros(0, np.int64))
    order = np.argsort(pos, kind="stable")
    pos, inten, dsp, hk = pos[order], inten[order], dsp[order], hk[order]

    # 同 2θ 合并（与 vendor 版一致：按键 round(2θ/TOL) 合并、强度求和）
    key = np.round(pos / TWO_THETA_TOL).astype(np.int64)
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    sums = np.add.reduceat(inten, starts)
    counts = np.diff(np.r_[starts, pos.size])
    # 每组的代表 hkl：组内强度最大者
    rep = np.empty(starts.size, dtype=np.int64)
    for j, s0 in enumerate(starts):
        seg = inten[s0:s0 + counts[j]]
        rep[j] = s0 + int(np.argmax(seg))
    return ReflectionTable(pos[starts], sums, dsp[rep],
                           np.array([_canonical(h) for h in hk[rep]]).reshape(-1, 3),
                           counts.astype(np.int64))


def _canonical(hkl: np.ndarray) -> np.ndarray:
    """把反射指数规范化到「首个非零指数为正」的等价类代表（显示约定）。

    与 d 值无关（Friedel 定律 I(hkl)=I(-h-k-l)），仅用于界面与报告展示，
    避免出现 (-2 0 0) 这类反号写法。
    """
    h, k, l = int(hkl[0]), int(hkl[1]), int(hkl[2])
    if h < 0 or (h == 0 and k < 0) or (h == 0 and k == 0 and l < 0):
        return np.array([-h, -k, -l], dtype=np.int64)
    return np.array([h, k, l], dtype=np.int64)


def d_spacing(cell, hkl) -> float:
    """单条反射的晶面间距 (Å)。"""
    a, b, c, al, be, ga = cell
    ast, bst, cst = reciprocal_basis(a, b, c, al, be, ga)
    v = int(hkl[0]) * ast + int(hkl[1]) * bst + int(hkl[2]) * cst
    return 1.0 / float(np.linalg.norm(v))
