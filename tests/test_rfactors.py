"""R 因子口径：GSAS-II 口径（背景计入、σ=√max(y,1)）。

最容易出错的是「GOF 的定义」与「完美拟合是否真的给 0」。这里把两者钉住：
若有人把 Rexp 写成不含 (N−P)，GOF 会系统性偏大，最终导致界面误判拟合质量。
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from lfp.core.refine.rfactors import RFactors, compute_rfactors


def test_perfect_fit_gives_zero_r():
    y = np.array([100.0, 200.0, 50.0, 10.0])
    rf = compute_rfactors(y, y, n_params=0)
    assert rf.rwp == pytest.approx(0.0, abs=1e-12)
    assert rf.rp == pytest.approx(0.0, abs=1e-12)
    assert rf.chi2 == pytest.approx(0.0, abs=1e-12)


def test_rexp_formula():
    """Rexp = 100·√((N−P) / Σ w·y²)，w = 1/max(y,1)。"""
    y = np.array([100.0, 200.0, 50.0, 10.0])
    n, p = y.size, 2
    w = 1.0 / np.maximum(y, 1.0)
    expect = 100.0 * math.sqrt((n - p) / float(np.sum(w * y * y)))
    rf = compute_rfactors(y, y * 1.05, n_params=p)
    assert rf.rexp == pytest.approx(expect, rel=1e-12)


def test_gof_is_rwp_over_rexp():
    rf = RFactors(rwp=20.0, rp=15.0, rexp=10.0, chi2=4.0)
    assert rf.gof == pytest.approx(2.0)


def test_gof_infinite_when_rexp_zero():
    assert RFactors(rwp=1.0, rp=1.0, rexp=0.0, chi2=0.0).gof == float("inf")


def test_more_params_lower_rexp_and_raise_chi2():
    """P 越大 → (N−P) 越小 → Rexp 越小 → 折算 χ² 与 GOF 越大。

    这是 Rexp 的定义性质（自由度惩罚），也是「为什么不能靠加参数把 GOF 刷下去」
    的数学来源：加参数只会让 GOF 变大，不会让它变小。
    """
    y = np.linspace(50, 500, 200)
    yc = y * 0.97
    a = compute_rfactors(y, yc, n_params=1)
    b = compute_rfactors(y, yc, n_params=20)
    assert b.rexp < a.rexp
    assert b.chi2 > a.chi2
    assert a.rwp == pytest.approx(b.rwp)        # Rwp 与 P 无关
    # χ² 就是 (Rwp/Rexp)²，即折算卡方；GOF = √χ²
    for rf in (a, b):
        assert rf.chi2 == pytest.approx((rf.rwp / rf.rexp) ** 2)
        assert rf.gof == pytest.approx(math.sqrt(rf.chi2))
