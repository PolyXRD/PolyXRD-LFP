"""pytest 公共夹具。

设计原则
--------
1. **不依赖外部数据**：核心测试全部用内置 CIF 合成谱，任何人 clone 下来都能跑。
2. **真实数据可选**：若设置了环境变量 ``POLYXRD_LFP_DATA``（指向仪器导出的
   谱图目录），则额外跑一组「真实谱判定」回归；目录不存在时自动 skip，
   而不是让整个测试套件红掉。
3. **随机种子固定**：泊松噪声用固定 seed，测试结果可复现。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lfp.core.dtypes import Pattern                     # noqa: E402
from lfp.core.profile.cif import parse_cif              # noqa: E402
from lfp.core.profile.forward import phase_profile       # noqa: E402
from lfp.core.refine.nonlinear import initial_params     # noqa: E402

#: Cu Kα1（Å）——家族统一口径
CU_KA1 = 1.54056

#: 真实谱图目录（可选）；Windows 上仪器导出的 txt 就在这个目录下
REAL_DATA_ENV = "POLYXRD_LFP_DATA"
DEFAULT_REAL_DATA = Path(r"D:/Project/XRD/XRData/smz geshi")


def _builtin_cif() -> Path:
    return ROOT / "lfp" / "data" / "lfp.cif"


@pytest.fixture(scope="session")
def struct():
    """内置 LiFePO4 结构（Pnma，Z=4）。"""
    return parse_cif(_builtin_cif())


@pytest.fixture(scope="session")
def real_data_dir() -> Path | None:
    """真实谱图目录；不存在时返回 None（对应测试 skip）。"""
    cand = Path(os.environ.get(REAL_DATA_ENV, DEFAULT_REAL_DATA))
    return cand if cand.is_dir() else None


def make_pattern(struct, *, two_min: float = 10.0, two_max: float = 90.0,
                 step: float = 0.02, size_nm: float = 120.0,
                 strain: float = 5e-4, zero: float = 0.02,
                 scale: float = 1000.0, background: float = 200.0,
                 noise: bool = True, seed: int = 20260218) -> Pattern:
    """用内置结构合成一条「像真实仪器测出来的」LFP 谱。

    强度按真实计数水平给（背景 ~200、最强峰 ~1200 counts），而不是直接用
    ``phase_profile`` 的任意单位（那里峰高可达 1e6 量级）。这不是美观问题：
    计数水平决定了泊松噪声的相对大小，进而决定 Rwp/Rexp/GOF 的可达范围——
    若合成谱的计数大到「几乎无噪声」，任何真实模型都拟合不到那个精度，
    GOF 会虚假地爆到几百，测试就失去意义了。
    """
    # 仪器项（W, eta）刻意沿用 initial_params 的默认值：合成谱与精修模型
    # 必须共用同一套仪器假设，否则「拟合不上」反映的是假设不一致，而不是算法差
    prm = initial_params(wavelength=CU_KA1).with_changes(
        zero=zero, size_nm=size_nm, strain=strain)
    grid = np.arange(two_min, two_max + 1e-9, step)
    prof = np.asarray(phase_profile(struct, grid, prm, 5.0, 120.0),
                      dtype=np.float64)
    top = float(prof.max())
    if top > 0:
        prof = prof / top
    y = background + scale * prof
    if noise:
        rng = np.random.default_rng(seed)
        y = rng.poisson(np.maximum(y, 1.0)).astype(np.float64)
    return Pattern(grid, y, {"wavelength": CU_KA1, "anode": "Cu"})


@pytest.fixture(scope="session")
def lfp_pattern(struct) -> Pattern:
    """合成 LFP 谱（判定/精修测试共用）。"""
    return make_pattern(struct)
