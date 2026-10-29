"""拟合优度的界面判读档位（界面与报告共用，避免两处各写一套阈值）。

Rwp 的绝对值与**计数统计**强相关：同一条谱，快扫（低计数）时 Rexp 本身就
很高，Rwp 不可能做到 10% 以下；慢扫高计数时容易达到 2–5%。因此单看 Rwp
会给用户错误信号，本模块同时看 GOF = Rwp/Rexp：

======================  ============================================
判据                    结论
======================  ============================================
Rwp ≤ 10%               优秀（绝对水平好）
10% < Rwp ≤ 15%         良好
Rwp > 15% 但 GOF ≤ 1.2  拟合已充分（Rwp 高是数据计数统计所限）
15% < Rwp ≤ 20%         可接受
Rwp > 20% 且 GOF > 1.2  偏低，建议检查模型
======================  ============================================

GOF < 1 说明逐点残差比泊松噪声还小（数据被平滑/合并过，或 σ 高估），
此时 Rwp 的绝对值同样不可直接与「≤10%」的行业经验值比较。
"""

from __future__ import annotations

RWP_EXCELLENT = 10.0
RWP_GOOD = 15.0
RWP_ACCEPTABLE = 20.0
GOF_WELL_FIT = 1.2


def rwp_verdict(rwp: float, gof: float | None = None) -> tuple[str, str]:
    """返回 (i18n 键, 语义色档位)。"""
    if rwp <= RWP_EXCELLENT:
        return "verdict.rwp.excellent", "good"
    if rwp <= RWP_GOOD:
        return "verdict.rwp.good", "fair"
    if gof is not None and gof <= GOF_WELL_FIT:
        return "verdict.rwp.consistent", "good"
    if rwp <= RWP_ACCEPTABLE:
        return "verdict.rwp.acceptable", "warn"
    return "verdict.rwp.poor", "bad"


def gof_verdict(gof: float) -> tuple[str, str]:
    """GOF 档位（1 附近最好；<1 表示 σ 偏大而非「更好」）。"""
    if 0.8 <= gof <= 1.2:
        return "verdict.gof.good", "good"
    if 1.2 < gof <= 2.0:
        return "verdict.gof.fair", "warn"
    if gof > 2.0:
        return "verdict.gof.poor", "bad"
    return "verdict.gof.low", "warn"


def rbragg_level(rb: float | None) -> str:
    """R_Bragg 语义色（经验档位见 :mod:`lfp.core.refine.rbragg`）。"""
    if rb is None:
        return "neutral"
    if rb <= 5.0:
        return "good"
    if rb <= 10.0:
        return "fair"
    return "bad"
