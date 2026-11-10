# -*- coding: utf-8 -*-
"""画面质检：每条的 4 张卡各抽 1 帧，检查非黑屏、有文字、截图卡有真实像素。

  python tools/qc-frames.py [--workers 6]
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'
# 4 张卡的中段时刻（避开切换淡出）
TS = [2.5, 6.2, 10.5, 15.0]


def check(it):
    proj = ROOT / it['dir']
    f = proj / 'renders' / 'final.mp4'
    if not f.exists():
        return it['repo'], 'MISSING', []
    notes = []
    tmp = proj / 'review' / '_qc.png'
    tmp.parent.mkdir(exist_ok=True)
    for t in TS:
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', str(f), '-frames:v', '1',
                        '-y', str(tmp)], check=False, capture_output=True)
        if not tmp.exists():
            return it['repo'], 'NO_FRAME', notes
        im = Image.open(tmp).convert('RGB')
        a = np.asarray(im).astype(int)
        mean = a.mean()
        uniq = len(np.unique(a.reshape(-1, 3), axis=0))
        if mean < 12:
            notes.append(f't={t} 黑屏 mean={mean:.1f}')
        elif uniq < 400:
            notes.append(f't={t} 画面单调 uniq={uniq}')
    tmp.unlink(missing_ok=True)
    return it['repo'], ('OK' if not notes else 'WARN'), notes


def main():
    workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 6
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    bad = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for repo, st, notes in ex.map(check, idx):
            if st != 'OK':
                bad.append((repo, st, notes))
                print(f'  {repo:<38} {st} {"; ".join(notes)[:80]}')
    print(f'\n画面质检：通过 {len(idx)-len(bad)}/{len(idx)}')
    return bad


if __name__ == '__main__':
    main()
