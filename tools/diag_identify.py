"""判定模块回归表：一条谱一行，打印全部判据与闸门的中间量。

调 ``lfp.core.identify`` 的容差/阈值/反解口径时先跑它——所有阈值都该由
这张表上的实测数字来定，而不是拍脑袋。

用法::

    python tools/diag_identify.py            # 合成谱 + 真实谱（目录存在时）
    python tools/diag_identify.py --real     # 只看真实谱
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tests"))

import numpy as np                                                  # noqa: E402
from conftest import make_pattern, DEFAULT_REAL_DATA                # noqa: E402
from lfp.core.identify import COVERAGE_PASS, RESID_RMS_RATIO, UNEXPLAINED_PASS  # noqa: E402
from lfp.core.profile.cif import parse_cif                           # noqa: E402
from lfp.core.profile.forward import scaled_cell                     # noqa: E402
from lfp.core.refine.api import identify_pattern                     # noqa: E402

HEAD = (f"{'case':34s} {'LFP':>4s} {'cov':>6s} {'top3':>5s} {'unexp':>6s} "
        f"{'dz':>8s} {'strain%':>8s} {'npair':>5s} {'tol':>6s} "
        f"{'rms':>7s} {'rms/tol':>8s} {'model':>6s}")


def row(label: str, res) -> str:
    ratio = res.resid_rms / res.tolerance if res.tolerance else float("inf")
    return (f"{label[:34]:34s} {str(res.is_lfp):>4s} {res.coverage:6.3f} "
            f"{res.top_strong_matched:5d} {res.unexplained:6.3f} "
            f"{res.zero_shift:+8.4f} {100 * res.strain_scale:+8.3f} "
            f"{res.n_matched:5d} {res.tolerance:6.3f} {res.resid_rms:7.4f} "
            f"{ratio:8.3f} {str(res.model_ok):>6s}")


def main() -> int:
    struct = parse_cif(BASE / "lfp/data/lfp.cif")
    only_real = "--real" in sys.argv
    print(HEAD)
    print("-" * len(HEAD))
    bad = 0

    if not only_real:
        synth = [
            ("synth plain (zero=.02)", make_pattern(struct), True),
            ("synth zero=+0.15", make_pattern(struct, zero=0.15), True),
            ("synth zero=-0.12", make_pattern(struct, zero=-0.12), True),
            ("synth iso +0.4%", make_pattern(scaled_cell(struct, 1.004, 1.004, 1.004),
                                             zero=0.05), True),
            ("synth iso -0.6%", make_pattern(scaled_cell(struct, 0.994, 0.994, 0.994),
                                             zero=0.02), True),
            ("synth aniso a+1% b-0.5%", make_pattern(
                scaled_cell(struct, 1.01, 0.995, 1.0), zero=0.05), False),
            ("synth aniso all +/-1%", make_pattern(
                scaled_cell(struct, 1.01, 0.99, 1.005), zero=0.05), False),
            ("synth aniso a+1% c+0%", make_pattern(
                scaled_cell(struct, 1.01, 1.0, 1.0), zero=0.02), False),
        ]
        for label, pat, expect in synth:
            res = identify_pattern(pat, struct)
            print(row(label, res), "" if res.is_lfp is expect else "  <<< 不符")
            bad += int(res.is_lfp is not expect)

    real_dir = Path(DEFAULT_REAL_DATA)
    if real_dir.is_dir():
        from lfp.core.io import read_pattern

        cases = [
            ("LiFePO4#01##20250520-100220_100.txt", True),
            ("LinSuanTieLi#1##20250527-141148_100.txt", True),
            ("FePO4#01##20250520-132913_100.txt", False),
            ("PVDF#01##20250527-161442_100.txt", False),
            ("LLZTO#01##20250521-130019_100.txt", False),
            ("ShiMo-C3#1##20250527-180340_100.txt", False),
            ("1. Si.txt", False),
            ("羟基磷灰石#01##20250522-094117_100.txt", False),
        ]
        for name, expect in cases:
            p = real_dir / name
            if not p.exists():
                print(f"{name[:34]:34s}   (缺样本)")
                continue
            res = identify_pattern(read_pattern(p), struct)
            print(row(name, res), "" if res.is_lfp is expect else "  <<< 不符")
            bad += int(res.is_lfp is not expect)
    else:
        print(f"（真实谱目录不存在：{real_dir}）")

    print(f"\n阈值: coverage>={COVERAGE_PASS}  unexplained<={UNEXPLAINED_PASS}  "
          f"rms/tol<={RESID_RMS_RATIO}")
    print(f"不符: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
