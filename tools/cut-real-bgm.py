# -*- coding: utf-8 -*-
"""从真实曲目里切出 18 秒最佳片段，并估算 BPM 做切点对齐。

  python tools/cut-real-bgm.py <source.mp3> <out.wav> [--dur 18] [--at 1.15]

选段策略：按 1 秒能量滑窗，找「能量最高且波动最大」的 18 秒（通常是有 drop 的副歌）。
对齐策略：估算 BPM → 拍长 → 让第一个强拍落在 at 时刻。
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 44100


def decode(p):
    o = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-ac', '2', '-ar', str(SR),
                        '-f', 'f32le', '-'], capture_output=True, check=True)
    x = np.frombuffer(o.stdout, dtype=np.float32).reshape(-1, 2)
    return x


def onset_env(x, sr=SR, hop=512):
    m = x.mean(axis=1)
    n = len(m) // hop
    env = np.array([np.abs(m[i * hop:(i + 1) * hop]).mean() for i in range(n)])
    d = np.diff(env, prepend=env[0])
    return np.maximum(d, 0)


def estimate_bpm(env, sr=SR, hop=512):
    fps = sr / hop
    e = env - env.mean()
    ac = np.correlate(e, e, 'full')[len(e) - 1:]
    lo, hi = int(fps * 60 / 180), int(fps * 60 / 70)     # 70–180 BPM
    if hi <= lo:
        return 120.0
    seg = ac[lo:hi]
    lag = lo + int(np.argmax(seg))
    return 60.0 * fps / lag


def pick_window(x, dur, sr=SR):
    """滑窗找能量最高的 dur 秒"""
    m = x.mean(axis=1)
    win = int(dur * sr)
    if len(m) <= win:
        return 0
    step = sr // 2
    best, best_score = 0, -1e9
    for start in range(0, len(m) - win, step):
        seg = m[start:start + win]
        rms = np.sqrt((seg ** 2).mean())
        # 偏好有起伏的段落（副歌），惩罚过平的
        crest = np.abs(seg).max() / (rms + 1e-9)
        score = rms * (1 + 0.15 * min(crest, 8))
        if score > best_score:
            best_score, best = score, start
    return best


def main():
    a = sys.argv
    src, out = Path(a[1]), Path(a[2])
    dur = float(a[a.index('--dur') + 1]) if '--dur' in a else 18.0
    at = float(a[a.index('--at') + 1]) if '--at' in a else 1.15

    x = decode(src)
    start = pick_window(x, dur)
    seg = x[start:start + int(dur * SR)]

    bpm = estimate_bpm(onset_env(seg))
    beat = 60.0 / bpm
    # 找到段内第一个强拍，对齐到 at
    env = onset_env(seg)
    fps = SR / 512
    first = None
    thr = env.mean() + env.std()
    for i, v in enumerate(env):
        if v > thr:
            first = i / fps
            break
    first = first or 0.0
    # 目标：把强拍移到 at 的整拍位置
    shift = (at % beat) - (first % beat)
    n_shift = int(shift * SR)
    # 关键：不要用补零实现偏移，否则首尾会整段静音（实测 head/tail = -180dB）。
    # 改为把切点整体前移/后移，保证 18 秒内全是声音。
    win = int(dur * SR)
    new_start = start - n_shift
    if new_start < 0:
        new_start = 0
    if new_start + win > len(x):
        new_start = max(0, len(x) - win)
    seg = x[new_start:new_start + win]
    if len(seg) < win:
        seg = np.concatenate([seg, np.repeat(seg[-1:], win - len(seg), axis=0)])
    start = new_start

    # 归一 + 首尾淡入淡出
    peak = np.abs(seg).max()
    if peak > 0:
        seg = seg / peak * 0.92
    fi, fo = int(0.03 * SR), int(0.6 * SR)
    seg[:fi] *= np.linspace(0, 1, fi)[:, None]
    seg[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5

    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2',
                    '-i', '-', '-c:a', 'pcm_s16le', str(out)],
                   input=seg.astype(np.float32).tobytes(), check=True)
    print(f'{src.name} → {out.name}')
    print(f'  切点 {start/SR:.1f}s  估算 {bpm:.0f} BPM  拍长 {beat*1000:.0f}ms  对齐偏移 {shift*1000:+.0f}ms')


if __name__ == '__main__':
    main()
