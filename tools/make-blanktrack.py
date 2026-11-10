# -*- coding: utf-8 -*-
"""生成「留白版」成片：去掉 BGM 轨，只保留人声 + 音效，供抖音站内挂曲。

  python tools/make-blanktrack.py [--workers 8]

为什么需要它：
  抖音规则要求「站内曲库选曲才免授权」（星图帮助中心 · 抖音视频制作音频选定范围）：
  入口 = 拍摄页选音乐 → 发现 → 歌单分类 → 品牌精选。
  站外内嵌的火爆原曲属未授权，会被限流/下架。
  所以成片留出音乐轨道，发布时在 App 里挂曲，既用上爆火 BGM，又不侵权。

输出：<工程>/renders/final-blank.mp4
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'


def do(it):
    proj = ROOT / it['dir']
    raw = proj / 'renders/raw.mp4'
    vo = proj / 'audio/vo1.mp3'
    if not raw.exists() or not vo.exists():
        return it['repo'], 'skip'
    out = proj / 'renders/final-blank.mp4'
    end = 18.0
    cmd = ['ffmpeg', '-hide_banner', '-y',
           '-i', str(raw), '-i', str(vo),
           '-filter_complex',
           f'[1:a]aresample=48000,pan=stereo|c0=c0|c1=c0,highpass=f=110,lowpass=f=4500,'
           f'volume=2.6,adelay=600|600[vo];[vo]apad=pad_dur={end}[vop];'
           f'[vop]alimiter=limit=0.85:attack=5:release=60:level=disabled[an]',
           '-map', '0:v', '-map', '[an]',
           '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000',
           '-movflags', '+faststart', '-t', f'{end}', str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return it['repo'], ('ok' if r.returncode == 0 else 'fail:' + r.stderr.strip()[-80:])


def main():
    workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 8
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    res = {'ok': 0, 'fail': 0, 'skip': 0}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for repo, st in ex.map(do, idx):
            res[st.split(':')[0]] = res.get(st.split(':')[0], 0) + 1
            if not st.startswith('ok'):
                print(f'  {repo:<38} {st}')
    print(f'留白版：ok={res["ok"]} fail={res["fail"]} skip={res["skip"]}')


if __name__ == '__main__':
    main()
