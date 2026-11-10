# -*- coding: utf-8 -*-
"""批量生成 100 条视频工程 + 文案。

  python tools/batch-build.py --limit 100 [--jobs 3] [--root video-batch]

单条流程：
  1. data/candidates.json[i] → content.json / content.js
  2. 模板 film.js 写入工程（卡片按该仓库数据生成）
  3. engine 软链
  4. render.py 渲画面（并行）
  5. 配上 batch-music（128BPM 卡点）+ 人声混音
  6. 写真 · 文案到 out/
"""
import json
from datetime import date
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))


# 直接复用 batch-make 的函数（文件名带连字符，用 exec 载入）
ns = {}
src = (ROOT / 'tools/batch-make.py').read_text(encoding='utf-8-sig')
src = src.split('if __name__ ==')[0]
ns['__file__'] = str(ROOT / 'tools/batch-make.py')
exec(src, ns)
build_content = ns['build_content']
pick_hook = ns['pick_hook']
build_douyin = ns['build_douyin']
slug = ns['slug']
human = ns['human']

FILM_TMPL = (ROOT / 'tools/film-batch.js').read_text(encoding='utf-8')


def _jsq(text):
    """安全转义成 JS 单引号字符串内容：先转义反斜杠，再转义单引号。"""
    return (text or '').replace('\\', '\\\\').replace("'", "\\'").replace('\n', ' ')


def main():
    a = sys.argv[1:]
    limit = int(a[a.index('--limit') + 1]) if '--limit' in a else 100
    out_root = Path(a[a.index('--root') + 1]) if '--root' in a else ROOT.parent / 'video-batch'
    out_root.mkdir(exist_ok=True)

    cand = json.loads((ROOT / 'data/candidates.json').read_text(encoding='utf-8'))
    picked = cand[:limit]

    index = []
    for i, r in enumerate(picked):
        d = build_content(r)
        hook, sub = pick_hook(d)
        title, body = build_douyin(d, hook, sub)
        proj = out_root / slug(r['full_name'])
        proj.mkdir(exist_ok=True)
        (proj / 'content.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
        (proj / 'content.js').write_text('window.CONTENT = ' + json.dumps(d, ensure_ascii=False, indent=2) + ';\n',
                                         encoding='utf-8')
        days = (date(2026, 11, 10) - date(*[int(x) for x in r['created'].split('-')])).days
        film = (FILM_TMPL
                .replace('__HOOK__', hook.replace("'", "\\'"))
                .replace('__SUB__', sub.replace("'", "\\'"))
                .replace('__STAR__', d['starHuman'])
                .replace('__FORKS__', d['forkHuman'])
                .replace('__NAME__', d['name'].replace("'", "\\'"))
                .replace('__OWNER__', d['owner'].replace("'", "\\'"))
                .replace('__LANG__', (d['lang'] or 'Multi').replace("'", "\\'"))
                .replace('__CREATED__', d['created'])
                .replace('__DESC__', _jsq(build_content(r)['desc']))
                .replace('__TOPICS__', json.dumps(d['topics'], ensure_ascii=False))
                .replace('__DAYS__', str(days)))
        (proj / 'film.js').write_text(film, encoding='utf-8')
        shutil.copy(ROOT / 'index.html', proj / 'index.html')
        (proj / 'copy.md').write_text(body, encoding='utf-8')
        index.append({'i': i, 'repo': r['full_name'], 'stars': r['stars'],
                      'title': title, 'dir': str(proj.name), 'hook': hook, 'sub': sub})
        print(f'[{i+1}/{len(picked)}] {r["full_name"]:<40} {d["starHuman"]:>5}★  {hook}')

    (out_root / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n工程目录 {len(index)} 个 → {out_root}')
    print(f'清单 → {out_root / "index.json"}')


if __name__ == '__main__':
    main()
