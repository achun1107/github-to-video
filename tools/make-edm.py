# -*- coding: utf-8 -*-
"""合成"抖音卡点"风格的电子鼓点 BGM（128 BPM，bass boosted）。

  python tools/make-edm.py <输出wav> [--bpm 128] [--dur 34.8] [--at 1.15]

与片子的 9 个切点对齐：切点前 0.45s riser、切点处 impact；
11.55s 与 21.10s（drop）各有一段军鼓滚奏。
全部 DSP 都用 scipy/向量化实现，4 秒内出片。
"""
import subprocess
import sys

import numpy as np
from scipy.signal import lfilter, fftconvolve

SR = 44100
rng = np.random.default_rng(20261110)
CUTS = [1.15, 2.60, 6.10, 11.55, 14.20, 17.12, 21.10, 25.70, 29.00]
DROP = 21.10


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    return lfilter([1 - a], [1, -a], x)


def highpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    return lfilter([1 - a], [1, -a], x - np.concatenate([[0], x[:-1]]))


def kick():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    f = 44 + 150 * np.exp(-t / 0.026)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)
    sub = np.sin(2 * np.pi * 42 * t) * np.exp(-t / 0.28) * 0.5
    click = rng.standard_normal(n) * np.exp(-t / 0.0025) * 0.45
    return np.tanh((body + sub + click) * 1.7)


def snare():
    n = int(0.2 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n) * np.exp(-t / 0.05)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.045) * 0.5
    return (noise * 0.7 + tone) * 0.5


def hat(open_=False):
    n = int((0.2 if open_ else 0.045) * SR)
    x = rng.standard_normal(n)
    x = np.diff(x, prepend=0.0)
    return x * np.exp(-np.arange(n) / ((0.05 if open_ else 0.008) * SR)) * 0.32


def clap():
    n = int(0.16 * SR)
    x = np.zeros(n)
    for k, off in enumerate((0.0, 0.010, 0.020, 0.034)):
        s = int(off * SR)
        seg = rng.standard_normal(n - s) * np.exp(-np.arange(n - s) / (0.008 * SR))
        x[s:] += seg * (1.0 if k == 0 else 0.5)
    return np.diff(x, prepend=0.0) * 0.14


def saw(freqs, n):
    """多音同时生成（freqs 是数组），返回叠加的锯齿波"""
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f in freqs:
        out += 2 * ((f * t) % 1.0) - 1
    return out / max(1, len(freqs))


def bass_note(freq, dur):
    n = int(dur * SR)
    x = saw([freq], n) * 0.8 + np.sin(2 * np.pi * freq * np.arange(n) / SR) * 0.9
    return np.tanh(lowpass(x, 260) * 1.5) * np.exp(-np.arange(n) / (0.15 * SR))


def lead_stab(freqs, dur=0.18):
    n = int(dur * SR)
    x = saw(freqs + [-f * 0.006 for f in freqs] + [f * 0.007 for f in freqs], n)
    return lowpass(x, 3200) * 0.11 * np.exp(-np.arange(n) / (0.05 * SR))


def riser(dur=0.45):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 320 * np.exp(t / dur * 1.7)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.11
    noise = np.diff(rng.standard_normal(n), prepend=0.0) * 0.05
    return (tone + noise) * (np.linspace(0, 1, n) ** 2)


def impact(dur=0.55):
    n = int(dur * SR)
    t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (36 + 70 * np.exp(-t / 0.018)) * t) * np.exp(-t / 0.17)
    return np.tanh(boom * 1.7) * 0.8


def roll(dur, step=0.062):
    n = int(dur * SR)
    out = np.zeros(n)
    t = 0.0
    base = snare()
    while t < dur:
        i = int(t * SR)
        g = 0.35 + 0.65 * (t / dur)
        seg = base[: max(0, n - i)] * g
        out[i:i + len(seg)] += seg
        t += step * (1.0 - 0.45 * (t / dur))
    return out


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    out = a[0]
    bpm = float(a[a.index('--bpm') + 1]) if '--bpm' in a else 128.0
    dur = float(a[a.index('--dur') + 1]) if '--dur' in a else 34.8
    at = float(a[a.index('--at') + 1]) if '--at' in a else 1.15

    beat = 60.0 / bpm
    offset = at % beat
    n = int(dur * SR)
    mix = np.zeros(n)
    kick_at = []

    def add(sig, t0, gain=1.0):
        i = int(round(t0 * SR))
        if i >= n or i < 0:
            return
        seg = sig[: n - i]
        mix[i:i + len(seg)] += seg * gain

    # 底鼓：四拍到底
    for k in range(-2, int(dur / beat) + 2):
        t0 = offset + k * beat
        if 0 <= t0 <= dur:
            add(kick(), t0, 1.0)
            kick_at.append(t0)

    # 十六分闭镲
    step = beat / 4
    for k in range(-8, int(dur / step) + 8):
        t0 = offset + k * step
        if t0 < 0.05 or t0 > dur:
            continue
        add(hat(), t0, 0.20 if k % 4 else 0.34)
        if k % 8 == 6:
            add(hat(open_=True), t0 + step * 0.5, 0.28)

    # 拍手 + 军鼓（2/4 拍）
    for k in range(0, int(dur / beat) + 2):
        t0 = offset + (k + 1) * beat
        if t0 < 1.9 or t0 > dur:
            continue
        add(clap(), t0, 0.9)
        add(snare(), t0, 0.42)

    # 和声 + 贝斯
    chords = [(110.00, [220.0, 261.6, 329.6]),
              (87.31, [174.6, 220.0, 261.6]),
              (130.81, [196.0, 261.6, 329.6]),
              (98.00, [196.0, 246.9, 293.7])]
    bar = beat * 4
    idx = 0
    b0 = offset
    while b0 < dur:
        root, triad = chords[idx % 4]
        pn = int(bar * 2 * SR)
        pad = lowpass(saw([f * d for f in triad for d in (0.994, 1.0, 1.007)], pn), 1600) * 0.10
        pad *= np.minimum(1, np.arange(pn) / (0.02 * SR))
        add(pad, b0, 1.0)
        sub = 4 if b0 >= DROP - 1 else 2
        for s_ in range(int(8 * sub)):
            tb = b0 + s_ * beat / sub
            if tb > dur or tb < 1.4:
                continue
            octv = 2 if s_ % 4 == 3 else 1
            add(bass_note(root * octv, beat / sub * 0.9), tb, 0.6)
        if b0 >= DROP - 1:
            for s_ in range(8):
                tb = b0 + (s_ + 0.5) * beat
                if tb <= dur:
                    add(lead_stab([f * 2 for f in triad]), tb, 0.85)
        idx += 1
        b0 += bar * 2

    # 切点：riser + impact；两段滚奏
    add(impact(0.8), 0.0, 0.95)
    for c in CUTS:
        if c - 0.45 > 0:
            add(riser(0.45), c - 0.45, 0.6)
        add(impact(), c, 0.9)
    add(roll(0.9), 11.55 - 0.9, 0.75)
    add(roll(1.2), DROP - 1.2, 0.85)

    # 侧链（底鼓位置压 30%）
    for t0 in kick_at:
        i = int(t0 * SR)
        ln = min(int(0.2 * SR), n - i)
        if ln > 0:
            mix[i:i + ln] *= 1 - 0.30 * np.exp(-np.arange(ln) / (0.05 * SR))

    # 低频增强 + 软削波
    mix = mix + lowpass(mix.copy(), 120) * 0.55
    mix = np.tanh(mix * 1.35)

    fo, fi = int(1.3 * SR), int(0.2 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo) ** 1.5
    mix[:fi] *= np.linspace(0, 1, fi)
    mix *= 0.93 / max(1e-9, np.abs(mix).max())

    stereo = np.stack([mix, np.roll(mix, 18) * 0.97], axis=1).astype(np.float32)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2',
                    '-i', '-', '-c:a', 'pcm_s16le', out], input=stereo.tobytes(), check=True)
    print(f'saved {out}  {dur:.2f}s  {bpm:.0f} BPM  offset={offset:.3f}s  drop={DROP}s')


if __name__ == '__main__':
    main()
