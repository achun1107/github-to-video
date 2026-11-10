# -*- coding: utf-8 -*-
"""批量配音 v3：精确落在 16–18 秒（约 125–140 字 @ 7.8 字/秒）。

  python tools/batch-tts3.py [--limit 100] [--workers 4]

v2 的文案约 180 字 → 21–24 秒，超了。v3 砍到 4 句、约 130 字，
并用实测时长做一次自动微调（超长则提速，偏短则降速），保证每条都贴着 18 秒。
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'
TARGET = 17.0          # 目标时长（片子 18s，留 1s 余量）
ACCEPT = (15.5, 18.2)


def script_for(d, hook, sub):
    star = d['starHuman'].replace('w', ' 万').replace('k', ' 千')
    name = d['name'].replace('-', ' ')
    month = str(int(d['created'][5:7]))
    day = str(int(d['created'][8:10]))
    lang = d['lang'] or '多种语言'
    forks = d['forkHuman'].replace('w', ' 万').replace('k', ' 千')

    parts = [
        f'{hook}。{sub}。',
        f'{name}，GitHub 上 {star} 个 Star，{forks} 个 Fork，{month} 月 {day} 号才上线。',
        f'它是 {lang} 写的，不是概念，是 clone 下来就能跑的仓库。',
        f'现在完全开源、本地就能部署，代码随便改。仓库名 {name}，GitHub 搜得到。',
    ]
    return ''.join(parts)


def synth(text, mp3, srt, rate):
    subprocess.run([sys.executable, '-m', 'edge_tts', '-t', text,
                    '-v', 'zh-CN-YunxiNeural', f'--rate={rate}', '--pitch=+5Hz',
                    '--write-media', str(mp3), '--write-subtitles', str(srt)],
                   check=True, capture_output=True)


def adur(p):
    o = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=nw=1:nk=1', str(p)], capture_output=True, text=True)
    try:
        return float(o.stdout.strip())
    except ValueError:
        return 0.0


def do(it):
    proj = ROOT / it['dir']
    d = json.loads((proj / 'content.json').read_text(encoding='utf-8'))
    text = script_for(d, it['hook'], it.get('sub', ''))
    mp3 = proj / 'audio/vo1.mp3'
    srt = proj / 'audio/vo1.srt'
    try:
        rate = '+30%'
        synth(text, mp3, srt, rate)
        dur = adur(mp3)
        # 自动微调一次：偏长就提速，偏短就降速（幅度有限，避免语速失真）
        if dur > ACCEPT[1]:
            delta = int((dur / TARGET - 1) * 100) + 2
            rate = f'+{min(60, 30 + delta)}%'
            synth(text, mp3, srt, rate)
            dur = adur(mp3)
        elif dur < ACCEPT[0]:
            rate = '+18%'
            synth(text, mp3, srt, rate)
            dur = adur(mp3)
        return it['repo'], len(text), round(dur, 2), rate
    except Exception as e:
        return it['repo'], 0, f'FAIL:{type(e).__name__}', ''


def main():
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 100
    workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 4
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))[:limit]
    res = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, r in enumerate(ex.map(do, idx), 1):
            res.append(r)
            if i % 20 == 0:
                print(f'  ...{i}/{len(idx)}', flush=True)

    good = [r for r in res if isinstance(r[2], float)]
    bad = [r for r in good if not (ACCEPT[0] <= r[2] <= ACCEPT[1])]
    err = [r for r in res if not isinstance(r[2], float)]
    if good:
        print(f'\n完成 {len(good)} 条；时长 {min(r[2] for r in good):.1f}–'
              f'{max(r[2] for r in good):.1f}s，均值 {sum(r[2] for r in good)/len(good):.2f}s')
    print(f'不合规 {len(bad)} 条，失败 {len(err)} 条')
    for b in bad[:6]:
        print(f'   {b[0]:<36} {b[2]}s  {b[3]}')


if __name__ == '__main__':
    main()
