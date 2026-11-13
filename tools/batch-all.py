# -*- coding: utf-8 -*-
"""一条命令跑完全部 100 条（幂等，可中断续跑）。

  python tools/batch-all.py [--limit 100]

步骤：抓取 → 建工程 → 依赖 → 截图 → 配音 → 渲染混音 → 文案 → 总览
每步都会跳过已完成的项，所以断了可以重跑。
"""
import json
import subprocess
import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'


def step(name, args, timeout=3600):
    print(f'\n=== {name} ===', flush=True)
    t0 = time.time()
    r = subprocess.run([sys.executable] + args, cwd=SRC, capture_output=True, text=True, timeout=timeout)
    tail = (r.stdout or '').strip().split('\n')[-3:]
    for ln in tail:
        print('  ' + ln)
    if r.returncode:
        print('  [ERR]', (r.stderr or '')[-300:])
    print(f'  ({int(time.time()-t0)}s)', flush=True)
    return r.returncode == 0


def main():
    limit = sys.argv[sys.argv.index('--limit') + 1] if '--limit' in sys.argv else '100'
    ok = True
    if not (SRC / 'data/candidates.json').exists():
        ok &= step('1/8 抓取候选仓库', ['tools/harvest.py'])
    ok &= step('2/8 建工程（content+film+文案骨架）', ['tools/batch-build.py', '--limit', limit, '--root', str(ROOT)])
    ok &= step('3/8 补齐运行时依赖', ['tools/batch-deps.py', '--limit', limit])
    ok &= step('4/8 截图仓库页', ['tools/batch-shot.py', '--limit', limit], timeout=7200)
    ok &= step('5/8 合成配音', ['tools/batch-tts.py', '--limit', limit], timeout=7200)
    ok &= step('6/8 渲染 + 混音', ['tools/batch-render.py', '--limit', limit], timeout=14400)
    ok &= step('7/8 生成发布包', ['tools/batch-copy.py', '--limit', limit])
    ok &= step('8/8 总览页 + 验收报告', ['tools/make-gallery.py'])

    finals = list(ROOT.glob('*/renders/final.mp4'))
    print(f'\n完成：{len(finals)}/{limit} 条成片')


if __name__ == '__main__':
    main()
