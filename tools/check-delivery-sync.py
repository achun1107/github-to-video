import hashlib
import json
from pathlib import Path

ROOT = Path(r'D:\DSH\achun')
BATCH = ROOT / 'video-batch'
DELIV = ROOT / '00-交付-100条视频'


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


idx = json.loads((BATCH / 'index.json').read_text(encoding='utf-8'))
bad = []
for it in idx:
    n = it['i'] + 1
    owner, name = it['repo'].split('/')
    base = f'{n:03d}-{owner}-{name}'
    src = BATCH / it['dir'] / 'renders' / 'final.mp4'
    cands = [DELIV / 'videos' / f'{base}-带配乐.mp4',
             DELIV / '手机发布包' / f'{base}.mp4']
    hs = md5(src)
    for c in cands:
        if not c.exists():
            bad.append((base, 'missing', c.name))
        elif md5(c) != hs:
            bad.append((base, 'differs', c.name))

print(f'检查 {len(idx)} 条 × 2 处交付副本')
print(f'不一致 {len(bad)}')
for b in bad[:8]:
    print('  ', b)
