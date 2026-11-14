# -*- coding: utf-8 -*-
"""下载可商用的真实 BGM（Kevin MacLeod，CC BY 4.0）。

  python tools/get-real-bgm.py

为什么不把音频放进仓库：CC BY 4.0 允许再分发，但仓库应保持轻量，
且第三方音频应始终从版权方获取。这里只提供下载 + 说明。
"""
import sys
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / 'audio' / 'bgm' / 'real'
BASE = 'https://incompetech.com/music/royalty-free/mp3-royaltyfree/'

# 曲目 → 听感说明
TRACKS = {
    'EDM Detection Mode': '电子、律动强，129 BPM',
    'Electro Cabello': '低频最重，117 BPM',
    'Rocket Power': '慢但厚重，73 BPM',
    'Electrodoodle': '轻电子，适合快节奏口播',
    'OctoBlues': '蓝调电子，个性强',
}

ATTRIBUTION = """Music: Kevin MacLeod (incompetech.com)
Licensed under Creative Commons: By Attribution 4.0
https://creativecommons.org/licenses/by/4.0/

（发布时把上面三行放进文案末尾或视频简介）
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    for title, note in TRACKS.items():
        url = BASE + urllib.parse.quote(title) + '.mp3'
        dst = OUT / f'{title}.mp3'
        if dst.exists():
            print(f'  跳过（已存在）{dst.name}')
            ok += 1
            continue
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=60) as r, open(dst, 'wb') as f:
                f.write(r.read())
            print(f'  OK  {dst.name:<24} {dst.stat().st_size/1e6:.1f} MB  {note}')
            ok += 1
        except Exception as e:
            print(f'  FAIL {title}: {type(e).__name__}')
            fail += 1

    (OUT / 'ATTRIBUTION.txt').write_text(ATTRIBUTION, encoding='utf-8')
    print(f'\n完成 ok={ok} fail={fail} → {OUT}')
    print('署名要求见 ATTRIBUTION.txt，发布时必须带上。')


if __name__ == '__main__':
    main()
