# -*- coding: utf-8 -*-
"""分析曲库：BPM、律动强度（onset 密度）、响度、时长。

  python tools/analyze-music.py <目录>
"""
import subprocess
import sys
from pathlib import Path

import numpy as np


def load(path, sr=22050):
    p = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(sr),
                        '-f', 'f32le', '-'], capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32), sr


def analyze(path):
    x, sr = load(path)
    dur = len(x) / sr
    # 帧能量（20ms hop）
    hop = int(sr * 0.02)
    n = len(x) // hop
    frames = x[: n * hop].reshape(n, hop)
    rms = np.sqrt((frames ** 2).mean(axis=1))
    # 频谱通量（用短时 FFT 的帧差分近似 onset）
    win = 1024
    m = (len(x) - win) // hop
    S = np.abs(np.fft.rfft(np.lib.stride_tricks.sliding_window_view(x, win)[:m], axis=1))
    flux = np.maximum(0, np.diff(S, axis=0)).mean(axis=1)
    flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    # onset 密度：超过阈值的帧比例
    onset_rate = float((flux > 1.2).mean())
    # BPM：对 flux 自相关找 0.3-1.2s 周期
    f = flux - flux.mean()
    ac = np.correlate(f, f, mode='full')[len(f) - 1:]
    ac /= (ac[0] + 1e-9)
    fps = sr / hop
    lo, hi = int(0.3 * fps), int(1.2 * fps)
    lag = lo + int(np.argmax(ac[lo:hi]))
    bpm = 60.0 * fps / lag
    # 低频能量占比（鼓感）
    low = np.abs(np.fft.rfft(x)).mean()
    rms_db = 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9)
    return {
        'name': Path(path).name, 'dur': round(dur, 2), 'bpm': round(bpm, 1),
        'ac': round(float(ac[lag]), 2), 'onset_rate': round(onset_rate, 3),
        'rms_db': round(float(rms_db), 1), 'flux_std': round(float(flux.std()), 3),
    }


if __name__ == '__main__':
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
    rows = []
    for p in sorted(root.rglob('*.mp3')) + sorted(root.rglob('*.wav')):
        if p.name.startswith('vo') or p.name == 'score.wav':
            continue
        try:
            rows.append(analyze(p))
        except Exception as e:
            print('skip', p.name, e)
    rows.sort(key=lambda r: -r['onset_rate'])
    print(f"{'曲目':<32}{'时长':>7}{'BPM':>7}{'自相关':>8}{'律动密度':>10}{'RMS dB':>9}")
    for r in rows:
        print(f"{r['name']:<32}{r['dur']:>7.1f}{r['bpm']:>7.1f}{r['ac']:>8.2f}{r['onset_rate']:>10.3f}{r['rms_db']:>9.1f}")
