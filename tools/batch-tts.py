# -*- coding: utf-8 -*-
"""批量配音：每条只用「数字 + 项目名」串一句，edge-tts 合成 8 秒，避免 100 条写稿。

  python tools/batch-tts.py --limit 100

每条配音脚本模板（数据驱动，不编造）：
  「<钩子>。<项目名>，<星数>个 Star，<创建日期>上线。<一句话简介>。」
长度控制在 9–13 秒，配合 34.8s 的画面做前段解说。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'


def script_for(d, hook):
    """只用中文能读通的部分：英文简介不硬读，改成说标签/语言。"""
    star = d['starHuman'].replace('w', ' 万').replace('k', ' 千')
    name = d['name'].replace('-', ' ')
    month = d['created'][5:7].lstrip('0')
    day = d['created'][8:].lstrip('0')
    lang = d['lang'] or ''
    topics = [t for t in (d.get('topics') or []) if t.isascii()][:2]
    head = f'{hook}。{name}，GitHub 上 {star} 个 Star'
    tail = f'{month} 月 {day} 号才上线'
    if lang:
        tail += f'，{lang} 写的'
    if topics:
        tail += f'，主打 {"、".join(topics)}'
    return f'{head}，{tail}。'


def synth(text, mp3, srt):
    subprocess.run([sys.executable, '-m', 'edge_tts', '-t', text,
                    '-v', 'zh-CN-YunxiNeural', '--rate=+35%', '--pitch=+5Hz',
                    '--write-media', str(mp3), '--write-subtitles', str(srt)],
                   check=True, capture_output=True)


def main():
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 100
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    todo = [it for it in idx[:limit] if not (ROOT / it['dir'] / 'audio/vo1.mp3').exists()]
    print(f'待合成 {len(todo)} 条（已跳过 {limit - len(todo)} 条）')
    for n, it in enumerate(todo, 1):
        proj = ROOT / it['dir']
        d = json.loads((proj / 'content.json').read_text(encoding='utf-8'))
        text = script_for(d, it['hook'])
        aud = proj / 'audio'
        aud.mkdir(exist_ok=True)
        try:
            synth(text, aud / 'vo1.mp3', aud / 'vo1.srt')
            # 复制一份提示音轨（无第二条人声，用空白占位保持混音脚本兼容）
            blank = aud / 'vo2.mp3'
            if not blank.exists():
                subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi',
                                '-i', 'anullsrc=r=48000:cl=stereo', '-t', '0.1', '-c:a', 'libmp3lame',
                                str(blank)], check=True)
            print(f'[{n}/{len(todo)}] {it["repo"]:<38} ok')
        except Exception as e:
            print(f'[{n}/{len(todo)}] {it["repo"]:<38} FAIL {type(e).__name__}')


if __name__ == '__main__':
    main()
