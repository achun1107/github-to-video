# -*- coding: utf-8 -*-
"""校验「画面字幕 = 解说」：从成片抽帧做 OCR 不现实，
改成校验源数据一致性 + 抽帧人工比对点。

  python tools/check-subs-sync.py

校验三件事：
  1. vo-subs.js 与 vo1.srt 逐句一致（文字与时间码）
  2. film.js 确实在使用 window.VO_SUBS
  3. 成片抽帧：字幕出现的时间点有变化（说明没整段缺失）
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'


def parse_srt(p):
    if not p.exists():
        return []
    txt = p.read_text(encoding='utf-8-sig', errors='replace')
    out = []
    for b in re.split(r'\n\s*\n', txt.strip()):
        lines = [x for x in b.strip().split('\n') if x.strip()]
        if len(lines) < 3:
            continue
        m = re.search(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)', lines[1])
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        a = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        b2 = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        t = ''.join(lines[2:]).strip().replace(' 万,个', ' 万').replace(' 千,个', ' 千')
        out.append((round(a, 3), round(b2, 3), t))
    return out


def chip_dark_ratio(frame_path, y0=1440, y1=1590):
    """说明条区域是否为深色块（说明字幕存在）"""
    im = Image.open(frame_path).convert('RGB')
    a = np.asarray(im).astype(int)[y0:y1, 120:960]
    dark = (a.max(axis=2) < 110).mean()
    return float(dark)


def main():
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    bad_txt, bad_frame = [], []
    tmp = ROOT / '_qc_tmp.png'

    for it in idx:
        proj = ROOT / it['dir']
        srt = parse_srt(proj / 'audio/vo1.srt')
        vs = proj / 'vo-subs.js'
        if not vs.exists():
            bad_txt.append((it['repo'], '缺 vo-subs.js'))
            continue
        raw = vs.read_text(encoding='utf-8')
        subs = json.loads(raw[raw.index('['): raw.rindex(']') + 1])
        if len(subs) != len(srt):
            bad_txt.append((it['repo'], f'句数不符 {len(subs)} vs {len(srt)}'))
            continue
        for s, (a, b, t) in zip(subs, srt):
            if abs(s['a'] - a) > 0.02 or s['zh'] != t:
                bad_txt.append((it['repo'], f'句子不一致: {s["zh"][:18]} vs {t[:18]}'))
                break
        # film.js 是否引用 VO_SUBS
        if 'window.VO_SUBS' not in (proj / 'film.js').read_text(encoding='utf-8'):
            bad_txt.append((it['repo'], 'film.js 未使用 VO_SUBS'))

        # 抽 3 帧看字幕块是否存在
        frames_ok = []
        for t in (2.0, 7.0, 13.0):
            subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i',
                            str(proj / 'renders' / 'final.mp4'), '-frames:v', '1', '-y', str(tmp)],
                           capture_output=True)
            if tmp.exists():
                frames_ok.append(chip_dark_ratio(tmp) > 0.05)
        if frames_ok and not all(frames_ok):
            bad_frame.append((it['repo'], frames_ok))

    tmp.unlink(missing_ok=True)
    for r, e in bad_txt[:8]:
        print(f'  [字幕源] {r:<36} {e}')
    for r, f in bad_frame[:8]:
        print(f'  [抽帧]   {r:<36} {f}')
    print(f'\n字幕=解说 校验：{len(idx)-len(bad_txt)}/{len(idx)} 通过；抽帧异常 {len(bad_frame)} 条')


if __name__ == '__main__':
    main()
