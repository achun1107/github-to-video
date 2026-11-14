# -*- coding: utf-8 -*-
"""BGM v3.1：三总线分离（鼓 / 低频 / 明亮层），按目标频谱配平。

  python tools/make-edm2.py <out.wav> [--bpm 150] [--dur 18] [--at 1.15] [--check]

设计依据（商业电音参考值，以 120–400Hz 为 0 基准）：
  20–60   -4 ~ 0
  60–120  -3 ~ +2
  120–400  0
  400–1.5k -6 ~ -2
  1.5–5k  -9 ~ -4
  5k+     -14 ~ -8
本文件不靠感觉，直接 measure 后按偏差调各总线增益。
"""
import subprocess
import sys

import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
rng = np.random.default_rng(20261115)


def _filt(x, kind, c, order=2):
    if kind == 'lp':
        sos = butter(order, c / (SR / 2), btype='low', output='sos')
    elif kind == 'hp':
        sos = butter(order, c / (SR / 2), btype='high', output='sos')
    else:
        sos = butter(order, [c[0] / (SR / 2), c[1] / (SR / 2)], btype='band', output='sos')
    return sosfilt(sos, x)


# ───────────── 鼓 ─────────────
def kick():
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    f = 58 + 190 * np.exp(-t / 0.020)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.070)
    click = _filt(rng.standard_normal(n) * np.exp(-t / 0.0016), 'bp', (1800, 7000)) * 0.9
    x = _filt(body + click, 'hp', 42)
    return np.tanh(x * 1.5)


def snare():
    n = int(0.15 * SR)
    t = np.arange(n) / SR
    body = _filt(rng.standard_normal(n), 'bp', (900, 5000)) * np.exp(-t / 0.040)
    tone = np.sin(2 * np.pi * 220 * t) * np.exp(-t / 0.030) * 0.45
    return (body + tone) * 0.55


def hat(open_=False):
    n = int((0.14 if open_ else 0.035) * SR)
    x = _filt(rng.standard_normal(n), 'bp', (7000, 16000))
    return x * np.exp(-np.arange(n) / ((0.040 if open_ else 0.006) * SR)) * 0.30


def clap():
    n = int(0.13 * SR)
    x = np.zeros(n)
    for k, off in enumerate((0.0, 0.008, 0.017, 0.028)):
        s = int(off * SR)
        seg = _filt(rng.standard_normal(n - s), 'bp', (1200, 6000)) * np.exp(-np.arange(n - s) / (0.006 * SR))
        x[s:] += seg * (1.0 if k == 0 else 0.5)
    return x * 0.25


def sub_burst(dur=0.30):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 48 + 12 * np.exp(-t / 0.02)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.11)


def impact(dur=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (44 + 80 * np.exp(-t / 0.014)) * t) * np.exp(-t / 0.14)
    body = _filt(rng.standard_normal(n), 'bp', (200, 3000)) * np.exp(-t / 0.05) * 0.35
    return np.tanh((boom + body) * 1.7) * 0.8


def riser(dur=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 300 * np.exp(t / dur * 2.1)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.10
    noise = _filt(rng.standard_normal(n), 'bp', (2500, 9000)) * 0.09
    return (tone + noise) * (np.linspace(0, 1, n) ** 2.0)


def roll(dur, step=0.055):
    n = int(dur * SR)
    out = np.zeros(n)
    t, base = 0.0, snare()
    while t < dur:
        i = int(t * SR)
        g = 0.3 + 0.7 * (t / dur)
        seg = base[: max(0, n - i)] * g
        out[i:i + len(seg)] += seg
        t += step * (1 - 0.5 * (t / dur))
    return out


# ───────────── 有音高 ─────────────
def saw(f, n):
    t = np.arange(n) / SR
    return 2 * ((f * t) % 1.0) - 1


def bass_note(freq, dur):
    n = int(dur * SR)
    x = saw(freq, n) * 0.8 + np.sin(2 * np.pi * freq * np.arange(n) / SR)
    x = _filt(x, 'lp', 300, order=3)
    return np.tanh(x * 1.5) * np.exp(-np.arange(n) / (0.11 * SR)) * 0.9


def pad(freqs, dur, bright=3000):
    """持续 pad：4 个失谐锯齿平均，缓慢起音（不归一化到很小）"""
    n = int(dur * SR)
    if n <= 0:
        return np.zeros(0)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in freqs:
        for dt in (-0.007, -0.002, 0.002, 0.007):
            x += saw(f * (1 + dt), n)
    x /= len(freqs) * 4
    x = _filt(x, 'lp', bright)
    lfo = 1 + 0.06 * np.sin(2 * np.pi * 0.33 * t)
    env = np.minimum(1, np.arange(n) / (0.15 * SR)) * lfo
    return x * env * 1.0


def pluck(freq, dur=0.26):
    n = int(dur * SR)
    raw = saw(freq, n) * 0.7 + np.sign(np.sin(2 * np.pi * freq * 2 * np.arange(n) / SR)) * 0.3
    out = np.zeros(n)
    blk = 512
    for i in range(0, n, blk):
        k = i / n
        cut = min(6500 * np.exp(-k * 5.0) + 800, 16000)
        out[i:i + blk] = _filt(raw[i:i + blk], 'lp', cut)
    return out * np.exp(-np.arange(n) / (0.12 * SR)) * 1.0


def stab(freqs, dur=0.20):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in freqs:
        x += saw(f * 1.003, n) + saw(f * 0.997, n)
    x = _filt(x, 'bp', (500, 7500))
    return x * np.exp(-t / 0.07) * 0.5


def haas(x, ms=11):
    d = int(ms / 1000 * SR)
    return x, np.concatenate([np.zeros(d), x[:-d]]) if d else x


def band_db(x, lo, hi):
    y = _filt(x, 'bp', (lo, min(hi, SR / 2 - 200)), order=3)
    return 20 * np.log10(np.sqrt((y ** 2).mean()) + 1e-9)


def main():
    a = sys.argv
    out = a[1]
    def opt(k, d):
        return float(a[a.index(k) + 1]) if k in a else d
    bpm, dur, at = opt('--bpm', 150.0), opt('--dur', 18.0), opt('--at', 1.15)

    # 预设：让 100 条视频不必共用同一段 BGM
    PRESETS = {
        1: dict(name='A/Am-150', bpm=150, chords=[(220.0, [220.0, 261.6, 329.6]),
                                                  (174.6, [174.6, 220.0, 261.6]),
                                                  (261.6, [261.6, 329.6, 392.0]),
                                                  (196.0, [196.0, 246.9, 293.7])],
                motif=[12, 15, 19, 15, 12, 10, 12, 7], padbright=3000),
        2: dict(name='B/Dm-145-暗', bpm=145, chords=[(293.7, [293.7, 349.2, 440.0]),
                                                    (233.1, [233.1, 293.7, 349.2]),
                                                    (174.6, [174.6, 220.0, 261.6]),
                                                    (196.0, [196.0, 233.1, 293.7])],
                motif=[12, 10, 15, 12, 7, 10, 12, 15], padbright=2000),
        3: dict(name='C/Cm-158-猛', bpm=158, chords=[(261.6, [261.6, 311.1, 392.0]),
                                                    (207.7, [207.7, 261.6, 311.1]),
                                                    (174.6, [174.6, 207.7, 261.6]),
                                                    (233.1, [233.1, 277.2, 349.2])],
                motif=[19, 15, 12, 15, 19, 22, 19, 15], padbright=3800),
        4: dict(name='D/Em-142-柔', bpm=142, chords=[(164.8, [164.8, 196.0, 246.9]),
                                                    (220.0, [220.0, 261.6, 329.6]),
                                                    (130.8, [130.8, 164.8, 196.0]),
                                                    (196.0, [196.0, 246.9, 293.7])],
                motif=[12, 14, 19, 14, 12, 7, 9, 12], padbright=2600),
    }
    preset = int(opt('--preset', 0))
    PR = PRESETS.get(preset)
    if PR:
        bpm = float(PR['bpm'])
    DG, LG, BG, SUB = opt('--dg', 1.5), opt('--lg', 2.6), opt('--bg', 1.2), opt('--sub', 0.7)

    beat = 60.0 / bpm
    offset = at % beat
    n = int(dur * SR)
    drums = np.zeros(n)
    low = np.zeros(n)
    bright_l = np.zeros(n)
    bright_r = np.zeros(n)
    kick_at = []

    def add(buf, sig, t0, g=1.0):
        i = int(round(t0 * SR))
        if i >= n or i < 0 or len(sig) == 0:
            return
        seg = sig[: n - i]
        buf[i:i + len(seg)] += seg * g

    # 鼓
    for k in range(-2, int(dur / beat) + 2):
        t0 = offset + k * beat
        if 0 <= t0 <= dur:
            add(drums, kick(), t0, 1.0)
            kick_at.append(t0)
    step = beat / 4
    for k in range(-8, int(dur / step) + 8):
        t0 = offset + k * step
        if 0.03 <= t0 <= dur:
            add(drums, hat(), t0, 0.16 if k % 4 else 0.26)
            if k % 4 == 2:
                add(drums, hat(True), t0, 0.20)
    for k in range(0, int(dur / beat) + 2):
        t0 = offset + (k + 1) * beat
        if 1.0 <= t0 <= dur:
            add(drums, snare(), t0, 0.5)
            add(drums, clap(), t0, 0.9)

    # 和声/旋律
    chords = PR['chords'] if PR else [(220.0, [220.0, 261.6, 329.6]),
                                      (174.6, [174.6, 220.0, 261.6]),
                                      (261.6, [261.6, 329.6, 392.0]),
                                      (196.0, [196.0, 246.9, 293.7])]
    MOTIF = PR['motif'] if PR else [12, 15, 19, 15, 12, 10, 12, 7]
    PADBRIGHT = PR['padbright'] if PR else 3000
    bar = beat * 4
    idx, b0 = 0, offset
    while b0 < dur:
        root, triad = chords[idx % 4]
        lvl = 0.5 if b0 < 1.15 else (1.0 if b0 < 8.3 else (1.15 if b0 < 12.6 else 1.35))
        if preset == 4:
            lvl *= 0.88          # 柔和版整体收一点

        for s_ in range(8):
            tb = b0 + (s_ + 0.5) * beat / 2
            if 0.5 <= tb <= dur:
                add(low, bass_note(root * (2 if s_ % 4 == 3 else 1), beat / 2 * 0.8), tb, 0.6 * lvl)

        pd = pad(triad, min(bar * 2, dur - b0 + 0.05), bright=PADBRIGHT)
        if len(pd):
            L, R = haas(pd, 13)
            add(bright_l, L, b0, 1.0 * min(lvl, 1.2))
            add(bright_r, R, b0, 1.0 * min(lvl, 1.2))

        if b0 >= 4.0:
            for s_ in range(16):
                tb = b0 + (s_ + 0.5) * beat / 4
                if tb <= dur:
                    st = stab([f * 2 for f in triad])
                    L, R = haas(st, 9)
                    add(bright_l, L, tb, 0.7 * lvl)
                    add(bright_r, R, tb, 0.7 * lvl)

        if b0 >= 8.0:
            for s_ in range(8):
                tb = b0 + s_ * beat / 2
                if tb > dur:
                    break
                f = root * 2 * (2 ** (MOTIF[s_ % len(MOTIF)] / 12))
                p = pluck(f)
                add(bright_l, p, tb, 0.9 * lvl)
                add(bright_r, p, tb + 0.008, 0.8 * lvl)

        idx += 1
        b0 += bar

    # sub 层：跟着底鼓，补 20–60Hz
    sub = np.zeros(n)
    for t0 in kick_at:
        add(sub, sub_burst(), t0, SUB)
    sub = _filt(sub, 'lp', 70, order=3)

    # 卡点
    for c in (1.15, 4.05, 8.30, 12.60, 16.60):
        if c > dur:
            continue
        if c - 0.5 > 0:
            add(drums, riser(0.5), c - 0.5, 0.5)
        add(drums, impact(), c, 0.8)
    add(drums, roll(0.75), max(0, 8.30 - 0.75), 0.65)
    add(drums, roll(0.85), max(0, 12.60 - 0.85), 0.8)

    # 三总线配平（目标：明亮层 400-5k 提到与 120-400 差 <10dB）
    m_l = drums * DG + low * LG + bright_l * BG
    m_r = drums * DG + low * LG + bright_r * BG

    # 侧链（压低频与明亮层）
    sc = np.ones(n)
    for t0 in kick_at:
        i = int(t0 * SR)
        ln = min(int(0.16 * SR), n - i)
        if ln > 0:
            sc[i:i + ln] = np.minimum(sc[i:i + ln], 1 - 0.40 * np.exp(-np.arange(ln) / (0.05 * SR)))
    duck = drums * DG + sub
    m_l = duck + (low * LG + bright_l * BG) * sc
    m_r = duck + (low * LG + bright_r * BG) * sc

    def eq(x):
        x = _filt(x, 'hp', 35)
        return x + _filt(x, 'hp', 4000) * 0.9

    m_l, m_r = eq(m_l), eq(m_r)

    peak = max(np.abs(m_l).max(), np.abs(m_r).max(), 1e-9)
    k = 0.95 / peak
    m_l, m_r = np.tanh(m_l * k), np.tanh(m_r * k)

    fo, fi = int(0.8 * SR), int(0.05 * SR)
    for buf in (m_l, m_r):
        buf[-fo:] *= np.linspace(1, 0, fo) ** 1.3
        buf[:fi] *= np.linspace(0, 1, fi)

    stereo = np.stack([m_l, m_r], axis=1).astype(np.float32)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2',
                    '-i', '-', '-c:a', 'pcm_s16le', out], input=stereo.tobytes(), check=True)

    rms = 20 * np.log10(np.sqrt(((m_l ** 2 + m_r ** 2).mean() / 2)) + 1e-9)
    crest = 20 * np.log10(np.abs(m_l).max() / (np.sqrt((m_l ** 2).mean()) + 1e-9))
    tag = PR['name'] if PR else '默认'
    print(f'saved {out} {dur:.1f}s {bpm:.0f}BPM [{tag}] RMS={rms:.1f}dB 峰值因数={crest:.1f}dB')
    if '--check' in a:
        bands = [(20, 60), (60, 120), (120, 400), (400, 1500), (1500, 5000), (5000, 12000)]
        vals = [band_db(m_l, lo, hi) for lo, hi in bands]
        base = vals[2]
        print('  相对 120–400Hz 的偏差:', [f'{v-base:+.1f}' for v in vals], '(目标 -4/0/0/-4/-6/-11 左右)')


if __name__ == '__main__':
    main()
