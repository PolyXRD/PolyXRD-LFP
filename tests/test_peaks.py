"""寻峰：位置精度、SNR 过滤、去重。

寻峰是判定与报告的共同输入，最容易出的两类缺陷是
(1) 同一峰重复出 2–3 条（数值抖动），(2) 把基线噪声当峰。
这里用一个「3 个已知峰 + 噪声」的合成谱同时约束这两点。
"""

from __future__ import annotations

import numpy as np
import pytest

from lfp.core.dtypes import Pattern
from lfp.core.peaks import d_of, find_peaks


def _three_peak_pattern(seed=11) -> Pattern:
    x = np.arange(15.0, 50.0, 0.02)
    centers = [20.0, 29.7, 35.6]
    amps = [400.0, 1200.0, 500.0]
    y = np.full_like(x, 60.0)
    for c, a in zip(centers, amps):
        y += a * np.exp(-((x - c) ** 2) / (2 * 0.08 ** 2))
    y = np.random.default_rng(seed).poisson(y).astype(float)
    return Pattern(x, y, {"wavelength": 1.54056})


def test_positions_and_no_duplicates():
    pat = _three_peak_pattern()
    peaks = find_peaks(pat)
    found = np.array([p.two_theta for p in peaks])
    assert found.size >= 3
    for want in (20.0, 29.7, 35.6):
        assert np.min(np.abs(found - want)) < 0.03, f"未找到 {want}° 附近的峰"
    # 去重：位序严格递增且彼此间距不小于半高宽的 0.3 倍
    order = np.sort(found)
    gaps = np.diff(order)
    assert np.all(gaps > 0.05), f"存在重复峰: {order.round(3)}"


def test_strongest_peak_first_by_height():
    pat = _three_peak_pattern()
    peaks = find_peaks(pat)
    top = max(peaks, key=lambda p: p.height)
    assert abs(top.two_theta - 29.7) < 0.05


def test_snr_and_fit_quality_flags():
    pat = _three_peak_pattern()
    for p in find_peaks(pat):
        assert p.snr >= 3.0
        assert 0.0 <= p.eta <= 1.0
        assert p.fwhm > 0
        if p.fitted:
            assert p.r2 > 0.5        # 拟合成功的峰不能是「勉强贴上去」


def test_min_height_filters_weak_peaks():
    pat = _three_peak_pattern()
    few = find_peaks(pat, min_rel_height=0.6)
    many = find_peaks(pat, min_rel_height=0.05, max_peaks=60)
    assert len(few) <= len(many)
    assert all(p.height >= 0.5 * max(q.height for q in many) for p in few)


def test_empty_or_flat_spectrum():
    x = np.arange(10.0, 30.0, 0.02)
    flat = Pattern(x, np.full_like(x, 100.0))
    assert find_peaks(flat) == []
    assert find_peaks(Pattern(x[:5], np.zeros(5))) == []


def test_d_of_bragg():
    assert d_of(29.7, 1.54056) == pytest.approx(3.005, abs=0.01)
