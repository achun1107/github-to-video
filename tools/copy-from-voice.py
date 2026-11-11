# -*- coding: utf-8 -*-
"""从「解说原文」反推文案 —— 保证解说与文案一字不差。

  python tools/copy-from-voice.py [--limit 100]

原理：vo1.srt 是配音的字幕（=观众听到的话），直接拿它当正文骨架：
  标题   = 画面钩子（第 1 句去掉句号）
  副标题 = 第 2 句
  正文   = 逐句解说原文（观众听到什么，看到的就是什么）
  封面   = 钩子 + 核心数字
话题仍按仓库标签/语言生成。
"""
import json
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'
OUT = SRC / 'out' / '发布包'


def read_srt(p):
    """返回 [(start, end, text)]"""
    if not p.exists():
        return []
    txt = p.read_text(encoding='utf-8-sig', errors='replace')
    blocks = re.split(r'\n\s*\n', txt.strip())
    out = []
    for b in blocks:
        lines = [x for x in b.strip().split('\n') if x.strip()]
        if len(lines) < 3:
            continue
        m = re.match(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)', lines[1])
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        out.append((round(start, 2), round(end, 2), ''.join(lines[2:]).strip()))
    return out


def norm_num(s):
    """把 5.5 万, → 5.5 万；7.1 千, → 7.1 千（去掉 TTS 插入的逗号）"""
    return s.replace(' 万,个', ' 万').replace(' 千,个', ' 千').replace(',个', ' 个').replace('，。', '。')


def tags_for(d):
    topics = [t for t in (d.get('topics') or []) if t.isascii()][:3]
    pool = ['#开源项目', '#GitHub', '#程序员']
    if d.get('lang'):
        pool.append('#' + d['lang'])
    low = ' '.join(topics).lower()
    if any(k in low for k in ('ai', 'llm', 'agent')):
        pool += ['#AI工具', '#Agent']
    elif any(k in low for k in ('cli', 'tool')):
        pool += ['#效率工具', '#命令行']
    elif any(k in low for k in ('web', 'frontend', 'ui')):
        pool += ['#前端', '#界面']
    else:
        pool += ['#涨知识', '#神器分享']
    pool.append('#一天一个开源项目')
    seen, out = set(), []
    for t in pool:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return ' '.join(out[:6])


def build(it, proj):
    d = json.loads((proj / 'content.json').read_text(encoding='utf-8'))
    segs = read_srt(proj / 'audio/vo1.srt')
    if not segs:
        return None

    sentences = [norm_num(s[2]) for s in segs]
    hook = sentences[0].rstrip('。')
    sub = sentences[1].rstrip('。') if len(sentences) > 1 else ''

    body_lines = [''.join(sentences)]   # 解说全文，观众听到什么就看到什么
    body_lines.append('')
    body_lines.append('———')
    body_lines.append('')
    if d.get('desc'):
        body_lines.append(f'一句话：{d["desc"][:90]}')
    body_lines.append(f'仓库：{d["repo"]}　星数：{d["starHuman"]}　Fork：{d["forkHuman"]}')
    body_lines.append(f'上线：{d["created"]}　语言：{d.get("lang") or "多语言"}')
    if d.get('topics'):
        body_lines.append(f'标签：{" / ".join("#" + t for t in d["topics"][:4])}')

    cover = [
        f'第一行：{hook}',
        f'第二行：{d["starHuman"]} Star · {int(d["created"][5:7])} 月上线',
        f'第三行：{d["name"]}',
    ]

    return {
        'n': it['i'] + 1,
        'repo': d['repo'],
        'dir': it['dir'],
        'title': hook,
        'sub': sub,
        'sentences': sentences,
        'body': '\n'.join(body_lines),
        'tags': tags_for(d),
        'cover': '\n'.join(cover),
        'stars': it['stars'],
        'created': d['created'],
        'lang': d.get('lang') or '',
    }


def main():
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 100
    OUT.mkdir(parents=True, exist_ok=True)
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))[:limit]

    packs, miss = [], []
    for it in idx:
        p = build(it, ROOT / it['dir'])
        if p:
            packs.append(p)
        else:
            miss.append(it['repo'])

    for p in packs:
        md = f"""# {p['n']:03d} · {p['repo']}

## 标题
{p['title']}

## 副标题（画面第二行）
{p['sub']}

## 正文
{p['body']}

## 话题
{p['tags']}

## 封面三行
{p['cover']}

## 解说全文（与视频一字不差）
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(p['sentences']))}

## 工程
video-batch/{p['dir']}
"""
        (OUT / f"{p['n']:03d}-{p['dir']}.md").write_text(md, encoding='utf-8')

    total = ['# 抖音发布包 · 100 组（解说即文案）\n',
             f'共 {len(packs)} 条。标题、副标题、正文全部取自视频里的解说原文，确保一条视频一套话。\n']
    for p in packs:
        total.append(f"\n---\n\n## {p['n']:03d} · {p['repo']} · {p['stars']} ★\n")
        total.append(f"**标题**：{p['title']}\n\n")
        total.append(f"**副标题**：{p['sub']}\n\n")
        total.append(f"**正文**\n\n```\n{p['body']}\n```\n\n")
        total.append(f"**话题**：{p['tags']}\n\n")
        total.append(f"**封面**：{p['cover'].replace(chr(10), ' ｜ ')}\n")
    (OUT / '抖音发布包-100组.md').write_text(''.join(total), encoding='utf-8')

    import csv
    with open(OUT / '发布清单.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(['序号', '仓库', '星数', '标题', '副标题', '话题', '上线', '语言', '工程目录'])
        for p in packs:
            w.writerow([p['n'], p['repo'], p['stars'], p['title'], p['sub'],
                        p['tags'], p['created'], p['lang'], p['dir']])

    print(f'生成 {len(packs)} 组（解说即文案）')
    if miss:
        print(f'缺字幕跳过 {len(miss)} 条: {miss[:5]}')


if __name__ == '__main__':
    main()
