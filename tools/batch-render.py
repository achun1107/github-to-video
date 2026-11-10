# -*- coding: utf-8 -*-
"""批量渲染 + 混音 → 每条 18s 成片（卡点 BGM + 人声）。

  python tools/batch-render.py --limit 100 --jobs 2

每条：render.py 渲 raw.mp4 → mix-band 混音（128BPM 卡点 + 人声 + 侧链）→ final.mp4
"""
import json
import subprocess
import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'
MIX = SRC / 'tools/mix-batch.py'


def run(cmd, cwd, timeout=900):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)


def main():
    a = sys.argv[1:]
    limit = int(a[a.index('--limit') + 1]) if '--limit' in a else 100
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    items = idx[:limit]
    t0 = time.time()
    ok = fail = skip = 0
    for n, it in enumerate(items, 1):
        proj = ROOT / it['dir']
        final = proj / 'renders' / 'final.mp4'
        if final.exists():
            skip += 1
            continue
        try:
            r = run([sys.executable, 'engine/render.py', '.'], proj, timeout=900)
            if r.returncode != 0:
                fail += 1
                print(f'[{n}/{len(items)}] {it["repo"]:<36} RENDER FAIL')
                continue
            m = run([sys.executable, str(MIX), '.'], proj, timeout=600)
            if m.returncode != 0 or not final.exists():
                fail += 1
                print(f'[{n}/{len(items)}] {it["repo"]:<36} MIX FAIL {m.stderr[-150:]}')
                continue
            ok += 1
            print(f'[{n}/{len(items)}] {it["repo"]:<36} ok  {final.stat().st_size/1e6:.1f}MB  '
                  f'{int(time.time()-t0)}s', flush=True)
        except Exception as e:
            fail += 1
            print(f'[{n}/{len(items)}] {it["repo"]:<36} ERR {type(e).__name__}')
    print(f'\n完成 ok={ok} fail={fail} skip={skip}  用时 {int(time.time()-t0)}s')


if __name__ == '__main__':
    main()
