# -*- coding: utf-8 -*-
"""逐条检查配音是否覆盖全片：把 18 秒切成 9 段，任何一段低于 -30dB 就算断档。

  python tools/check-voice.py
"""
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'
THRESH = -30.0


def seg_rms(f, a, b):
    p = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(a), '-to', str(b), '-i', str(f),
                        '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True)
    x = np.frombuffer(p.stdout, dtype=np.float32)
    return round(float(20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9)), 1) if len(x) else -99.0


def check(it):
    f = ROOT / it['dir'] / 'renders' / 'final.mp4'
    if not f.exists():
        return it['repo'], 'MISSING', []
    segs = [seg_rms(f, a, a + 2) for a in range(0, 18, 2)]
    dead = [a for a, v in zip(range(0, 18, 2), segs) if v < THRESH]
    return it['repo'], ('OK' if not dead else 'GAP'), dead


def main():
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    bad = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for repo, st, dead in ex.map(check, idx):
            if st != 'OK':
                bad.append((repo, st, dead))
                print(f'  {repo:<38} {st} 断档段={dead}')
    print(f'\n配音覆盖检查：通过 {len(idx)-len(bad)}/{len(idx)}')


if __name__ == '__main__':
    main()
