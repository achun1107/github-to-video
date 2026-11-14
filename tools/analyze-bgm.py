# -*- coding: utf-8 -*-
"""诊断 BGM：和声变化、旋律存在度、频段平衡、重复度。

  python tools/analyze-bgm.py <wav>
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt


def load(p, sr=22050):
    o = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-ac', '1', '-ar', str(sr),
                        '-f', 'f32le', '-'], capture_output=True, check=True)
    return np.frombuffer(o.stdout, dtype=np.float32), sr


def band_db(x, sr, lo, hi):
    sos = butter(4, [lo, min(hi, sr / 2 - 100)], btype='band', fs=sr, output='sos')
    y = sosfiltfilt(sos, x)
    return round(20 * np.log10(np.sqrt((y ** 2).mean()) + 1e-9), 1)


def chroma_profile(x, sr, win=8192, hop=4096):
    """粗略音高类分布（12 半音），用来看有没有稳定的和声/旋律"""
    n = (len(x) - win) // hop
    prof = np.zeros(12)
    for i in range(n):
        seg = x[i * hop: i * hop + win] * np.hanning(win)
        S = np.abs(np.fft.rfft(seg))
        freqs = np.fft.rfftfreq(win, 1 / sr)
        m = (freqs > 60) & (freqs < 1200)
        f, s = freqs[m], S[m]
        pc = (np.round(12 * np.log2(f / 440.0 + 1e-9)) % 12).astype(int)
        for k in range(12):
            prof[k] += s[pc == k].sum()
    prof /= prof.sum() + 1e-9
    return prof


def repetition(x, sr, seg=1.0):
    """相邻 1 秒片段的相似度，衡量编曲是否在推进"""
    n = int(seg * sr)
    chunks = [x[i * n:(i + 1) * n] for i in range(len(x) // n)]
    sims = []
    for a, b in zip(chunks, chunks[1:]):
        va, vb = a / (np.linalg.norm(a) + 1e-9), b / (np.linalg.norm(b) + 1e-9)
        sims.append(float(np.dot(va, vb)))
    return [round(s, 2) for s in sims]


def main():
    p = Path(sys.argv[1])
    x, sr = load(p)
    print(f'文件: {p.name}  时长 {len(x)/sr:.2f}s')
    print()
    print('频段能量（dB）:')
    for name, lo, hi in [('超低 20-60', 20, 60), ('低音 60-120', 60, 120), ('低中 120-400', 120, 400),
                         ('中 400-1.5k', 400, 1500), ('中高 1.5-5k', 1500, 5000), ('高 5k+', 5000, 10000)]:
        print(f'  {name:<14} {band_db(x, sr, lo, hi):>7.1f}')
    print()
    prof = chroma_profile(x, sr)
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    top = np.argsort(prof)[::-1][:5]
    print('音高类 Top5（看和声是否集中）:', ', '.join(f'{names[i]} {prof[i]*100:.0f}%' for i in top))
    print(f'  分布均匀度（越低越集中=越有调性）: {prof.std()/prof.mean():.2f}')
    print()
    sims = repetition(x, sr)
    print('相邻秒相似度（越高越像在原地重复）:')
    print(' ', sims)
    print(f'  平均 {np.mean(sims):.2f}')


if __name__ == '__main__':
    main()
