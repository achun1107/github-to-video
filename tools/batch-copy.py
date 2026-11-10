# -*- coding: utf-8 -*-
"""生成 100 组抖音发布包（标题 / 正文 / 话题 / 封面文案）。

  python tools/batch-copy.py --limit 100

输出：
  发布包/抖音发布包.md      —— 100 组合集（总表，可直接浏览）
  发布包/NN-仓库名.md        —— 单条（复制粘贴用）
  发布包/发布清单.csv        —— 排期表
"""
import csv
import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
OUT = SRC / 'out' / '发布包'


def _days(created):
    from datetime import date
    y, m, dd = (int(x) for x in created.split('-'))
    return (date(2026, 11, 10) - date(y, m, dd)).days


def _days_line(created):
    from datetime import date
    y, m, dd = (int(x) for x in created.split('-'))
    days = (date(2026, 11, 10) - date(y, m, dd)).days
    if days <= 14:
        return f'{created} 上线，{days} 天就冲到下面这个数。'
    if days <= 35:
        return f'{created} 上线，{days} 天攒到这个数。'
    return f'{created} 上线，{days} 天累积下来。'


def build(r, d, hook):
    """r=候选原始记录, d=content, hook=标题钩子"""
    stars, forks = d['starHuman'], d['forkHuman']
    name, owner, lang = d['name'], d['owner'], d.get('lang') or ''
    created, pushed = d['created'], d['pushed']
    topics = d.get('topics') or []
    desc = d['desc']

    # ── 标题（≤28 字最优）
    cand_titles = [
        f'{stars}★ 的开源神作：{name}',
        f'{created[5:]} 上线，{stars} Star：{name}',
        f'{lang or "多语言"} 写的 {stars}★ 项目：{name}',
        f'{hook}｜{name}',
    ]
    title = next((t for t in cand_titles if len(t) <= 30), cand_titles[0])

    # ── 正文
    body_lines = [
        hook + '。',
        f'',
        f'{d["repo"]}，{stars} Star，{forks} Fork。',
        _days_line(created),
    ]
    if desc:
        body_lines.append('')
        # 英文简介整句保留（带引号），不截成半句；过长就省略
        if len(desc) <= 90:
            if len(desc) <= 100:
                body_lines.append(f'原文简介："{desc}"')
            else:
                _cut = desc[:96]
                if ' ' in _cut:
                    _cut = _cut[:_cut.rfind(' ')]
                body_lines.append(f'原文简介："{_cut}…"')
    body_lines.append('')
    if topics:
        body_lines.append(f'标签：{" / ".join("#" + t for t in topics[:4])}')
    body_lines.append(f'语言：{lang or "多语言"} · 最近更新 {pushed} · 开源可读')
    body_lines.append('')
    body_lines.append(f'仓库名 {name}，GitHub 搜得到。')
    body_lines.append('')
    body_lines.append('想看我拆哪一类（AI / 工具 / 前端 / 系统），评论区点一下。')

    # ── 话题（4–6 个）
    tag_pool = ['#开源项目', '#GitHub', '#程序员']
    if lang:
        tag_pool.append('#' + lang)
    if any(k in (topics or []) for k in ('ai', 'llm', 'agent')):
        tag_pool += ['#AI工具', '#Agent']
    elif any(k in (topics or []) for k in ('cli', 'tool')):
        tag_pool += ['#效率工具', '#命令行']
    elif any(k in (topics or []) for k in ('web', 'frontend', 'ui')):
        tag_pool += ['#前端', '#界面']
    else:
        tag_pool += ['#涨知识', '#神器分享']
    tag_pool.append('#一天一个开源项目')
    tags = ' '.join(tag_pool[:6])

    cover = [
        f'第一行：{hook.replace("来了", "")}来了',
        f'第二行：{stars} Star 才一个月',
        f'第三行：{name}',
    ]

    return {
        'repo': d['repo'], 'stars': d['stars'], 'title': title,
        'body': '\n'.join(x for x in body_lines if x is not None),
        'tags': tags, 'cover': '\n'.join(cover),
        'created': created, 'lang': lang,
    }


def main():
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 100
    OUT.mkdir(parents=True, exist_ok=True)
    idx = json.loads((SRC.parent / 'video-batch' / 'index.json').read_text(encoding='utf-8'))

    packs = []
    for n, it in enumerate(idx[:limit], 1):
        proj = SRC.parent / 'video-batch' / it['dir']
        d = json.loads((proj / 'content.json').read_text(encoding='utf-8'))
        p = build(it, d, it['hook'])
        p['hook'] = it['hook']
        p['sub'] = it['sub']
        p['n'] = n
        p['dir'] = it['dir']
        packs.append(p)

    # 单条
    for p in packs:
        md = f"""# {p['n']:03d} · {p['repo']}

## 标题
{p['title']}

## 正文
{p['body']}

## 话题
{p['tags']}

## 封面三行
{p['cover']}

## 工程
video-batch/{p['dir']}
"""
        (OUT / f"{p['n']:03d}-{p['dir']}.md").write_text(md, encoding='utf-8')

    # 总表
    total = ['# 抖音发布包 · 100 组（2026-10 至今 · 1000+ Star 开源项目）\n',
             f'共 {len(packs)} 条，每条含标题/正文/话题/封面三行。\n']
    for p in packs:
        total.append(f"\n---\n\n## {p['n']:03d} · {p['repo']} · {p['stars']} ★\n")
        total.append(f"**标题**：{p['title']}\n\n")
        total.append(f"**正文**\n\n```\n{p['body']}\n```\n\n")
        total.append(f"**话题**：{p['tags']}\n\n")
        total.append(f"**封面**：{p['cover'].replace(chr(10), ' ｜ ')}\n")
    (OUT / '抖音发布包-100组.md').write_text(''.join(total), encoding='utf-8')

    # CSV 排期
    with open(OUT / '发布清单.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(['序号', '仓库', '星数', '标题', '话题', '上线日期', '语言', '工程目录'])
        for p in packs:
            w.writerow([p['n'], p['repo'], p['stars'], p['title'], p['tags'],
                        p['created'], p['lang'], p['dir']])

    print(f'生成 {len(packs)} 组 → {OUT}')
    print(f'  抖音发布包-100组.md / 发布清单.csv / {len(packs)} 个单条 .md')


if __name__ == '__main__':
    main()
