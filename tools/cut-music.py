# -*- coding: utf-8 -*-
"""把配乐裁成「每一拍落在切点上」并循环铺满全片。

  python tools/cut-music.py <输入> <输出> [--at 1.15] [--dur 34.8]

做三件事：
 1. 用 onset 包络的自相关估拍速（先按 60–180 BPM 搜，再取二倍/一半里更强的那个）；
 2. 扫相位：让第一拍正好落在 --at（默认第一个切点 1.15s）；
 3. 不够长就首尾交叠循环，最后整体淡入淡出。
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 44100


def load(path, sr=SR):
    p = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '2', '-ar', str(sr),
                        '-f', 'f32le', '-'], capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32).reshape(-1, 2)


def onset_env(mono, hop=512, win=1024):
    n = (len(mono) - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    frames = mono[idx] * np.hanning(win)[None, :]
    S = np.abs(np.fft.rfft(frames, axis=1))
    flux = np.maximum(0, np.diff(S, axis=0)).mean(axis=1)
    return flux, SR / hop


def tempo(flux, fps):
    f = flux - flux.mean()
    ac = np.correlate(f, f, mode='full')[len(f) - 1:]
    ac /= (ac[0] + 1e-9)
    lo, hi = int(fps * 60 / 180), int(fps * 60 / 60)   # 180..60 BPM
    lag = lo + int(np.argmax(ac[lo:hi]))
    bpm = 60.0 * fps / lag
    # 二倍速更常见：如果 2*bpm 在 90–180 且自相关不弱，就用它
    lag2 = max(1, lag // 2)
    if 90 <= bpm * 2 <= 180 and ac[lag2] > 0.35:
        bpm, lag = bpm * 2, lag2
    return bpm, lag / fps, float(ac[lag])


def tile(y, dur_s, xfade=0.02):
    need = int(round(dur_s * SR))
    if len(y) >= need:
        return y[:need]
    fade = int(xfade * SR)
    out = y.copy()
    while len(out) < need:
        seg = y.copy()
        if fade and len(out) >= fade:
            w = np.linspace(0, 1, fade)[:, None]
            out[-fade:] = out[-fade:] * (1 - w) + seg[:fade] * w
            out = np.concatenate([out, seg[fade:]])
        else:
            out = np.concatenate([out, seg])
    return out[:need]


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    src, dst = Path(a[0]), Path(a[1])
    at = float(a[a.index('--at') + 1]) if '--at' in a else 1.15
    dur = float(a[a.index('--dur') + 1]) if '--dur' in a else 34.8

    x = load(src)
    mono = x.mean(axis=1)
    flux, fps = onset_env(mono)
    bpm, period, ac = tempo(flux, fps)
    print(f'{src.name}: {bpm:.1f} BPM（周期 {period:.3f}s，自相关 {ac:.2f}）')

    # 扫相位：取 onset 强度最高的那一段作为第一拍基准
    n = len(flux)
    k = max(1, int(period * fps))
    score = np.convolve(flux, np.ones(k), mode='same')
    b0 = int(np.argmax(score)) / fps
    # 让第一拍落在 at：往前推整数拍
    steps = int(np.ceil((b0 - at) / period)) if b0 > at else -int(np.ceil((at - b0) / period))
    start = b0 - at - steps * period
    while start < 0:
        start += period
    while start >= period:
        start -= period
    print(f'  第一拍 {b0:.3f}s → 从 {start:.3f}s 处开始播，使拍点落在 {at:.2f}s 附近')

    y = x[int(round(start * SR)):]
    if start > 0.01:
        # 前面补上曲尾的一段，循环无缝
        pad = int(round(start * SR))
        tail = x[-pad:] if pad <= len(x) else np.zeros((pad, 2), dtype=np.float32)
        y = np.concatenate([tail, y])
    y = tile(y, dur)
    fi, fo = int(0.30 * SR), int(1.6 * SR)
    y[:fi] *= np.linspace(0, 1, fi)[:, None]
    y[-fo:] *= np.linspace(1, 0, fo)[:, None]
    peak = np.abs(y).max()
    if peak > 0.98:
        y *= 0.98 / peak

    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2',
                    '-i', '-', '-c:a', 'pcm_s16le', str(dst)],
                   input=y.astype(np.float32).tobytes(), check=True)
    print(f'  saved {dst}  {len(y) / SR:.2f}s')


if __name__ == '__main__':
    main()
