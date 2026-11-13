# -*- coding: utf-8 -*-
"""独立复验：逐条回查 GitHub API，确认 created>=2026-10-01 且 stars>=1000。

  python tools/verify-candidates.py

Search 里拿到的数据可能滞后，这里用 /repos/{owner}/{repo} 逐个核对（60 次/小时，分批跑）。
"""
import json
import time
import urllib.request
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'


def api(repo):
    req = urllib.request.Request(f'https://api.github.com/repos/{repo}', headers={
        'Accept': 'application/vnd.github+json', 'User-Agent': 'verify-loop'})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.load(r)
    except Exception as e:
        return {'_error': str(e)[:60]}


def main():
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    rows, errs = [], 0
    for n, it in enumerate(idx, 1):
        d = api(it['repo'])
        if '_error' in d:
            errs += 1
            rows.append({'repo': it['repo'], 'api': 'ERR', 'note': d['_error']})
            continue
        created = d.get('created_at', '')[:10]
        stars = d.get('stargazers_count', 0)
        ok = created >= '2026-10-01' and stars >= 1000
        rows.append({'repo': it['repo'], 'created': created, 'stars': stars,
                     'claim_stars': it['stars'], 'ok': ok})
        if not ok:
            print(f'  !! {it["repo"]:<40} created={created} stars={stars}')
        time.sleep(0.8)
        if errs and n % 20 == 0:
            print(f'  ...{n}/{len(idx)}  已错 {errs}')

    good = sum(1 for r in rows if r.get('ok'))
    (SRC / 'out' / '条件复验.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n复验：符合条件 {good}/{len(idx)}，API 错误 {errs}')
    if errs:
        print('  （API 限流时错误项不算失败，下次重跑会补）')


if __name__ == '__main__':
    main()
