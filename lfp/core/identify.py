"""LiFePO4 物相判定（"这条谱是不是 LFP？"）。

判定逻辑
--------
不做「相似度打分」这类黑箱，而是可解释的三条判据：

1. **覆盖率 coverage**：以 LFP 计算谱的参考峰（按积分强度加权，取数据范围内
   最强的一批）为分母，统计有实测峰在容差内对应的权重占比。
   权重 = 该反射的计算相对强度，因此「最强几条线是否都对上」说话最重。
2. **前三强判据**：数据范围内计算谱的 3 条最强线必须条条有对应实测峰。
   这是定性分析的行业惯例（最强线缺失即不是该相），也是最难被别的物相
   「碰巧凑上」的一条。
3. **未解释强度 unexplained**：实测峰中无法归给 LFP 的强度占比（含「能作为
   LFP 的 Kα2 卫星解释」的峰——这部分先豁免，避免用 Kα1/Kα2 双线自罚）。
4. **模型充分性 model_ok**：反解 (零点, 各向同性胀缩) 之后，配对峰的加权峰位
   残差 RMS 必须 ≤ 0.45×位置容差。前三条判据只数「有没有峰、强度够不够」，
   对「峰位系统性错到哪去」不敏感；若样品发生了明显各向异性形变（正极材料
   在充放电/掺杂下确有此类情况），两参数模型压不住峰位偏差，此时必须拒绝——
   否则会带着一个不属于它的结构进 Rietveld，拟合出物理上无意义的晶胞。

判定：coverage ≥ 0.70 且 前三强全中 且 unexplained ≤ 0.35 且 model_ok → 是 LFP。

容差与两步搜索
--------------
容许两种系统偏差（真实样品必然存在）：
- 零点/样品位移 dz：整体平移，搜索 ±0.20°；
- 晶胞失配 e = Δd/d：随 2θ 增大而增大的偏移（sinθ_obs = sinθ_ref/(1+e)），
  搜索 ±1%（对应 LFP 与 FePO4 之间约 0.6% 的晶胞差）。

搜索分两步，**不能只用网格**：
1. (dz, e) 网格定「哪条参考峰对上哪个实测峰」——覆盖率关于 dz 是阶跃函数，
   在 ±tol 内成片相同，网格最优点在平台上几乎是随机的（占位用，不作数）；
2. 用配对做加权最小二乘反解出连续的 (dz, e)，再按新值重配对，交替迭代至
   收敛。零点精度由此不再受网格步长限制。
命中的 (obs 2θ, hkl) 对随后用于**预拟合晶胞**（正交晶系对 1/a²,1/b²,1/c²
是线性的），再交给 Rietveld 精修。

实现独立于精修引擎：判定只用「参考峰位 + 相对强度」，不给精修留任何
「先把模型拟合上去再说」的余量——这是本工具「先判定、后精修」的纪律。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from lfp.core.dtypes import Pattern
from lfp.core.peaks import ObservedPeak, find_peaks
from lfp.core.processing import snip
from lfp.core.profile.cif import CifStructure
from lfp.core.profile.forward import ProfileParams, reflection_table
from lfp.core.profile.lattice import ReflectionTable

#: 参考峰强度下限（相对最强线）：低于此值的参考峰不参与覆盖率统计
REF_MIN_REL = 0.02
#: 参考峰条数上限（按强度取前 N 条，足够覆盖 5–90° 全部主峰）
REF_MAX_COUNT = 60
#: 位置容差（度）：tol = clip(0.35×实测中位 FWHM, TOL_FLOOR, TOL_CEIL)
#: 宽容差会把宽峰聚合物/无定形包误判成本相，故上限 0.30°——Rietveld
#: 前的定性判定宁可严格（漏判可由用户手动放行），不可宽松（错判会一路
#: 精修出毫无物理意义的晶胞）。
TOL_FLOOR = 0.15
TOL_CEIL = 0.30
#: 零点搜索范围与步长（度）
ZERO_RANGE = (-0.20, 0.20)
ZERO_STEP = 0.02
#: 晶胞失配搜索范围与步长（Δd/d）
STRAIN_RANGE = (-0.010, 0.010)
STRAIN_STEP = 0.001

# ---- 判定阈值（冻结；改动需同步更新文档与测试）-------------------------
COVERAGE_PASS = 0.70
UNEXPLAINED_PASS = 0.35
TOP_N_STRONG = 3

#: 模型充分性闸门：反解 (零点, 各向同性胀缩) 后，配对峰的加权峰位残差
#: RMS 不得超过「位置容差 × 该比例」。
#:
#: 依据（``tools/diag_identify.py`` 实测，残差比 = RMS/tol）：
#:   - 合格样本：合成 plain 0.19、各向同性 +0.4% 0.15、真实 LiFePO4 0.14、
#:     磷酸铁锂#1 0.13；
#:   - 该否掉、但三条基本判据拦不住的样本：a+1%/b−0.3% 覆盖率 0.731、
#:     前三强 3/3、未解释 0.315（三条全过）残差比 0.56；
#:     a+0.6%/b−0.6% 覆盖率 0.755 残差比 0.53。
#: 取 0.45：合格侧留 2 倍余量，又能拦住上面两个只靠覆盖率漏网的形变。
RESID_RMS_RATIO = 0.45
#: 反解迭代：从网格前 K 个候选出发，各迭代至多 N 轮
REFINE_STARTS = 4
REFINE_ROUNDS = 8


@dataclass(frozen=True)
class MatchPair:
    """一条「参考反射 ↔ 实测峰」的对应。"""

    two_theta_obs: float
    two_theta_ref: float
    hkl: tuple[int, int, int]
    rel_intensity: float
    delta: float
    obs: ObservedPeak


@dataclass(frozen=True)
class IdentifyResult:
    """判定结果（含证据链，界面与报告直接展示）。"""

    is_lfp: bool
    coverage: float
    unexplained: float
    zero_shift: float
    strain_scale: float
    top_strong_matched: int
    n_ref_used: int
    n_matched: int
    pairs: list[MatchPair] = field(default_factory=list)
    unmatched: list[ObservedPeak] = field(default_factory=list)
    observed: list[ObservedPeak] = field(default_factory=list)
    ref_table: ReflectionTable | None = None
    tolerance: float = TOL_FLOOR
    cell_scales: tuple[float, float, float] | None = None
    self_consistent: bool = False   # 预拟合晶胞是否合理（1/a² 全正）
    resid_rms: float = 0.0          # 配对峰加权峰位残差 RMS（度）
    model_ok: bool = True           # 两参数模型是否足以解释峰位（闸门）

    @property
    def top_strong_ok(self) -> bool:
        return self.top_strong_matched >= TOP_N_STRONG

    @property
    def resid_ratio(self) -> float:
        """峰位残差 RMS 与位置容差之比（模型充分性的无量纲度量）。"""
        return self.resid_rms / self.tolerance if self.tolerance else float("inf")

    def fail_reasons(self) -> list[str]:
        """未通过的判据（i18n 键序列，按判据顺序）。

        界面与报告必须能回答「为什么不是」：只看 coverage/top3/unexplained
        三个数的人，遇到「被残差闸门否掉」的谱会以为软件出错（三个数都合格）。
        """
        out: list[str] = []
        if self.coverage < COVERAGE_PASS:
            out.append("ident.reason.coverage")
        if not self.top_strong_ok:
            out.append("ident.reason.top3")
        if self.unexplained > UNEXPLAINED_PASS:
            out.append("ident.reason.unexplained")
        if not self.model_ok:
            out.append("ident.reason.model")
        return out

    def reason_kw(self) -> dict:
        """格式化 :meth:`fail_reasons` 文案所需的数值（多余的键被 format 忽略）。"""
        return {"cov": self.coverage * 100.0, "n": self.top_strong_matched,
                "unexp": self.unexplained * 100.0, "rms": self.resid_rms,
                "tol": self.tolerance, "ratio": self.resid_ratio}

    def summary_key(self) -> str:
        """判定结论的 i18n 键（界面/报告共用，保证口径一致）。"""
        if self.is_lfp:
            return "ident.verdict.pass"
        if self.coverage >= 0.4 or self.top_strong_ok:
            return "ident.verdict.partial"
        return "ident.verdict.fail"


def reference_peaks(struct: CifStructure, two_min: float, two_max: float,
                    prm: ProfileParams,
                    min_rel: float = REF_MIN_REL,
                    max_count: int = REF_MAX_COUNT) -> ReflectionTable:
    """LFP 参考峰（单色 Kα1 峰位 + 计算相对强度，按强度取前 N 条）。"""
    single = prm.with_changes(anode=None)
    table = reflection_table(struct, single, two_min, two_max)
    if len(table) == 0:
        return table
    imax = float(np.max(table.intensity))
    keep = table.intensity >= min_rel * imax
    idx = np.flatnonzero(keep)
    if idx.size > max_count:
        idx = idx[np.argsort(table.intensity[idx])[::-1][:max_count]]
        idx = np.sort(idx)
    return ReflectionTable(table.two_theta[idx], table.intensity[idx],
                           table.d[idx], table.hkl[idx], table.n_merged[idx])


def _predict(ref_tt: np.ndarray, strain: float, dz: float) -> np.ndarray:
    """由晶胞失配与零点预测参考峰位置。"""
    th = np.arcsin(np.clip(np.sin(np.radians(ref_tt / 2.0)) / (1.0 + strain),
                           -1.0, 1.0))
    return np.degrees(2.0 * th) + dz


def _ka2_position(two_theta: float, lam1: float = 1.54056,
                  lam2: float = 1.54439) -> float:
    """Kα2 卫星位置（用于豁免「实测峰其实是 Kα2」的情形）。"""
    th = math.radians(two_theta / 2.0)
    s = min(math.sin(th) * lam2 / lam1, 1.0)
    return math.degrees(2.0 * math.asin(s))


def _match_once(ref_tt, ref_int, obs_tt, tol: float):
    """容差内一对一匹配：按 |Δ2θ| 从小到大全局贪心分配。

    不用「逐参考峰取最近邻」那种顺序贪心：先到的弱峰会把后面的强峰本该
    占用的实测峰抢走（LFP 在 30–40° 一带参考峰间距可小于容差）。改成把
    全部候选对应按偏差排序后依次占位，强峰不再被弱峰挤掉——用不上的
    参考峰自然落空，不会污染配对。
    """
    if obs_tt.size == 0 or ref_tt.size == 0:
        return []
    d = np.abs(obs_tt[None, :] - np.asarray(ref_tt)[:, None])
    ii, jj = np.nonzero(d <= tol)
    if ii.size == 0:
        return []
    order = np.argsort(d[ii, jj], kind="stable")
    used_r: set[int] = set()
    used_o: set[int] = set()
    pairs: list[tuple[int, int]] = []
    for k in order:
        i, j = int(ii[k]), int(jj[k])
        if i in used_r or j in used_o:
            continue
        used_r.add(i)
        used_o.add(j)
        pairs.append((i, j))
    return pairs


def identify_lfp(pattern: Pattern, struct: CifStructure, prm: ProfileParams,
                 two_min: float | None = None, two_max: float | None = None,
                 observed: list[ObservedPeak] | None = None) -> IdentifyResult:
    """判定一条实测谱是否为 LiFePO4。

    pattern : 实测谱（**不要**先扣背景——内部自行估计背景，避免用户处理链
              影响判定结果的可比性）
    struct  : LFP 结构模型（内置 CIF）
    prm     : 峰形参数（只用其波长/双线设置决定参考峰位）
    """
    tt = np.asarray(pattern.two_theta, dtype=np.float64)
    y = np.asarray(pattern.intensity, dtype=np.float64)
    lo = float(two_min) if two_min is not None else float(tt[0])
    hi = float(two_max) if two_max is not None else float(tt[-1])
    lo = max(lo, float(tt[0]))
    hi = min(hi, float(tt[-1]))

    if observed is None:
        # 判定用的背景估计：SNIP 迭代次数取 ~FWHM 点数（10 点起步），
        # 与精修背景无关，只用于把峰从连续背景里提出来。
        step = float(np.median(np.diff(tt))) if tt.size > 2 else 0.02
        bg = snip(y, max(8, int(round(0.15 / max(step, 1e-6)))))
        observed = [p for p in find_peaks(pattern, background=bg)
                    if lo - 1e-9 <= p.two_theta <= hi + 1e-9]
    ref = reference_peaks(struct, lo, hi, prm)
    if len(ref) == 0 or not observed:
        return IdentifyResult(False, 0.0, 1.0, 0.0, 0.0, 0, len(ref), 0,
                              ref_table=ref, observed=list(observed))

    obs_tt = np.array([p.two_theta for p in observed])
    obs_h = np.array([p.height for p in observed])
    fwhms = np.array([p.fwhm for p in observed])
    tol = float(np.clip(0.35 * float(np.median(fwhms)), TOL_FLOOR, TOL_CEIL))
    ref_int = np.asarray(ref.intensity, dtype=np.float64)
    w = ref_int / float(np.max(ref_int))
    w_sum = float(np.sum(w)) or 1.0
    # 数据范围内计算谱最强的 N 条（用于「前三强必须命中」判据）
    strong_idx = set(np.argsort(ref_int)[::-1][:TOP_N_STRONG].tolist())

    total_h = float(np.sum(obs_h)) or 1.0

    def _evaluate(st: float, dz0: float, use_tol: float):
        """给定 (晶胞胀缩, 零点) 评估：覆盖率、前三强命中、未解释强度、配对表、峰位残差。

        未解释强度里对「能作为某个已命中峰的 Kα2 卫星」的峰做豁免——否则
        双线数据（未剥 Kα2）会被系统性判成含第二相。

        返回值末位 ``rms`` 是配对峰的**加权峰位残差均方根**（权重取
        ``√相对强度``）：它衡量「零点 + 各向同性胀缩」这个两参数模型能否
        解释实测峰位。覆盖率是阶跃量（容差内的错位不算错，±tol 的平移
        都拿满分），无法区分「模型对」与「模型勉强塞得下」；残差是连续量，
        正好补上这一课。
        """
        pred = _predict(np.asarray(ref.two_theta), st, dz0)
        prs = _match_once(pred, ref_int, obs_tt, use_tol)
        cov = float(np.sum([w[i] for i, _ in prs])) / w_sum
        hit = len({i for i, _ in prs} & strong_idx)
        used = {j for _, j in prs}
        sat = [_ka2_position(observed[j].two_theta) for j in used]
        unmatched: list[ObservedPeak] = []
        unexp = 0.0
        for j, p in enumerate(observed):
            if j in used:
                continue
            if any(abs(p.two_theta - s) <= use_tol for s in sat):
                continue      # 是 Kα2 卫星
            unmatched.append(p)
            unexp += float(p.height) / total_h
        out = [
            MatchPair(two_theta_obs=float(observed[j].two_theta),
                      two_theta_ref=float(ref.two_theta[i]),
                      hkl=tuple(int(x) for x in ref.hkl[i]),
                      rel_intensity=float(w[i]),
                      delta=float(observed[j].two_theta - ref.two_theta[i]),
                      obs=observed[j])
            for i, j in sorted(prs, key=lambda ij: ref.two_theta[ij[0]])
        ]
        if prs:
            r = np.array([observed[j].two_theta - pred[i] for i, j in prs])
            ww = np.array([w[i] for i, _ in prs])
            rms = float(np.sqrt(np.sum(ww * r * r) / np.sum(ww)))
        else:
            rms = float("inf")
        return cov, hit, unexp, out, unmatched, rms

    # ---- 第一步：网格搜索只用来定「哪条参考峰对上哪个实测峰」 -------
    # 覆盖率在这里是阶跃量：只要参考峰落在实测峰 ±tol 内就算命中，因此
    # (dz, δ) 平面上存在大片覆盖率相同的平台，取最大值等于在平台上随便
    # 落一点（实测：真值 +0.02° 会被报成 −0.12°，真值 0.15° 报成 0.04°）。
    # 所以网格结果不当最终解，只当配对初值。
    cands: list[tuple[tuple, float, float]] = []
    for strain in np.arange(STRAIN_RANGE[0], STRAIN_RANGE[1] + 1e-12, STRAIN_STEP):
        pred0 = _predict(np.asarray(ref.two_theta), strain, 0.0)
        for dz in np.arange(ZERO_RANGE[0], ZERO_RANGE[1] + 1e-12, ZERO_STEP):
            prs = _match_once(pred0 + dz, ref_int, obs_tt, tol)
            cov = float(np.sum([w[i] for i, _ in prs])) / w_sum
            top_hit = len({i for i, _ in prs} & strong_idx)
            # 选择准则必须与服务判据一致：**前三强全中是硬性要求**，覆盖率只是
            # 软指标。若只按覆盖率取胜，会选到「弱峰全命中、丢掉一条强线」的
            # 折中解（覆盖率更高但 top_hit=2），于是明明能判过的谱被否掉。
            # 因此把「top_hit 是否达标」提到第一关键字。
            key = (top_hit >= TOP_N_STRONG, round(cov, 4), top_hit)
            cands.append((key, strain, float(dz)))
    if not cands:
        return IdentifyResult(False, 0.0, 1.0, 0.0, 0.0, 0, len(ref), 0,
                              ref_table=ref, observed=list(observed))
    cands.sort(key=lambda c: c[0], reverse=True)

    # ---- 第二步：从若干最优网格点出发，交替「配对 → 反解 (dz, δ)」至收敛 --
    # 只从单点出发容易陷在错配对应的局部解里，故取前几个候选各跑一遍。
    best = None
    for _key, st0, dz0 in cands[:REFINE_STARTS]:
        st, dz = _refine_offset(np.asarray(ref.two_theta), ref_int, observed,
                                obs_tt, st0, dz0, tol)
        cov, hit, unexp, prs_out, unmatched, rms = _evaluate(st, dz, tol)
        model_ok = rms <= RESID_RMS_RATIO * tol
        # 排序口径与服务判据一致：前三强 -> 模型充分性 -> 覆盖率（粗分档，
        # 避免末位噪声抢戏）-> 残差小者优先。
        key = (hit >= TOP_N_STRONG, model_ok, round(cov, 2), -rms, cov)
        if best is None or key > best[0]:
            best = (key, st, dz, cov, hit, unexp, prs_out, unmatched, rms, model_ok)
    (_key, strain, dz, coverage, top_hit, unexplained,
     pairs_out, unmatched, resid_rms, model_ok) = best

    cell_scales, ok_cell = _prefit_cell(struct, pairs_out)
    is_lfp = (coverage >= COVERAGE_PASS and top_hit >= TOP_N_STRONG
              and unexplained <= UNEXPLAINED_PASS and model_ok)
    return IdentifyResult(is_lfp=is_lfp, coverage=coverage,
                          unexplained=unexplained, zero_shift=float(dz),
                          strain_scale=float(strain), top_strong_matched=int(top_hit),
                          n_ref_used=len(ref), n_matched=len(pairs_out),
                          pairs=pairs_out, unmatched=unmatched,
                          observed=list(observed), ref_table=ref, tolerance=tol,
                          cell_scales=cell_scales, self_consistent=ok_cell,
                          resid_rms=float(resid_rms), model_ok=bool(model_ok))


def _refine_offset(ref_tt, ref_int, observed, obs_tt, strain: float, dz: float,
                   tol: float, rounds: int = REFINE_ROUNDS):
    """交替「按当前 (dz, δ) 配对 → 用配对反解 (dz, δ)」，直到收敛。

    这是判定精度的关键一步：网格的 0.02°/0.001 步长本身就不足以定零点
    （实测 ±0.06° 的要求对应不到三格），必须让最小二乘在连续域上接管。
    """
    for _ in range(rounds):
        pred = _predict(np.asarray(ref_tt), strain, dz)
        prs = _match_once(pred, ref_int, obs_tt, tol)
        pairs = [
            MatchPair(two_theta_obs=float(observed[j].two_theta),
                      two_theta_ref=float(ref_tt[i]),
                      hkl=(0, 0, 0),
                      rel_intensity=float(ref_int[i]),
                      delta=float(observed[j].two_theta - ref_tt[i]),
                      obs=observed[j])
            for i, j in prs
        ]
        dz_new, st_new = _fit_offset(pairs)
        if dz_new is None:
            break
        moved = abs(dz_new - dz) > 1e-4 or abs(st_new - strain) > 1e-6
        dz, strain = dz_new, st_new
        if not moved:
            break
    return strain, dz


def _fit_offset(pairs: list[MatchPair]):
    """由匹配峰反解 (零点 dz, 晶胞胀缩 δ)：Δ2θ = dz − (360/π)·δ·tanθ。

    系数推导：晶胞整体胀缩 δ 使 sinθ 变为 sinθ/(1+δ)，即
    Δ2θ ≈ −2δ·tanθ（弧度）＝ −(360/π)·δ·tanθ（度）。
    δ 的口径与 :func:`_predict` 的 ``strain`` 一致（无量纲相对胀缩），
    两处不能各写一套，否则报出来的数字与搜索空间对不上。

    估计方式：**加权最小二乘 + MAD 剔除**。
    - 权重取 √相对强度：强峰峰位定得准（计数高、峰形拟合稳），弱峰容易被
      邻近强峰的拖尾/双线带偏，不该与强峰同权。
    - 剔除：错配一档的配对残差会明显偏离（相邻参考峰间距可小于容差），
      按 |r| > max(2.5·1.4826·MAD, 0.02°) 迭代剔除两轮。不剔除时这些
      离群对会把零点拉偏约 0.07°（实测：真值 0.15° 反解成 0.22°）。

    返回 (dz, δ)；点数不足或解不合理时返回 (None, 0.0)。
    """
    if len(pairs) < 3:
        return None, 0.0
    t = np.array([math.tan(math.radians(p.two_theta_ref / 2.0)) for p in pairs])
    d = np.array([p.delta for p in pairs])
    rel = np.array([p.rel_intensity for p in pairs])
    rel_max = float(np.max(rel)) if rel.size else 0.0
    wt = np.sqrt(rel / rel_max) if rel_max > 0 else np.ones_like(rel)
    wt = np.maximum(wt, 0.05)
    A = np.stack([np.ones_like(t), -(360.0 / math.pi) * t], axis=1)

    keep = np.ones(t.size, dtype=bool)
    sol = None
    for _ in range(3):
        Ak, dk, wk = A[keep], d[keep], wt[keep]
        try:
            sol, *_ = np.linalg.lstsq(Ak * wk[:, None], dk * wk, rcond=None)
        except Exception:
            return None, 0.0
        r = d - A @ sol
        rr = r[keep]
        mad = float(np.median(np.abs(rr - np.median(rr))))
        cut = max(2.5 * 1.4826 * mad, 0.02)
        new_keep = np.abs(r) <= cut
        if int(new_keep.sum()) < 3 or np.array_equal(new_keep, keep):
            break
        keep = new_keep
    if sol is None:
        return None, 0.0
    dz, e = float(sol[0]), float(sol[1])
    if not (abs(dz) <= 0.5 and abs(e) <= 0.02):
        return None, 0.0
    return dz, e


def _prefit_cell(struct: CifStructure, pairs: list[MatchPair]):
    """由命中峰的 (2θ_obs, hkl) 预拟合正交晶胞 -> 三轴比例。

    sin²θ = (λ/2)²·(h²/a² + k²/b² + l²/c²)，对 (1/a², 1/b², 1/c²) 线性，
    加权最小二乘（权重取相对强度的平方根，强峰定晶胞更可靠）。
    仅当解出三个正的、且偏离原晶胞 < 5% 的值时才采纳。
    """
    if len(pairs) < 4:
        return None, False
    lam = 1.54056
    A, b, wts = [], [], []
    for p in pairs:
        h, k, l = p.hkl
        A.append([h * h, k * k, l * l])
        b.append(4.0 * math.sin(math.radians(p.two_theta_obs / 2.0)) ** 2
                 / (lam * lam))
        wts.append(max(math.sqrt(p.rel_intensity), 0.05))
    A = np.asarray(A, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    wts = np.asarray(wts, dtype=np.float64)
    try:
        sol, *_ = np.linalg.lstsq(A * wts[:, None], b * wts, rcond=None)
    except Exception:
        return None, False
    if not np.all(np.isfinite(sol)) or np.any(sol <= 0):
        return None, False
    a, bb, c = (1.0 / math.sqrt(float(s)) for s in sol)
    a0, b0, c0 = struct.cell[:3]
    scales = (a / a0, bb / b0, c / c0)
    if any(not (0.95 <= s <= 1.05) for s in scales):
        return None, False
    return scales, True
