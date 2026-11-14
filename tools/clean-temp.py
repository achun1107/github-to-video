# -*- coding: utf-8 -*-
"""清理 C 盘 TEMP：只删 24 小时以前的 DSH 快照目录。

  python tools/clean-temp.py [--hours 24] [--dry]

不碰今天正在用的目录，避免破坏当前会话的撤销状态。
"""
import os
import shutil
import sys
import time
from pathlib import Path

TEMP = Path(os.environ.get('TEMP', r'C:\Users\Default\AppData\Local\Temp'))
PATTERNS = ('dsh-workspace-changes-', 'playwright-', 'puppeteer_', 'scoped_dir')


def dir_size(p):
    total = 0
    for root, _dirs, files in os.walk(p):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def main():
    hours = float(sys.argv[sys.argv.index('--hours') + 1]) if '--hours' in sys.argv else 24.0
    dry = '--dry' in sys.argv
    cutoff = time.time() - hours * 3600

    cands, freed, failed = [], 0, 0
    for p in TEMP.iterdir():
        if not p.is_dir():
            continue
        if not any(p.name.startswith(pref) for pref in PATTERNS):
            continue
        try:
            if p.stat().st_mtime > cutoff:
                continue
        except OSError:
            continue
        cands.append(p)

    print(f'候选目录 {len(cands)} 个（早于 {hours:.0f} 小时）')
    for p in cands:
        sz = dir_size(p)
        if dry:
            print(f'  [dry] {p.name:<40} {sz/1e9:.2f} GB')
            freed += sz
            continue
        try:
            shutil.rmtree(p, ignore_errors=False)
            freed += sz
        except Exception:
            failed += 1

    print(f'{"预计可释放" if dry else "已释放"} {freed/1e9:.2f} GB，失败 {failed} 个')
    if not dry and freed:
        shutil.disk_usage.home if False else None
        u = shutil.disk_usage('C:/')
        print(f'C 盘剩余 {u.free/1e9:.2f} GB')


if __name__ == '__main__':
    main()
