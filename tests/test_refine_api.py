"""精修编排（api.run_analysis）：判定闸门 + 分阶段精修 + 结果打包。

用合成谱做「可回收性」测试：起始晶胞给 1.0，合成时也用 1.0，因此精修
应当把晶胞找回 1.0 附近、窄峰还原成百纳米级晶粒、Rwp 落在个位数。
这不是精度竞赛，而是防止「接口改坏了但没报错」——Rwp 从 3 % 跳到 25 %
必须让测试红掉。
"""

from __future__ import annotations

import numpy as np
import pytest

from conftest import make_pattern
from lfp.core.refine.api import NotLFPError, run_analysis
from lfp.core.refine.nonlinear import RefineConfig


def _cfg(**kw) -> RefineConfig:
    base = dict(refine_cell=True, refine_zero=True, refine_size=True,
                refine_strain=True, refine_asym=True, refine_eta=True,
                refine_po=False, refine_uvw=False, refine_bfactor=False,
                n_bg=6, bg_mode="cheb", tmin=15.0, tmax=60.0, max_nfev=1200)
    base.update(kw)
    return RefineConfig(**base)


@pytest.fixture(scope="module")
def refined(struct):
    pat = make_pattern(struct, two_min=12.0, two_max=65.0, zero=0.03)
    return run_analysis(pat, struct, _cfg(), progress_cb=None)


@pytest.mark.slow
def test_refinement_quality(refined):
    assert refined.rwp < 12.0, f"Rwp 偏高：{refined.rwp:.2f} %"
    assert 0.5 < refined.gof < 2.0, f"GOF 异常：{refined.gof:.3f}"
    assert refined.rbragg is not None and refined.rbragg < 15.0


@pytest.mark.slow
def test_cell_recovered(refined):
    a, b, c, al, be, ga = refined.cell
    assert a == pytest.approx(10.329, rel=3e-3)
    assert b == pytest.approx(6.0065, rel=3e-3)
    assert c == pytest.approx(4.6908, rel=3e-3)
    assert (al, be, ga) == pytest.approx((90.0, 90.0, 90.0), abs=0.05)
    assert refined.volume == pytest.approx(291.02, rel=0.01)


@pytest.mark.slow
def test_microstructure_and_symmetry(refined):
    # 合成用 120 nm；Scherrer 反解允许 2 倍以内的偏差（与应变强相关）
    assert refined.size_nm is not None and 40.0 < refined.size_nm < 400.0
    assert refined.strain is not None and refined.strain < 5e-3
    sym = refined.symmetry
    assert sym.space_group == "Pnma" and sym.point_group == "mmm"
    assert sym.bravais == "oP"


@pytest.mark.slow
def test_result_payload_shapes(refined):
    n = refined.two_theta.size
    for arr in (refined.yobs, refined.ycalc, refined.diff, refined.background):
        assert arr.size == n
    assert np.allclose(refined.diff, refined.yobs - refined.ycalc)
    assert refined.refinement.n_params >= 5
    assert refined.stages and all(isinstance(s[1], float) for s in refined.stages)


@pytest.mark.slow
def test_not_lfp_raises(struct):
    """判定不通过时必须抛 NotLFPError，且携带判定证据供界面弹窗。"""
    from test_identify import _foreign_pattern

    with pytest.raises(NotLFPError) as exc:
        run_analysis(_foreign_pattern(), struct, _cfg())
    assert exc.value.result.is_lfp is False


@pytest.mark.slow
def test_ident_reuse_skips_recomputation(struct):
    """界面传入已有判定结果时应被复用（不再重算，且用其预拟合晶胞作起点）。"""
    from lfp.core.refine.api import identify_pattern

    pat = make_pattern(struct, two_min=12.0, two_max=65.0)
    ident = identify_pattern(pat, struct)
    res = run_analysis(pat, struct, _cfg(), ident=ident)
    assert res.identification is ident
    assert res.rwp < 12.0
