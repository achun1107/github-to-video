# -*- coding: utf-8 -*-
"""列出某个抖音视频的所有可下载地址及其大小，挑最长的那个。"""
import re
import sys
import urllib.parse
import urllib.request

UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 '
      '(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
VID = sys.argv[1] if len(sys.argv) > 1 else '7651119042799565267'
URL = f'https://www.iesdouyin.com/share/video/{VID}/'

req = urllib.request.Request(URL)
req.add_header('User-Agent', UA)
req.add_header('Referer', 'https://www.douyin.com/')
html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'replace')
print('页面长度', len(html))

cands = set()
for pat in (r'"play_addr":\{[^}]*"url_list":\[(.*?)\]',
            r'"playApi":"([^"]+)"',
            r'"uri":"([^"]+)"'):
    for m in re.finditer(pat, html, re.S):
        for u in re.findall(r'"(https?://[^"]+)"', m.group(1) if 'url_list' in pat else m.group(0)):
            u = u.replace('\\u002F', '/').replace('\\/', '/').replace('\\u0026', '&')
            if u.startswith('http'):
                cands.add(u)

# 兜底：全页 mp4
for u in re.findall(r'https?://[^\s"\'\\<>]+?\.mp4[^\s"\'\\<>]*', html):
    cands.add(u.replace('\\u002F', '/').replace('\\/', '/'))

print('候选', len(cands))
rows = []
for u in cands:
    u2 = u.replace('/playwm/', '/play/')
    try:
        r = urllib.request.Request(u2, method='HEAD')
        r.add_header('User-Agent', UA)
        r.add_header('Referer', 'https://www.douyin.com/')
        with urllib.request.urlopen(r, timeout=20) as resp:
            size = int(resp.headers.get('Content-Length') or 0)
    except Exception as e:
        size = -1
    rows.append((size, u2))

rows.sort(reverse=True)
for size, u in rows[:8]:
    print(f'  {size/1e6:8.2f} MB  {u[:110]}')
