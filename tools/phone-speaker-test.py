# -*- coding: utf-8 -*-
"""手机外放模拟对比：抖音 80% 的播放发生在手机扬声器上，
而手机扬声器 500Hz 以下衰减严重。所以"频谱对不对"不如"手机外放好不好听"。

  python tools/phone-speaker-test.py

做法：
  1. 用 HP 500Hz + 削掉 12kHz 以上模拟手机扬声器
  2. 统一响度到 -14 LUFS（抖音的实际播放响度）
  3. 测三件事：可听响度、中频厚度、瞬态清晰度
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
BGM = Path(r'D:\DSH\achun\video-goofish\audio\bgm')


def load(p, sec=None):
    cmd = ['ffmpeg', '-v', 'error', '-i', str(p)]
    if sec:
        cmd += ['-t', str(sec)]
    cmd += ['-ac', '1', '-ar', str(SR), '-f', 'f32le', '-']
    o = subprocess.run(cmd, capture_output=True)
    return np.frombuffer(o.stdout, dtype=np.float32)


def phone_sim(x):
    """手机扬声器近似：500Hz 高通（2 阶）+ 12kHz 低通"""
    sos = butter(2, 500 / (SR / 2), btype='high', output='sos')
    y = sosfilt(sos, x)
    sos2 = butter(2, 12000 / (SR / 2), btype='low', output='sos')
    return sosfilt(sos2, y)


def norm_lufs(x, target=-14.0):
    rms = np.sqrt((x ** 2).mean()) + 1e-9
    cur = 20 * np.log10(rms)
    return x * 10 ** ((target - cur) / 20)


def band(x, lo, hi):
    sos = butter(3, [lo / (SR / 2), min(hi, SR / 2 - 200) / (SR / 2)], btype='band', output='sos')
    y = sosfilt(sos, x)
    return 20 * np.log10(np.sqrt((y ** 2).mean()) + 1e-9)


def transient_clarity(x):
    """瞬态清晰度：300–3k 的峰值因数，越高越"脆"越好听"""
    sos = butter(3, [300 / (SR / 2), 3000 / (SR / 2)], btype='band', output='sos')
    y = sosfilt(sos, x)
    rms = np.sqrt((y ** 2).mean()) + 1e-9
    return float(20 * np.log10(np.abs(y).max() / rms))


def main():
    targets = [
        ('variant-1.wav', '合成-A'), ('variant-2.wav', '合成-B'),
        ('variant-3.wav', '合成-C'), ('variant-4.wav', '合成-D'),
        ('real-edm1.wav', '真实-EDM Detection'), ('real-edm2.wav', '真实-Electro Cabello'),
        ('real-edm3.wav', '真实-Rocket Power'), ('real-edm4.wav', '真实-Electrodoodle'),
        ('real-edm5.wav', '真实-OctoBlues'),
    ]
    print(f'{"音源":<24}{"手机可听储能":>12}{"中频厚度":>10}{"瞬态清晰":>10}{"总评":>8}')
    rows = []
    for fn, label in targets:
        p = BGM / fn
        if not p.exists():
            continue
        x = load(p)
        y = norm_lufs(phone_sim(x))
        audible = 20 * np.log10(np.sqrt((y ** 2).mean()) + 1e-9)   # 归一后应接近 -14
        body = band(y, 500, 1500)
        crisp = transient_clarity(y)
        # 总评：中频厚度 + 瞬态清晰度（都是事后手机外放的关键）
        score = body + crisp * 0.5
        rows.append((label, audible, body, crisp, score))
        print(f'{label:<24}{audible:>12.1f}{body:>10.1f}{crisp:>10.1f}{score:>8.1f}')

    print()
    rows.sort(key=lambda r: -r[4])
    print('手机外放排序（分数越高越好听）:')
    for i, r in enumerate(rows, 1):
        print(f'  {i}. {r[0]:<24} {r[4]:.1f}')


if __name__ == '__main__':
    main()
