# -*- coding: utf-8 -*-
"""全量检查：每条的说明条是否在应该出现的时候出现。

  python tools/check-sub-presence.py [--workers 8]

对每条取 6 个时间点（按 vo-subs 的时间码），比较「有字幕」与「无字幕」时的深色占比，
低于阈值说明该帧没画字幕。
"""
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'
THRESH = 0.10


def load_subs(proj):
    p = proj / 'vo-subs.js'
    if not p.exists():
        return []
    raw = p.read_text(encoding='utf-8')
    try:
        return json.loads(raw[raw.index('['): raw.rindex(']') + 1])
    except Exception:
        return []


def dark_ratio(img_path):
    a = np.asarray(Image.open(img_path).convert('RGB')).astype(int)[1390:1600, 90:990]
    return float((a.max(axis=2) < 110).mean())


def check(it):
    proj = ROOT / it['dir']
    mp4 = proj / 'renders' / 'final.mp4'
    if not mp4.exists():
        return it['repo'], 'MISSING', []
    subs = load_subs(proj)
    if not subs:
        return it['repo'], 'NO_SUBS_FILE', []

    # 每条字幕取中点（确保在句子内部）
    spots = []
    for s in subs:
        mid = (s['a'] + s['b']) / 2
        if 0.3 < mid < 17.6:
            spots.append(round(mid, 2))
    spots = spots[:6]

    bad = []
    with tempfile.TemporaryDirectory() as td:
        for t in spots:
            out = Path(td) / f'f{t}.png'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(mp4), '-ss', str(t),
                            '-frames:v', '1', str(out)], capture_output=True)
            if not out.exists():
                bad.append(t)
                continue
            if dark_ratio(out) < THRESH:
                bad.append(t)
    return it['repo'], ('OK' if not bad else 'NOCAP'), bad


def main():
    workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 8
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    bad = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for repo, st, spots in ex.map(check, idx):
            if st != 'OK':
                bad.append((repo, st, spots))
                print(f'  {repo:<40} {st} {spots}')
    print(f'\n字幕存在性：{len(idx)-len(bad)}/{len(idx)} 通过')


if __name__ == '__main__':
    main()
