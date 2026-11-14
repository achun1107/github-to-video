import subprocess
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

SR = 22050
PROJ = Path(r'D:\DSH\achun\video-batch\gathin23-cleanyourtv')
MIX = Path(r'D:\DSH\achun\video-goofish\tools\mix-batch.py')
OUT = Path(r'D:\DSH\achun\_tmp')


def load(f):
    p = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(f), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                       capture_output=True)
    return np.frombuffer(p.stdout, dtype=np.float32)


def band(x, lo, hi):
    sos = butter(3, [lo / (SR / 2), min(hi, SR / 2 - 100) / (SR / 2)], btype='band', output='sos')
    y = sosfilt(sos, x)
    return float(20 * np.log10(np.sqrt((y ** 2).mean()) + 1e-9))


def rms(x):
    return float(20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9))


OUT.mkdir(exist_ok=True)
voice_only = OUT / 'voice_only.mp4'

# 关掉音乐 = 只留人声
subprocess.run(['python', str(MIX), str(PROJ), '--music-gain', '0.0', '--out', str(voice_only)],
               check=True, capture_output=True, cwd=str(PROJ))

v = load(voice_only)
new = load(PROJ / 'renders/final.mp4')
n = min(len(v), len(new))
bgm_new = new[:n] - v[:n]          # 新版 BGM 在混音里的实际成分

old_path = OUT / 'old_final.mp4'
if old_path.exists():
    old = load(old_path)
    n2 = min(len(v), len(old))
    bgm_old = old[:n2] - v[:n2]
else:
    bgm_old = None

bands = [('20-60', 20, 60), ('60-120', 60, 120), ('120-400', 120, 400),
         ('400-1.5k', 400, 1500), ('1.5-5k', 1500, 5000), ('5k+', 5000, 11000)]

print('人声电平        :', round(rms(v), 1), 'dB')
print('新版 BGM 电平   :', round(rms(bgm_new), 1), 'dB  → 比人声低', round(rms(v) - rms(bgm_new), 1), 'dB')
if bgm_old is not None:
    print('旧版 BGM 电平   :', round(rms(bgm_old), 1), 'dB  → 比人声低', round(rms(v) - rms(bgm_old), 1), 'dB')
print()
print(f'{"频段":<10}{"新BGM":>9}{"旧BGM":>9}{"变化":>9}')
base_new = band(bgm_new, 120, 400)
base_old = band(bgm_old, 120, 400) if bgm_old is not None else None
for name, lo, hi in bands:
    nb = band(bgm_new, lo, hi) - base_new
    if bgm_old is not None:
        ob = band(bgm_old, lo, hi) - base_old
        print(f'{name:<10}{nb:>+9.1f}{ob:>+9.1f}{nb-ob:>+9.1f}')
    else:
        print(f'{name:<10}{nb:>+9.1f}')
