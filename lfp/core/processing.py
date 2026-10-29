"""谱图预处理：平滑、扣背景、去 Kα2。

三者都是**无损于原始数据**的派生操作：GUI 维护「原始谱 + 处理链」，
任何一步都可撤销/重算，导出与精修使用的始终是链尾的当前谱。

算法来源与口径
--------------
平滑
    Savitzky–Golay（局部多项式最小二乘卷积，Savitzky & Golay, Anal. Chem.
    36 (1964) 1627），保留峰形与峰位（不引入移动平均的削峰/偏移）；
    窗口点数不足或点数过少时自动降级为移动平均并给出提示。

扣背景
    - **SNIP**（Statistics-sensitive Non-linear Iterative Peak-clipping，
      Ryan et al., Nucl. Instr. Meth. B34 (1988) 396）：在 log-log 空间做
      迭代削峰，适合连续衰减的粉末背景，不需要人工选区。迭代次数 m 与
      峰宽相关，经验取 m ≈ FWHM(点数)。
    - **多项式**：对全谱做低阶多项式最小二乘，配合 σ 截断迭代
      （只让「远离峰」的点参与拟合），适合平缓背景。
    - **端点线性**：左右端点（或用户给定区间均值）连线，最保守，用于
      只需净峰高的场合。

去 Kα2
    Rachinger 剥离（Rachinger, J. Sci. Instrum. 25 (1948) 254）：把 Kα2
    分量按 Iα2/Iα1 比例与已知 2θ 位移从 Kα1 谱中逐点扣除。
    实现为「正向合成的最小二乘反解」：给定 Kα1 谱 y1 与比例 r，
    y_obs(2θ) = y1(2θ) + r·y1(2θ + Δ(2θ))，用迭代反解（Gangulee 修正），
    对噪声的放大比直接相减小。
"""

from __future__ import annotations

import numpy as np

from lfp.core.dtypes import Pattern

# --------------------------------------------------------------------------- #
# 平滑
# --------------------------------------------------------------------------- #
def savgol(y: np.ndarray, window: int = 11, order: int = 3) -> np.ndarray:
    """Savitzky–Golay 平滑（window 强制为奇数且 > order）。"""
    y = np.asarray(y, dtype=np.float64)
    w = int(window)
    if w % 2 == 0:
        w += 1
    w = max(w, int(order) + 2 + (int(order) % 2 == 0))
    if w % 2 == 0:
        w += 1
    if y.size < w:
        return y.copy()
    try:
        from scipy.signal import savgol_filter
        return savgol_filter(y, w, int(order), mode="interp")
    except Exception:
        # scipy 缺失时的移动平均降级（窗宽一致，端点收缩）
        k = np.ones(w) / w
        pad = w // 2
        ypad = np.pad(y, pad, mode="edge")
        return np.convolve(ypad, k, mode="valid")


def moving_average(y: np.ndarray, window: int = 5) -> np.ndarray:
    y = np.asarray(y, dtype=np.float64)
    w = max(int(window), 1)
    if w <= 1 or y.size < w:
        return y.copy()
    k = np.ones(w) / w
    ypad = np.pad(y, w // 2, mode="edge")
    return np.convolve(ypad, k, mode="valid")[: y.size]


# --------------------------------------------------------------------------- #
# 扣背景
# --------------------------------------------------------------------------- #
def snip(y: np.ndarray, iterations: int = 40, log_space: bool = True) -> np.ndarray:
    """SNIP 背景估计（返回与 y 等长的背景曲线）。

    iterations : 迭代次数 m。经验 m ≈ 峰 FWHM 对应的点数（至少 8）。
    log_space  : True 时先取对数（LLS 变换）再削峰，抑制强峰对背景的抬升；
                 数据含非正值时自动退回线性空间。
    """
    y = np.asarray(y, dtype=np.float64)
    n = y.size
    if n < 5:
        return y.copy()
    m = max(int(iterations), 1)
    m = min(m, (n - 1) // 2)
    if log_space and np.all(y > 0):
        v = np.log(np.log(np.sqrt(np.maximum(y, 1e-9)) + 1.0) + 1.0)
    else:
        v = y.copy()
    # 端点扩展，避免边界截断
    v = np.concatenate([v[m:0:-1], v, v[-2:-m - 2:-1]])
    for p in range(1, m + 1):
        avg = 0.5 * (np.roll(v, p) + np.roll(v, -p))
        v = np.minimum(v, avg)
    v = v[m:m + n]
    if log_space and np.all(y > 0):
        # 反变换
        b = np.expm1(np.expm1(v))
        b = np.maximum(b, 1e-9) ** 2
    else:
        b = v
    # 背景不应高于原谱（数值上可能因变换略有越界）
    return np.minimum(b, y)


def poly_background(x: np.ndarray, y: np.ndarray, order: int = 4,
                    n_iter: int = 8, k_sigma: float = 2.0) -> np.ndarray:
    """迭代多项式背景：σ 截断，只让「不在峰上」的点参与拟合。

    峰区数据点通常远高于拟合曲线，按 y > fit + k_sigma·σ 剔除。
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    order = max(1, min(int(order), 12))
    if y.size < order + 2:
        return np.full_like(y, float(np.min(y)) if y.size else 0.0)
    mask = np.ones(y.size, dtype=bool)
    coef = np.polyfit(x, y, order)
    for _ in range(max(int(n_iter), 1)):
        fit = np.polyval(coef, x)
        resid = y - fit
        sigma = 1.4826 * np.median(np.abs(resid[mask] - np.median(resid[mask]))) \
            if np.any(mask) else float(np.std(resid))
        sigma = max(sigma, 1e-6)
        new_mask = resid < k_sigma * sigma
        # 保证保留足够点数（至少 20%）
        if np.count_nonzero(new_mask) < max(10, int(0.2 * y.size)):
            break
        if np.array_equal(new_mask, mask):
            break
        mask = new_mask
        try:
            coef = np.polyfit(x[mask], y[mask], order)
        except Exception:
            break
    return np.minimum(np.polyval(coef, x), y)


def linear_edges(x: np.ndarray, y: np.ndarray, edge_frac: float = 0.05) -> np.ndarray:
    """端点线性背景：左右各取 edge_frac 比例数据求均值，两点连线。"""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    n = y.size
    if n < 4:
        return np.zeros_like(y)
    k = max(1, int(n * float(edge_frac)))
    yl = float(np.mean(y[:k]))
    yr = float(np.mean(y[-k:]))
    return np.minimum(np.interp(x, [x[0], x[-1]], [yl, yr]), y)


#: 背景方法键 → (中文名, 英文名, 是否需要参数)
BG_METHODS = {
    "snip": ("SNIP 迭代削峰", "SNIP clipping", ("iterations",)),
    "poly": ("多项式拟合", "Polynomial", ("order",)),
    "linear": ("端点线性", "Linear (end points)", ("edge_frac",)),
}


def estimate_background(pattern: Pattern, method: str = "snip",
                        *, iterations: int = 40, order: int = 4,
                        edge_frac: float = 0.05) -> np.ndarray:
    """按方法名估计背景曲线。"""
    x = np.asarray(pattern.two_theta, dtype=np.float64)
    y = np.asarray(pattern.intensity, dtype=np.float64)
    if method == "snip":
        return snip(y, iterations)
    if method == "poly":
        return poly_background(x, y, order)
    if method == "linear":
        return linear_edges(x, y, edge_frac)
    raise ValueError(f"未知背景方法: {method}")


def crop(pattern: Pattern, lo: float, hi: float,
         min_points: int = 64) -> Pattern:
    """裁出 [lo, hi] 区间的谱段（精修范围设定用；不修改原对象）。

    只做区间截取，不重采样：保留原始步长与强度，避免插值引入伪影。
    区间内点数不足 ``min_points`` 时判为无效范围并**原样返回**——宁可精修全谱，
    也不要因用户手误把精修范围设成一小段而得到看似漂亮实则无意义的 Rwp。
    """
    x = np.asarray(pattern.two_theta, dtype=np.float64)
    y = np.asarray(pattern.intensity, dtype=np.float64)
    mask = (x >= float(lo)) & (x <= float(hi))
    if int(mask.sum()) < int(min_points):
        return pattern
    meta = dict(getattr(pattern, "meta", {}) or {})
    meta["crop"] = (float(lo), float(hi))
    return Pattern(x[mask], y[mask], meta)


def subtract(pattern: Pattern, background: np.ndarray,
             clip_negative: bool = True) -> Pattern:
    """返回扣背景后的新谱（不修改原对象）。"""
    y = np.asarray(pattern.intensity, dtype=np.float64) - np.asarray(
        background, dtype=np.float64)
    if clip_negative:
        y = np.maximum(y, 0.0)
    meta = dict(getattr(pattern, "meta", {}) or {})
    meta["bg_subtracted"] = True
    return Pattern(pattern.two_theta, y, meta)


# --------------------------------------------------------------------------- #
# 去 Kα2
# --------------------------------------------------------------------------- #
KA1 = {"Cu": 1.54056, "Co": 1.78897, "Cr": 2.28970, "Fe": 1.93604,
       "Mo": 0.70930, "Ag": 0.55941}
KA2 = {"Cu": 1.54439, "Co": 1.79285, "Cr": 2.29361, "Fe": 1.93998,
       "Mo": 0.71359, "Ag": 0.56381}


def ka2_shift(two_theta, wavelength1: float, wavelength2: float) -> np.ndarray:
    """Kα2 分量相对 Kα1 的 2θ 位移（度）。

    Bragg 关系 sinθ = λ/(2d) => θ2 = asin(sinθ1·λ2/λ1)，Δ2θ = 2(θ2−θ1) > 0。
    """
    tt = np.asarray(two_theta, dtype=np.float64)
    th1 = np.radians(tt / 2.0)
    s = np.sin(th1) * (wavelength2 / wavelength1)
    s = np.clip(s, -1.0, 1.0)
    th2 = np.arcsin(s)
    return np.degrees(2.0 * (th2 - th1))


def strip_kalpha2(pattern: Pattern, anode: str = "Cu", ratio: float = 0.5,
                  iterations: int = 2) -> Pattern:
    """Rachinger 剥离 Kα2，返回只含 Kα1 的新谱。

    角度关系决定了递推方向
    ----------------------
    同一反射的 Kα2 峰出现在**更高**的 2θ（Δ > 0）。因此某个角度 θ 上测到的
    强度，包含「θ 处的 Kα1」与「Kα1 位置在 θ−Δ 的那条反射的 Kα2」：

        y_obs(θ) = y1(θ) + r·y1(θ − Δ)

    于是求解式只能是

        y1(θ) = y_obs(θ) − r·y1(θ − Δ)          （低角 → 高角逐点递推）

    递推方向若写成高角 → 低角，会在 Kα2 峰位处重复扣除自身，导致 Kα1 峰被
    越扣越矮（多轮迭代后甚至会变负）——这是本模块曾经的实现缺陷，已由
    ``tests/test_processing.py::test_strip_kalpha2_recovers_single_peak`` 锁死。

    低角端前 Δ 宽的一小段没有更低的 Kα1 可参考，按「无 Kα2 贡献」原样保留，
    这与 Rachinger 原始处理一致（该区间没有 Kα2 可用信息）。
    """
    if anode not in KA1:
        raise ValueError(f"未知阳极靶: {anode}")
    x = np.asarray(pattern.two_theta, dtype=np.float64)
    y_obs = np.asarray(pattern.intensity, dtype=np.float64).copy()
    w1, w2 = KA1[anode], KA2[anode]
    r = float(ratio)
    if r <= 0:
        return Pattern(x, y_obs, dict(getattr(pattern, "meta", {}) or {}))
    delta = ka2_shift(x, w1, w2)
    n = y_obs.size
    y1 = y_obs.copy()
    for _ in range(max(1, int(iterations))):
        # 原地更新：y1[i] 依赖的 y1[i−Δ] 已在上一轮循环中解出（Gauss–Seidel），
        # 单趟即得精确解；再迭代只是重算同一个不动点，不会过度扣除。
        for i in range(n):
            xq = x[i] - delta[i]
            if xq <= x[0]:
                y1[i] = y_obs[i]
                continue
            j = int(np.searchsorted(x, xq, side="right")) - 1
            j = min(max(j, 0), n - 2)
            t = (xq - x[j]) / max(x[j + 1] - x[j], 1e-12)
            yq = y1[j] * (1.0 - t) + y1[j + 1] * t
            y1[i] = y_obs[i] - r * yq
    meta = dict(getattr(pattern, "meta", {}) or {})
    meta["ka2_stripped"] = f"{anode} r={r:g}"
    return Pattern(x, np.maximum(y1, 0.0), meta)
