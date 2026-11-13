# -*- coding: utf-8 -*-
"""合成"抖音卡点"风格的电子鼓点 BGM（高能版，默认 150 BPM）。

  python tools/make-edm.py <输出wav> [--bpm 150] [--dur 18] [--at 1.15] [--energy high]

与低能版的区别：
  - 150 BPM（原 128），四拍更密
  - 底鼓更短更硬（sub 更重、click 更强）
  - 反拍贝斯 + 十六分闭镲 + 开镲
  - 每个切点前 0.5s 白噪 riser，切点处 impact
  - 8.3s 与 12.6s 各一段军鼓滚奏（build-up）
  - 整体过 tanh 软削波 + 低频增强（bass boosted 手感）
全部 DSP 向量化，3 秒内出片。
"""
import subprocess
import sys

import numpy as np
from scipy.signal import lfilter

SR = 44100
rng = np.random.default_rng(20261111)


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    return lfilter([1 - a], [1, -a], x)


def highpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    return lfilter([1 - a], [1, -a], x - np.concatenate([[0], x[:-1]]))


def kick(hard=1.0):
    n = int(0.36 * SR)
    t = np.arange(n) / SR
    f = 52 + 210 * np.exp(-t / 0.018)          # 起频更高 → 更"嘣"
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.075)
    sub = np.sin(2 * np.pi * 45 * t) * np.exp(-t / 0.22) * 0.75
    click = rng.standard_normal(n) * np.exp(-t / 0.0018) * 0.75
    return np.tanh((body * 1.2 + sub + click) * hard * 1.9)


def snare():
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    noise = highpass(rng.standard_normal(n), 900) * np.exp(-t / 0.045)
    tone = np.sin(2 * np.pi * 210 * t) * np.exp(-t / 0.035) * 0.55
    return (noise * 0.9 + tone) * 0.62


def hat(open_=False):
    n = int((0.16 if open_ else 0.04) * SR)
    x = highpass(rng.standard_normal(n), 6000)
    return x * np.exp(-np.arange(n) / ((0.045 if open_ else 0.007) * SR)) * 0.42


def clap():
    n = int(0.15 * SR)
    x = np.zeros(n)
    for k, off in enumerate((0.0, 0.009, 0.019, 0.031)):
        s = int(off * SR)
        seg = rng.standard_normal(n - s) * np.exp(-np.arange(n - s) / (0.007 * SR))
        x[s:] += seg * (1.0 if k == 0 else 0.55)
    return highpass(x, 1200) * 0.20


def saw(freqs, n):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f in freqs:
        out += 2 * ((f * t) % 1.0) - 1
    return out / max(1, len(freqs))


def bass_note(freq, dur):
    n = int(dur * SR)
    x = saw([freq, freq * 1.005], n) * 0.9 + np.sin(2 * np.pi * freq * np.arange(n) / SR) * 1.1
    return np.tanh(lowpass(x, 320) * 1.9) * np.exp(-np.arange(n) / (0.10 * SR))


def lead_stab(freqs, dur=0.16):
    n = int(dur * SR)
    x = saw([f * r for f in freqs for r in (0.993, 1.0, 1.008)], n)
    x = np.tanh(lowpass(x, 4200) * 2.0)
    return x * 0.16 * np.exp(-np.arange(n) / (0.040 * SR))


def riser(dur=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 260 * np.exp(t / dur * 2.0)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.14
    noise = highpass(rng.standard_normal(n), 1800) * 0.10
    return (tone + noise) * (np.linspace(0, 1, n) ** 2.2)


def impact(dur=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (40 + 90 * np.exp(-t / 0.012)) * t) * np.exp(-t / 0.13)
    return np.tanh(boom * 2.2) * 0.9


def roll(dur, step=0.055):
    n = int(dur * SR)
    out = np.zeros(n)
    t, base = 0.0, snare()
    while t < dur:
        i = int(t * SR)
        g = 0.30 + 0.70 * (t / dur)
        seg = base[: max(0, n - i)] * g
        out[i:i + len(seg)] += seg
        t += step * (1.0 - 0.5 * (t / dur))
    return out


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    out = a[0]
    bpm = float(a[a.index('--bpm') + 1]) if '--bpm' in a else 150.0
    dur = float(a[a.index('--dur') + 1]) if '--dur' in a else 18.0
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

    # 四拍底鼓
    for k in range(-2, int(dur / beat) + 2):
        t0 = offset + k * beat
        if 0 <= t0 <= dur:
            add(kick(), t0, 1.0)
            kick_at.append(t0)

    # 十六分闭镲 + 反拍开镲
    step = beat / 4
    for k in range(-8, int(dur / step) + 8):
        t0 = offset + k * step
        if t0 < 0.04 or t0 > dur:
            continue
        add(hat(), t0, 0.26 if k % 4 else 0.40)
        if k % 4 == 2:
            add(hat(open_=True), t0, 0.30)

    # 2/4 拍军鼓 + 拍手
    for k in range(0, int(dur / beat) + 2):
        t0 = offset + (k + 1) * beat
        if t0 < 1.0 or t0 > dur:
            continue
        add(snare(), t0, 0.55)
        add(clap(), t0, 0.95)

    # 和声 + 反拍贝斯 + lead
    chords = [(110.00, [220.0, 261.6, 329.6]),
              (87.31, [174.6, 220.0, 261.6]),
              (130.81, [196.0, 261.6, 329.6]),
              (98.00, [196.0, 246.9, 293.7])]
    bar = beat * 4
    idx, b0 = 0, offset
    while b0 < dur:
        root, triad = chords[idx % 4]
        # 反拍贝斯（八分，落在他拍上）
        for s_ in range(8):
            tb = b0 + (s_ + 0.5) * beat / 2
            if 0.6 <= tb <= dur:
                octv = 2 if s_ % 4 == 3 else 1
                add(bass_note(root * octv, beat / 2 * 0.85), tb, 0.75)
        # lead stab（十六分反拍，drop 之后才进）
        if b0 >= 8.0:
            for s_ in range(16):
                tb = b0 + (s_ + 0.5) * beat / 4
                if tb <= dur:
                    add(lead_stab([f * 2 for f in triad]), tb, 0.7)
        idx += 1
        b0 += bar * 2

    # 切点：riser + impact
    for c in (1.15, 4.05, 8.30, 12.60, 16.60):
        if c > dur:
            continue
        if c - 0.5 > 0:
            add(riser(0.5), c - 0.5, 0.55)
        add(impact(), c, 0.85)
    # build-up 滚奏
    add(roll(0.8), max(0, 8.30 - 0.8), 0.7)
    add(roll(0.9), max(0, 12.60 - 0.9), 0.8)

    # 侧链（底鼓压 35%）
    for t0 in kick_at:
        i = int(t0 * SR)
        ln = min(int(0.17 * SR), n - i)
        if ln > 0:
            mix[i:i + ln] *= 1 - 0.35 * np.exp(-np.arange(ln) / (0.045 * SR))

    # bass boost + 软削波
    mix = mix + lowpass(mix.copy(), 110) * 0.65
    mix = np.tanh(mix * 1.7)

    fo, fi = int(0.9 * SR), int(0.06 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo) ** 1.4
    mix[:fi] *= np.linspace(0, 1, fi)
    mix *= 0.95 / max(1e-9, np.abs(mix).max())

    stereo = np.stack([mix, np.roll(mix, 14) * 0.96], axis=1).astype(np.float32)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2',
                    '-i', '-', '-c:a', 'pcm_s16le', out], input=stereo.tobytes(), check=True)
    rms = 20 * np.log10(np.sqrt((mix ** 2).mean()) + 1e-9)
    print(f'saved {out}  {dur:.1f}s  {bpm:.0f} BPM  offset={offset:.3f}s  RMS={rms:.1f} dB')


if __name__ == '__main__':
    main()
