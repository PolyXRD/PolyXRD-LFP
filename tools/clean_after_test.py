#!/usr/bin/env python3
"""清理测试 / 构建过程产物（可再生文件），源码一律不动。

保留（永不删除）
----------------
* 所有 ``*.py`` / ``*.spec`` / ``*.bat`` / ``*.iss`` / ``*.md`` —— 包括
  ``tests/`` 与 ``tools/`` 下的测试代码、诊断脚本（以后要复用）
* ``docs/``（含 ``docs/evidence/`` 截图与报告证据，README 引用，属交付物）
* ``installer/`` ``resources/`` 源码包 ``tests/out/.gitkeep``
* ``dist/`` 的两个交付物（旧版本的清理由 ``tidy_dist.bat`` 负责）

删除（每次测试 / 构建后都该清）
--------------------------------
* ``build/``            PyInstaller 中间目录（几百 MB，构建时 --clean 会重建）
* ``__pycache__/`` ``.pytest_cache/`` ``.ruff_cache/`` ``.mypy_cache/``
* ``build*.log``        构建日志
* ``tests/out/`` 下除 ``.gitkeep`` 外的全部（冒烟截图 / HTML / 中间谱）
* 根目录 ``_*.png`` ``_*.html``（临时证据，正式证据在 docs/evidence/）
* ``%TEMP%/pxrd_*_ver.txt`` 版本临时文件

用法
----
    python tools/clean_after_test.py            # 执行清理
    python tools/clean_after_test.py --dry      # 只列清单和体积，不删
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CACHE_DIRS = (".pytest_cache", ".ruff_cache", ".mypy_cache")


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024.0
    return f"{n:.1f} GB"


def _size(path: Path) -> int:
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for name in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass
    return total


def _rm(path: Path) -> bool:
    try:
        if path.is_symlink() or path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path, onerror=_force_rm)
        return not path.exists()
    except OSError:
        return False


def _force_rm(func, path, _exc):  # noqa: ANN001 - shutil callback signature
    """Windows 只读文件 / 被占用时的兜底。"""
    try:
        os.chmod(path, 0o777)
        func(path)
    except OSError:
        pass


def collect() -> list[Path]:
    items: list[Path] = []

    build = ROOT / "build"
    if build.is_dir():
        items.append(build)

    for name in CACHE_DIRS:
        p = ROOT / name
        if p.is_dir():
            items.append(p)

    for p in ROOT.rglob("__pycache__"):
        if p.is_dir() and "build" not in p.relative_to(ROOT).parts:
            items.append(p)

    items.extend(p for p in ROOT.glob("build*.log") if p.is_file())

    out = ROOT / "tests" / "out"
    if out.is_dir():
        items.extend(p for p in out.iterdir() if p.name != ".gitkeep")

    for pattern in ("_*.png", "_*.html"):
        items.extend(p for p in ROOT.glob(pattern) if p.is_file())

    tmp = Path(tempfile.gettempdir())
    if tmp.is_dir():
        items.extend(p for p in tmp.glob("pxrd_*_ver.txt") if p.is_file())

    return items


def main() -> int:
    ap = argparse.ArgumentParser(description="清理测试/构建过程产物")
    ap.add_argument("--dry", action="store_true", help="只列清单，不删除")
    args = ap.parse_args()

    if not (ROOT / "tests").is_dir() and not list(ROOT.glob("*.spec")):
        print(f"[ABORT] {ROOT} 不像 PolyXRD 项目根（缺 tests/ 与 *.spec），未做任何删除。")
        return 1

    items = collect()
    if not items:
        print(f"[clean] {ROOT.name}: 没有需要清理的产物，环境已经是干净的。")
        return 0

    print(f"[clean] {ROOT.name}  ({'dry-run' if args.dry else '执行'})")
    freed = 0
    removed = failed = 0
    for p in sorted(items, key=lambda x: str(x).lower()):
        rel = p.relative_to(ROOT) if ROOT in p.parents else p
        size = _size(p)
        if args.dry:
            print(f"  - {rel}  ({_human(size)})")
            freed += size
            continue
        ok = _rm(p)
        if ok:
            removed += 1
            freed += size
            print(f"  del {rel}  ({_human(size)})")
        else:
            failed += 1
            print(f"  FAIL {rel}  (被占用或无权限)")

    keep = "tests/*.py  tools/*.py  docs/  installer/  resources/  dist/(两个交付物)"
    if args.dry:
        print(f"[dry] 共 {len(items)} 项，可释放 {_human(freed)}；保留 {keep}")
    else:
        print(f"[clean] 删除 {removed} 项，失败 {failed} 项，释放 {_human(freed)}；保留 {keep}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
