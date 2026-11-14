import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

SR = 22050
ROOT = Path(r'D:\DSH\achun\video-batch')
MIX = Path(r'D:\DSH\achun\video-goofish\tools\mix-batch.py')
TMP = Path(r'D:\DSH\achun\_tmp')


def load(f):
    p = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(f), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                       capture_output=True)
    return np.frombuffer(p.stdout, dtype=np.float32)


def rms(x):
    return float(20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9))


def band(x, lo, hi):
    sos = butter(3, [lo / (SR / 2), min(hi, SR / 2 - 100) / (SR / 2)], btype='band', output='sos')
    y = sosfilt(sos, x)
    return float(20 * np.log10(np.sqrt((y ** 2).mean()) + 1e-9))


idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
TMP.mkdir(exist_ok=True)

# 取 4 条（每种变体一条）验证 BGM 电平与明亮度
samples = [idx[0], idx[1], idx[2], idx[3]]
print(f'{"序号":<5}{"变体":<5}{"人声":>8}{"BGM":>8}{"差值":>8}{"中高":>8}')
rows = []
for it in samples:
    proj = ROOT / it['dir']
    v = it['i'] % 4 + 1
    vo_path = TMP / f'vo_{it["i"]}.mp4'
    subprocess.run(['python', str(MIX), str(proj), '--music-gain', '0.0', '--out', str(vo_path)],
                   check=True, capture_output=True, cwd=str(proj))
    vx = load(vo_path)
    fx = load(proj / 'renders' / 'final.mp4')
    n = min(len(vx), len(fx))
    bgm = fx[:n] - vx[:n]
    rows.append((it['i'] + 1, v, rms(vx), rms(bgm), rms(bgm) - rms(vx), band(bgm, 1500, 5000)))
    vo_path.unlink(missing_ok=True)

for n, v, vv, bb, dd, mh in rows:
    print(f'{n:<5}v{v:<4}{vv:>8.1f}{bb:>8.1f}{dd:>8.1f}{mh:>8.1f}')

print()
print('目标：人声约 -13 dB，BGM 比人声低 6~9 dB（现在约 -8），中高 > -12 dB')
