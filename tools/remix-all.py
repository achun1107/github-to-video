# -*- coding: utf-8 -*-
"""把所有已渲染的片子按最新混音脚本重新混一遍（不重渲画面，几秒/条）。

  python tools/remix-all.py [--limit 100]
"""
import json
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'
MIX = SRC / 'tools/mix-batch.py'


def main():
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 100
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    ok = fail = skip = 0
    for it in idx[:limit]:
        proj = ROOT / it['dir']
        raw = proj / 'renders/raw.mp4'
        if not raw.exists():
            skip += 1
            continue
        if not (proj / 'audio/vo1.mp3').exists():
            skip += 1
            continue
        r = None
        for attempt in range(2):
            try:
                r = subprocess.run([sys.executable, str(MIX), '.'], cwd=proj,
                                   capture_output=True, text=True, timeout=1800)
                if r.returncode == 0:
                    break
            except subprocess.TimeoutExpired:
                print(f'{it["repo"]:<36} timeout, retry')
        if r is not None and r.returncode == 0:
            ok += 1
        else:
            fail += 1
            err = (r.stderr[-150:] if r else 'timeout').replace(chr(10), ' ')
            print(f'{it["repo"]:<36} FAIL {err}')
    print(f'remix: ok={ok} fail={fail} skip={skip}')


if __name__ == '__main__':
    main()
