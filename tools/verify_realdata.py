"""真实仪器谱回归：判定 + 完整 Rietveld 精修，打印可直接粘进验证文档的表。

为什么单独一个脚本
------------------
pytest 里的真实谱用例只断言「判过/判否」这一位，不检查精修的数值；而精修
数值（Rwp / GOF / 晶胞 / 尺寸）才是判定阶段预拟合晶胞、起点零点这些改动的
真实晴雨表。本脚本把它们逐条打出来，改动内核后跑一遍就知道有没有退化。

用法::

    python tools/verify_realdata.py                 # 默认目录
    python tools/verify_realdata.py <谱图目录>
    python tools/verify_realdata.py --no-refine     # 只判定（快）
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from lfp.core.io import read_pattern                     # noqa: E402
from lfp.core.profile.cif import parse_cif                # noqa: E402
from lfp.core.refine.api import (NotLFPError, identify_pattern,  # noqa: E402
                                run_analysis)
from lfp.core.refine.nonlinear import RefineConfig        # noqa: E402

DEFAULT_DIR = Path(r"D:/Project/XRD/XRData/smz geshi")

#: (文件名, 期望判定)。期望值来自人工物相确认，不是软件的自我确认。
CASES = [
    ("LiFePO4#01##20250520-100220_100.txt", True),
    ("LinSuanTieLi#1##20250527-141148_100.txt", True),
    ("FePO4#01##20250520-132913_100.txt", False),
    ("PVDF#01##20250527-161442_100.txt", False),
    ("LLZTO#01##20250521-130019_100.txt", False),
    ("ShiMo-C3#1##20250527-180340_100.txt", False),
    ("1. Si.txt", False),
    ("羟基磷灰石#01##20250522-094117_100.txt", False),
]


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    do_refine = "--no-refine" not in argv
    data_dir = Path(args[0]) if args else DEFAULT_DIR
    if not data_dir.is_dir():
        print(f"[跳过] 谱图目录不存在：{data_dir}")
        return 0

    struct = parse_cif(BASE / "lfp/data/lfp.cif")
    head = (f"{'file':30s} {'判':>3s} {'cov':>5s} {'t3':>3s} {'unexp':>6s} "
            f"{'rms/tol':>7s} {'Rwp':>6s} {'Rp':>6s} {'Rexp':>6s} {'GOF':>5s} "
            f"{'RB':>5s} {'D(nm)':>7s} {'ε(%)':>6s} {'a(Å)':>10s} {'s':>5s}")
    print(head)
    print("-" * len(head))
    fails = 0
    for name, expect in CASES:
        path = data_dir / name
        if not path.exists():
            print(f"{name[:30]:30s}  (缺样本)")
            continue
        pat = read_pattern(path)
        t0 = time.perf_counter()
        ident = identify_pattern(pat, struct)
        t_id = time.perf_counter() - t0
        ratio = ident.resid_ratio
        ok = "✓" if ident.is_lfp is expect else "✗"
        fails += ident.is_lfp is not expect
        line = (f"{name[:30]:30s} {ok:>3s} {ident.coverage:5.3f} "
                f"{ident.top_strong_matched:3d} {ident.unexplained:6.3f} "
                f"{ratio:7.2f}")
        if do_refine and ident.is_lfp:
            try:
                t1 = time.perf_counter()
                res = run_analysis(pat, struct, RefineConfig(), ident=ident)
                el = time.perf_counter() - t1
                rf = res.refinement.rf
                a = res.cell[0]
                rb = res.rbragg
                line += (f" {rf.rwp:6.2f} {rf.rp:6.2f} {rf.rexp:6.2f} "
                         f"{rf.gof:5.3f} "
                         f"{(rb or 0.0):5.2f} "
                         f"{(res.size_nm or 0):7.1f} "
                         f"{100 * (res.strain or 0):6.3f} {a:10.5f} {el:5.1f}")
            except Exception as exc:              # noqa: BLE001
                line += f"  精修失败: {exc}"
                fails += 1
        else:
            line += " " * 60
        print(line)
        print(f"{'':30s} 判定用时 {t_id:.2f} s")
    print(f"\n不符/失败: {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
