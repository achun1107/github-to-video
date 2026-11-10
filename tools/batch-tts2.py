# -*- coding: utf-8 -*-
"""批量配音 v2：文案加长到覆盖 18 秒全片（约 115–135 字 @ 8 字/秒）。

  python tools/batch-tts2.py [--limit 100] [--workers 4]

原来是 9 秒配音配 18 秒画面，第 10 秒起没人声。这次按 4 张卡的节奏写满：
  卡1 钩子 → 卡2 星数/上线 → 卡3 一句话是什么 → 卡4 怎么用/结论
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'


def script_for(d, hook, sub):
    star = d['starHuman'].replace('w', ' 万').replace('k', ' 千')
    name = d['name'].replace('-', ' ')
    month = d['created'][5:7].lstrip('0')
    day = d['created'][8:].lstrip('0')
    lang = d['lang'] or '多种语言'
    forks = d['forkHuman'].replace('w', ' 万').replace('k', ' 千')
    topics = [t for t in (d.get('topics') or []) if t.isascii()][:3]

    parts = [
        f'{hook}。{sub}。',                                    # 卡1
        f'{name}，GitHub 上 {star} 个 Star，{forks} 个 Fork，'
        f'{month} 月 {day} 号才上线。',                          # 卡2
        (f'它是用 {lang} 写的，' if lang else ''),
        (f'主打 {"、".join(topics)}，' if topics else ''),
        '不是概念，是 clone 下来就能跑的仓库。',                    # 卡3
        f'现在完全开源，本地就能部署，代码随便改。',                  # 卡4
        f'仓库名 {name}，GitHub 搜一下就能找到。',
    ]
    return ''.join(p for p in parts if p)


def synth(text, mp3, srt):
    subprocess.run([sys.executable, '-m', 'edge_tts', '-t', text,
                    '-v', 'zh-CN-YunxiNeural', '--rate=+28%', '--pitch=+5Hz',
                    '--write-media', str(mp3), '--write-subtitles', str(srt)],
                   check=True, capture_output=True)


def do(it):
    proj = ROOT / it['dir']
    d = json.loads((proj / 'content.json').read_text(encoding='utf-8'))
    text = script_for(d, it['hook'], it.get('sub', ''))
    try:
        synth(text, proj / 'audio/vo1.mp3', proj / 'audio/vo1.srt')
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                    '-of', 'default=nw=1:nk=1', str(proj / 'audio/vo1.mp3')],
                                   capture_output=True, text=True).stdout.strip())
        return it['repo'], len(text), round(dur, 2)
    except Exception as e:
        return it['repo'], 0, f'FAIL:{type(e).__name__}'


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

    durs = [r[2] for r in res if isinstance(r[2], float)]
    bad = [r for r in res if not isinstance(r[2], float) or r[2] < 15 or r[2] > 18.5]
    print(f'\n完成 {len(durs)} 条；时长 {min(durs):.1f}–{max(durs):.1f}s，'
          f'均值 {sum(durs)/len(durs):.2f}s')
    print(f'超出 15–18.5s 区间：{len(bad)} 条')
    for b in bad[:8]:
        print(f'   {b[0]:<36} {b[2]}')


if __name__ == '__main__':
    main()
