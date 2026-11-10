# -*- coding: utf-8 -*-
"""并行重混：8 条同时跑，只处理超过 30 分钟未更新的片子。

  python tools/remix-fast.py [--workers 8] [--age 1800]
"""
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'
MIX = SRC / 'tools/mix-batch.py'


def do(it):
    proj = ROOT / it['dir']
    if not (proj / 'renders/raw.mp4').exists() or not (proj / 'audio/vo1.mp3').exists():
        return it['repo'], 'skip'
    try:
        r = subprocess.run([sys.executable, str(MIX), '.'], cwd=proj,
                           capture_output=True, text=True, encoding='utf-8', errors='replace',
                           timeout=900)
        return it['repo'], ('ok' if r.returncode == 0 else 'fail:' + r.stderr.strip()[-80:])
    except subprocess.TimeoutExpired:
        return it['repo'], 'timeout'


def main():
    workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 8
    age = int(sys.argv[sys.argv.index('--age') + 1]) if '--age' in sys.argv else 1800
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    now = time.time()
    todo = []
    for it in idx:
        fin = ROOT / it['dir'] / 'renders' / 'final.mp4'
        if fin.exists() and (now - fin.stat().st_mtime) < age:
            continue
        todo.append(it)
    print(f'待重混 {len(todo)} 条（{workers} 并发）')
    t0 = time.time()
    res = {'ok': 0, 'fail': 0, 'skip': 0}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (repo, st) in enumerate(ex.map(do, todo), 1):
            key = st.split(':')[0]
            res[key] = res.get(key, 0) + 1
            if key != 'ok':
                print(f'  {repo:<38} {st}')
            if i % 20 == 0:
                print(f'  ...{i}/{len(todo)}  {int(time.time()-t0)}s', flush=True)
    print(f'done ok={res["ok"]} fail={res["fail"]} skip={res["skip"]}  用时 {int(time.time()-t0)}s')


if __name__ == '__main__':
    main()
