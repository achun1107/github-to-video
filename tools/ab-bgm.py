# -*- coding: utf-8 -*-
"""A/B 对比两条 BGM：频段、峰值因数、动态、以及老版基线。

  python tools/ab-bgm.py old.wav new.wav
"""
import subprocess
import sys

import numpy as np
from scipy.signal import butter, sosfilt

SR = 22050


def load(p):
    o = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(SR),
                        '-f', 'f32le', '-'], capture_output=True, check=True)
    return np.frombuffer(o.stdout, dtype=np.float32)


def band(x, lo, hi):
    sos = butter(3, [lo / (SR / 2), min(hi, SR / 2 - 100) / (SR / 2)], btype='band', output='sos')
    y = sosfilt(sos, x)
    return 20 * np.log10(np.sqrt((y ** 2).mean()) + 1e-9)


def report(name, x):
    rms = 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9)
    peak = 20 * np.log10(np.abs(x).max() + 1e-9)
    crest = peak - rms
    bands = [band(x, lo, hi) for lo, hi in [(20, 60), (60, 120), (120, 400), (400, 1500), (1500, 5000), (5000, 11000)]]
    base = bands[2]
    rel = [b - base for b in bands]
    print(f'{name}')
    print(f'  峰值因数 : {crest:5.1f} dB   （越低越"厚"，越高越"尖"）')
    print(f'  频段偏差 : ' + '  '.join(f'{v:+.1f}' for v in rel))
    print(f'             20-60  60-120  120-400  400-1.5k  1.5-5k  5k+')
    return rel, crest


def main():
    a = sys.argv
    old, new = a[1], a[2]
    xo, xn = load(old), load(new)
    ro, co = report('旧版 ' + old.split('/')[-1].split('\\')[-1], xo)
    rn, cn = report('新版 ' + new.split('/')[-1].split('\\')[-1], xn)
    print()
    print('改善量（新 - 旧，正值=新版更亮/更少尖）:')
    labels = ['20-60', '60-120', '120-400', '400-1.5k', '1.5-5k', '5k+']
    for lb, o, n in zip(labels, ro, rn):
        print(f'  {lb:<8} {n-o:+6.1f} dB')
    print(f'  峰值因数 {co-cn:+6.1f} dB')


if __name__ == '__main__':
    main()
