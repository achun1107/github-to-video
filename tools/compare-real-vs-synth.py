# -*- coding: utf-8 -*-
"""对比：真实录音 vs 自合成，看差距在哪。

  python tools/compare-real-vs-synth.py
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 22050


def load(p, sec=None):
    cmd = ['ffmpeg', '-v', 'error', '-i', str(p)]
    if sec:
        cmd += ['-t', str(sec)]
    cmd += ['-ac', '1', '-ar', str(SR), '-f', 'f32le', '-']
    o = subprocess.run(cmd, capture_output=True)
    return np.frombuffer(o.stdout, dtype=np.float32)


def band_db(x, lo, hi):
    S = np.abs(np.fft.rfft(x))
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = (f >= lo) & (f < hi)
    return 20 * np.log10(np.sqrt((S[m] ** 2).mean()) + 1e-9)


def metrics(x):
    rms = 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9)
    peak = 20 * np.log10(np.abs(x).max() + 1e-9)
    # 频谱平坦度：越高越"噪声化"，真实录音通常更丰富
    S = np.abs(np.fft.rfft(x)) + 1e-9
    flat = float(np.exp(np.mean(np.log(S))) / np.mean(S))
    bands = [(20, 60), (60, 120), (120, 400), (400, 1500), (1500, 5000), (5000, 11000)]
    b = [band_db(x, lo, hi) for lo, hi in bands]
    rel = [v - b[2] for v in b]
    # 音高类分布（是否有清晰和声）
    win, hop = 8192, 4096
    prof = np.zeros(12)
    for i in range(0, max(1, (len(x) - win) // hop)):
        seg = x[i * hop:i * hop + win] * np.hanning(win)
        S2 = np.abs(np.fft.rfft(seg))
        f2 = np.fft.rfftfreq(win, 1 / SR)
        m = (f2 > 60) & (f2 < 1200)
        pc = (np.round(12 * np.log2(f2[m] / 440.0 + 1e-9)) % 12).astype(int)
        for k in range(12):
            prof[k] += S2[m][pc == k].sum()
    prof /= prof.sum() + 1e-9
    return dict(rms=rms, crest=peak - rms, flat=flat, rel=rel, chroma_std=float(prof.std() / prof.mean()))


def main():
    synth = Path(r'D:\DSH\achun\video-goofish\audio\bgm\variant-1.wav')
    reals = [
        Path(r'D:\DSH\achun\_tmp\EDM Detection Mode.mp3'),
        Path(r'D:\DSH\achun\_tmp\Electro Cabello.mp3'),
        Path(r'D:\DSH\achun\_tmp\Rocket Power.mp3'),
    ]
    rows = [('自合成 v1', metrics(load(synth)))]
    for p in reals:
        if p.exists():
            rows.append((p.stem[:22], metrics(load(p, 20))))

    print(f'{"来源":<24}{"峰值因数":>9}{"频谱平坦":>9}{"和声集中":>9}')
    for name, m in rows:
        print(f'{name:<24}{m["crest"]:>9.1f}{m["flat"]:>9.3f}{m["chroma_std"]:>9.2f}')

    print()
    print('频段偏差（相对 120–400Hz）:')
    labels = ['20-60', '60-120', '120-400', '400-1.5k', '1.5-5k', '5k+']
    print(f'{"来源":<24}' + ''.join(f'{l:>9}' for l in labels))
    for name, m in rows:
        print(f'{name:<24}' + ''.join(f'{v:>+9.1f}' for v in m['rel']))


if __name__ == '__main__':
    main()
