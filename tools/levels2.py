# -*- coding: utf-8 -*-
"""精确测量：只看人声频段的能量，避免被鼓点低频淹没。

  python tools/levels2.py
"""
import subprocess

import numpy as np
from scipy.signal import butter, sosfiltfilt


def load(f, a, b, sr=16000):
    p = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(a), '-to', str(b), '-i', f,
                        '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'],
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32), sr


def band_db(x, sr, lo, hi):
    sos = butter(4, [lo, hi], btype='band', fs=sr, output='sos')
    y = sosfiltfilt(sos, x)
    return round(float(20 * np.log10(np.sqrt((y ** 2).mean()) + 1e-9)), 1)


f = 'renders/final.mp4'
# 人声主频约 100–4000Hz；鼓点低频 <120Hz、镲 >5kHz
for label, a, b in [('纯音乐 0.0–0.55', 0.0, 0.55), ('纯音乐 18.5–19.5', 18.5, 19.5),
                    ('人声 2.4–4.0', 2.4, 4.0), ('人声 23.0–24.5', 23.0, 24.5),
                    ('人声 29.5–31.0', 29.5, 31.0)]:
    x, sr = load(f, a, b)
    if not len(x):
        print(f'{label}: 空')
        continue
    print(f'{label:20s} 全频 {band_db(x, sr, 20, 7000):>6.1f} dB | '
          f'人声带(120–4000) {band_db(x, sr, 120, 4000):>6.1f} dB | '
          f'低频(<120) {band_db(x, sr, 20, 120):>6.1f} dB')
