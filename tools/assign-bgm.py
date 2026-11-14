# -*- coding: utf-8 -*-
"""给每条视频分配 BGM 变体，并在拷贝后立即校验（不信任 cp 结果）。

  python tools/assign-bgm.py [--variants 4] [--verify]
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'
BGM = SRC / 'audio' / 'bgm'


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def main():
    nv = int(sys.argv[sys.argv.index('--variants') + 1]) if '--variants' in sys.argv else 4
    variants = {}
    for v in range(1, nv + 1):
        p = BGM / f'variant-{v}.wav'
        if not p.exists():
            sys.exit(f'缺 {p}')
        variants[v] = md5(p)
    # 变体之间必须真的不同
    uniq = len(set(variants.values()))
    print(f'变体去重后 {uniq} 个（应为 {nv}）')
    if uniq != nv:
        sys.exit('变体文件有重复，先重新生成')

    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    counts = {v: 0 for v in range(1, nv + 1)}
    mismatch = []

    for it in idx:
        v = it['i'] % nv + 1
        dst_dir = ROOT / it['dir'] / 'audio' / 'bgm'
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / 'edm-cut.wav'
        # 必须先删：100 个工程的 edm-cut.wav 曾是同一 inode 的硬链接（实测 nlink=100），
        # 直接写入会连带改掉所有工程，导致 100 条变成同一个变体。
        if dst.exists():
            dst.unlink()
        shutil.copyfile(BGM / f'variant-{v}.wav', dst)
        if md5(dst) != variants[v]:
            mismatch.append(it['dir'])
        for f in dst_dir.glob('bed*.wav'):
            f.unlink(missing_ok=True)
        counts[v] += 1

    print('分配:', {f'v{k}': c for k, c in counts.items()})
    print('拷贝校验失败:', len(mismatch), mismatch[:3])

    if '--verify' in sys.argv:
        buckets = {}
        for it in idx:
            h = md5(ROOT / it['dir'] / 'audio' / 'bgm' / 'edm-cut.wav')
            v = next((k for k, hh in variants.items() if hh == h), 0)
            buckets[v] = buckets.get(v, 0) + 1
        print('复核分布:', dict(sorted(buckets.items())))


if __name__ == '__main__':
    main()
