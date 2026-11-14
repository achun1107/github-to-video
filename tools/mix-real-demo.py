# -*- coding: utf-8 -*-
"""用真实曲目混出对比视频，自动按目标电平计算增益。

  python tools/mix-real-demo.py
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r'D:\DSH\achun')
SRC = ROOT / 'video-goofish'
PROJ = ROOT / 'video-batch' / 'gathin23-cleanyourtv'
MIX = SRC / 'tools' / 'mix-batch.py'
BGM = SRC / 'audio' / 'bgm'
OUT = ROOT / '预览'
TARGET_BGM_DB = -17.0   # 侧链还会压约 4.3dB，实测落在 -21.3          # 混音里 BGM 的目标电平（实测人声约 -13.2）


def rms_of(p):
    o = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-ac', '1', '-ar', '22050',
                        '-f', 'f32le', '-'], capture_output=True)
    x = np.frombuffer(o.stdout, dtype=np.float32)
    return float(20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9))


def main():
    tracks = [
        ('real-edm1.wav', '真实曲目1-EDM Detection Mode'),
        ('real-edm2.wav', '真实曲目2-Electro Cabello'),
        ('real-edm3.wav', '真实曲目3-Rocket Power'),
        ('real-edm4.wav', '真实曲目4-Electrodoodle'),
        ('real-edm5.wav', '真实曲目5-OctoBlues'),
        ('variant-1.wav', '自合成-变体A'),
    ]
    print(f'{"曲目":<34}{"原始RMS":>9}{"增益":>8}')
    for fn, label in tracks:
        p = BGM / fn
        if not p.exists():
            print(f'{label:<34}  缺文件')
            continue
        r = rms_of(p)
        gain = 10 ** ((TARGET_BGM_DB - r) / 20)
        print(f'{label:<34}{r:>9.1f}{gain:>8.2f}')
        out = OUT / f'BGM真实对比-{label.split("-")[0] if False else label}.mp4'
        cmd = [sys.executable, str(MIX), str(PROJ), '--bgm', str(p),
               '--music-gain', f'{gain:.3f}', '--out', str(out)]
        rr = subprocess.run(cmd, cwd=str(PROJ), capture_output=True, text=True,
                            encoding='utf-8', errors='replace')
        print('   ->', 'ok' if rr.returncode == 0 else 'FAIL ' + rr.stderr[-90:])


if __name__ == '__main__':
    main()
