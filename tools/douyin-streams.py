# -*- coding: utf-8 -*-
"""用 Playwright 打开抖音分享页，拦截 aweme 详情，导出所有流的时长与地址。

  python tools/douyin-streams.py <video_id 或 url> [--out json]
"""
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

TARGET = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else ''
URL = TARGET if TARGET.startswith('http') else f'https://www.iesdouyin.com/share/video/{TARGET}/'

payloads = []


def on_response(resp):
    u = resp.url
    if not any(k in u for k in ('aweme', 'iteminfo', 'detail', 'video')):
        return
    try:
        ct = resp.headers.get('content-type', '')
        if 'json' not in ct:
            return
        payloads.append((u, resp.json()))
    except Exception:
        pass


with sync_playwright() as p:
    b = p.chromium.launch(channel='chrome', headless=True)
    pg = b.new_page(user_agent=('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'))
    pg.on('response', on_response)
    try:
        pg.goto(URL, wait_until='networkidle', timeout=60000)
    except Exception as e:
        print('goto:', type(e).__name__)
    pg.wait_for_timeout(4000)
    html = pg.content()
    b.close()

print('拦截到 JSON', len(payloads))


def walk(o, path=''):
    if isinstance(o, dict):
        if 'play_addr' in o:
            yield o
        for k, v in o.items():
            yield from walk(v, f'{path}.{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f'{path}[{i}]')


found = []
for url, data in payloads:
    for item in walk(data):
        try:
            pa = item.get('play_addr') or {}
            urls = pa.get('url_list') or []
            dur = (item.get('duration') or pa.get('duration') or 0) / 1000.0
            desc = (item.get('desc') or '')[:40]
            found.append((dur, desc, urls[0] if urls else ''))
        except Exception:
            pass

# HTML 兜底
if not found:
    for u in re.findall(r'https?://[^\s"\'\\<>]+?\.mp4[^\s"\'\\<>]*', html):
        found.append((0, 'html', u.replace('\\u002F', '/').replace('\\/', '/')))

found.sort(key=lambda x: -x[0])
print('找到', len(found), '个流')
seen = set()
for dur, desc, u in found[:10]:
    key = u[:80]
    if key in seen:
        continue
    seen.add(key)
    print(f'  {dur:7.2f}s  {desc:<42} {u[:80]}')

if '--out' in sys.argv:
    out = Path(sys.argv[sys.argv.index('--out') + 1])
    out.write_text(json.dumps([{'dur': d, 'desc': s, 'url': u} for d, s, u in found],
                              ensure_ascii=False, indent=2), encoding='utf-8')
    print('→', out)
