# -*- coding: utf-8 -*-
"""给每个批量工程补齐运行时依赖（engine / recipe.js / index.html / assets / audio）。"""
import json
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'


def main():
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 100
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    for item in idx[:limit]:
        proj = ROOT / item['dir']
        if not proj.exists():
            continue
        # engine（指向源工程，避免重复 3GB 字体）
        if not (proj / 'engine').exists():
            try:
                (proj / 'engine').symlink_to(SRC / 'engine', target_is_directory=True)
            except Exception:
                shutil.copytree(SRC / 'engine', proj / 'engine', dirs_exist_ok=True)
        for f in ('recipe.js', 'index.html'):
            if not (proj / f).exists():
                shutil.copy(SRC / f, proj / f)
        (proj / 'assets').mkdir(exist_ok=True)
        (proj / 'audio').mkdir(exist_ok=True)
        (proj / 'renders').mkdir(exist_ok=True)
        for f in ('score.wav',):
            if not (proj / 'audio' / f).exists():
                shutil.copy(SRC / 'audio' / f, proj / 'audio' / f)
UF = None


# 共用一条卡点 BGM（无版权、128BPM），所有人都用同一份
BED = SRC / 'audio/bgm/edm-cut.wav'


def link_bed():
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    for item in idx:
        proj = ROOT / item['dir']
        if not proj.exists():
            continue
        (proj / 'audio/bgm').mkdir(parents=True, exist_ok=True)
        dst = proj / 'audio/bgm/edm-cut.wav'
        if not dst.exists():
            try:
                dst.hardlink_to(BED)
            except Exception:
                shutil.copy(BED, dst)


if __name__ == '__main__':
    main()
    link_bed()
    print('deps ready')
