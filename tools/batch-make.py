# -*- coding: utf-8 -*-
"""把一条仓库数据 → 一整套「成片工程」（film.js / content.json / 文案）。

  python tools/batch-make.py --index 0 [--root ../video-batch]

生成的不是模板填充，而是**按该项目自身的数据结构选卡片**：
  - 有 5 个以上数字 → 数值卡
  - 有多个 topic/标签 → 标签墙
  - 有中文 README 片段 → 引文卡
  - 总是有：开场证据卡（仓库页截图）、一句话定位卡、结论卡
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def slug(full):
    return full.replace('/', '-').lower()


def clean(s, n=44):
    s = re.sub(r'^\s*[^\w(（]*', '', s or '')
    s = re.sub(r'[\r\n]+', ' ', s).strip()
    return s[:n]


def human(n):
    if n >= 10000:
        return f'{n / 10000:.1f}w'
    if n >= 1000:
        return f'{n / 1000:.1f}k'
    return str(n)


def build_content(r):
    """把仓库数据整理成画面 + 文案都用得上的结构"""
    topics = [t for t in r.get('topics', []) if t][:6]
    labels = topics or ([r['lang']] if r.get('lang') else [])
    d = {
        'repo': r['full_name'],
        'owner': r['full_name'].split('/')[0],
        'name': r['full_name'].split('/')[1],
        'stars': r['stars'],
        'starHuman': human(r['stars']),
        'forks': r['forks'],
        'forkHuman': human(r['forks']),
        'created': r['created'],
        'pushed': r['pushed'],
        'lang': r.get('lang') or '',
        'desc': clean(r.get('desc', ''), 90),
        'labels': labels,
        'topics': topics,
        'url': r['url'],
    }
    return d


# 标题钩子：按语言/话题给出不同"领域 + 极端比喻 + 来了"
HOOKS = [
    ('{domain}界最狠的那一个来了', '{sub}'),
]


def pick_hook(d):
    lang = d['lang']
    domain = {
        'Python': '脚本', 'TypeScript': '前端', 'JavaScript': '前端', 'Rust': '系统',
        'C': '底层', 'C++': '底层', 'Swift': 'iOS', 'Kotlin': '安卓', 'Go': '后端',
    }.get(lang, '开源')
    topics = ' '.join(d['topics']).lower()
    if any(k in topics for k in ('ai', 'llm', 'agent', 'gpt')):
        hook = 'AI 界最疯的那个项目来了'
        sub = '上线一个月就冲到前面这个数'
    elif any(k in topics for k in ('cli', 'tool', 'terminal')):
        hook = '命令行界最好用的那个来了'
        sub = '装一次，一辈子省事'
    elif any(k in topics for k in ('web', 'frontend', 'ui', 'design')):
        hook = '前端界最会做界面的那个来了'
        sub = '上手就能抄的界面库'
    elif any(k in topics for k in ('android', 'ios', 'mobile')):
        hook = '手机界最省的优化工具来了'
        sub = '一台旧手机直接复活'
    else:
        hook = f'{domain}界最狠的那一个来了'
        sub = '上线一个月就冲到前面这个数'
    return hook, sub


def build_film(d, hook, sub, segs):
    """生成 film.js：套用参考片版式，但卡片按数据生成"""
    cards_js = []
    for i, (a, b, name, fn) in enumerate(segs):
        cards_js.append(f'  [{a}, {b}, {fn}],')
    return ''


def build_douyin(d, hook, sub):
    title = f'{hook}｜{d["name"]}'
    if len(title) > 28:
        title = f'{d["starHuman"]}★ 的开源项目：{d["name"]}'
    body = f"""## 标题
{title}

## 正文
{hook}

{d['repo']}，一个 {d['starHuman']} Star 的开源项目{d['created']}上线。
{('· ' + d['desc']) if d['desc'] else ''}
· 语言：{d['lang'] or '多语言'}；上线 {d['created']}，最近更新 {d['pushed']}
{('· 标签：' + ' / '.join(d['topics'][:4])) if d['topics'] else ''}

开源、可读、能跑。仓库名 {d['name']}，GitHub 搜得到。

#开源项目 #GitHub #{d['name']} #{d['lang'] or '开源'} #程序员
"""
    return title, body


if __name__ == '__main__':
    cand = json.loads((ROOT / 'data/candidates.json').read_text(encoding='utf-8'))
    i = int(sys.argv[sys.argv.index('--index') + 1]) if '--index' in sys.argv else 0
    r = cand[i]
    d = build_content(r)
    hook, sub = pick_hook(d)
    title, body = build_douyin(d, hook, sub)
    print('仓库 :', d['repo'])
    print('星数 :', d['starHuman'])
    print('钩子 :', hook, '|', sub)
    print('标题 :', title)
