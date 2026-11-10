# -*- coding: utf-8 -*-
"""导出 100 个仓库网址清单（含画面/文案/文件路径对应关系）。

  python tools/export-urls.py
"""
import json
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'
OUT = SRC / 'out'


def main():
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    rows = []
    for it in idx:
        c = json.loads((ROOT / it['dir'] / 'content.json').read_text(encoding='utf-8'))
        rows.append({
            'n': it['i'] + 1,
            'repo': it['repo'],
            'url': c['url'],
            'stars': it['stars'],
            'created': c['created'],
            'lang': c.get('lang', ''),
            'hook': it['hook'],
            'video': f"video-batch/{it['dir']}/renders/final.mp4",
            'video_blank': f"video-batch/{it['dir']}/renders/final-blank.mp4",
            'copy': f"out/发布包/{it['i']+1:03d}-{it['dir']}.md",
            'shown_in_frame': True,   # 第 3 张卡「git clone <url>」画面内可见
        })

    # CSV（Excel 友好）
    import csv
    with open(OUT / '仓库网址清单.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(['序号', '仓库', '网址', '星数', '上线日期', '语言', '钩子',
                    '成片', '留白版', '文案', '网址在画面内'])
        for r in rows:
            w.writerow([r['n'], r['repo'], r['url'], r['stars'], r['created'], r['lang'],
                        r['hook'], r['video'], r['video_blank'], r['copy'], '是'])

    # Markdown
    md = ['# 100 个仓库网址清单', '',
          '每个网址都同时出现在**成片第 3 张卡**（`git clone <url>`，可截图核对）和本表。', '',
          '| # | 仓库 | 网址 | ★ | 上线 | 语言 |', '|---|---|---|---|---|---|']
    for r in rows:
        md.append(f"| {r['n']} | {r['repo']} | {r['url']} | {r['stars']} | {r['created']} | {r['lang']} |")
    md += ['', f'共 {len(rows)} 条。', '',
           '> 抖音文案里刻意不含链接（平台判站外引流会限流），所以网址只放在**画面内**与这份清单里。']
    (OUT / '仓库网址清单.md').write_text('\n'.join(md), encoding='utf-8')

    # JSON
    (OUT / '仓库网址清单.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'导出 {len(rows)} 条 → out/仓库网址清单.csv / .md / .json')


if __name__ == '__main__':
    main()
