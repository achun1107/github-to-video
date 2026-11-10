# -*- coding: utf-8 -*-
"""抓取 2026-10-01 之后创建、star > 1000 的 GitHub 项目（多维度筛选）。

  python tools/harvest.py [--min-stars 1000] [--since 2026-10-01]

GitHub Search 不支持 `a OR b` 混在 qualifier 里，所以每个维度只用一个 qualifier，
不同话题/语言分开多次查询（Search API 独立配额 10 次/分钟）。
"""
import json
import time
import urllib.parse
import urllib.request
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / 'data'
OUT.mkdir(exist_ok=True)


def api(q, per_page=50, retries=3):
    url = ('https://api.github.com/search/repositories?q=' + urllib.parse.quote(q, safe=':>')
           + f'&sort=stars&order=desc&per_page={per_page}')
    for k in range(retries):
        req = urllib.request.Request(url, headers={
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'goofish-video-research',
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            print(f'    retry {k+1}: {e}')
            time.sleep(10 * (k + 1))
    return {'items': []}


def main():
    since = '2026-10-01'
    min_stars = int(sys.argv[sys.argv.index('--min-stars') + 1]) if '--min-stars' in sys.argv else 1000

    base = f'created:>{since} stars:>{min_stars}'
    queries = [
        ('A_popular', base),
        ('B_ai', base + ' topic:ai'),
        ('B_llm', base + ' topic:llm'),
        ('B_agent', base + ' topic:agent'),
        ('C_zh', base + ' language:Chinese'),
        ('C_lang_py', base + ' language:Python'),
        ('C_lang_ts', base + ' language:TypeScript'),
        ('D_cli', base + ' topic:cli'),
        ('D_tool', base + ' topic:developer-tools'),
        ('E_web', base + ' topic:web'),
    ]

    all_items = {}
    for name, q in queries:
        print(f'[{name}] {q}')
        d = api(q)
        print(f'  total={d.get("total_count")} got={len(d.get("items", []))}')
        for r in d.get('items', []):
            prev = all_items.get(r['full_name'], {})
            dims = sorted(set(prev.get('_dims', []) + [name]))
            r['_dims'] = dims
            all_items[r['full_name']] = r
        time.sleep(7)

    rows = []
    for full, r in all_items.items():
        rows.append({
            'full_name': full,
            'url': r['html_url'],
            'stars': r['stargazers_count'],
            'forks': r['forks_count'],
            'created': r['created_at'][:10],
            'pushed': r['pushed_at'][:10],
            'lang': r.get('language') or '',
            'desc': (r.get('description') or '').strip(),
            'topics': r.get('topics', []),
            'dims': r['_dims'],
            'days': max(1, 40 - int(r['created_at'][8:10])),  # 粗略：距 10-01 的天数
        })
    # 运营价值：star 数 + 维度覆盖数（多维命中说明有话题性）
    for r in rows:
        r['score'] = r['stars'] + len(r['dims']) * 800
    rows.sort(key=lambda x: -x['score'])
    (OUT / 'candidates.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n候选总数 {len(rows)} → data/candidates.json')
    for r in rows[:20]:
        print(f"{r['stars']:>6} {r['created']} {r['full_name']:<38} {len(r['dims'])}维 {'/'.join(r['dims'])[:60]}")


if __name__ == '__main__':
    main()
