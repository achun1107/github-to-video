# -*- coding: utf-8 -*-
"""校验「解说 = 文案」：标题/副标题/正文必须与 vo1.srt 完全一致。

  python tools/check-copy-sync.py
"""
import json
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'
PACK = SRC / 'out' / '发布包'


def read_srt_text(p):
    if not p.exists():
        return []
    txt = p.read_text(encoding='utf-8-sig', errors='replace')
    blocks = re.split(r'\n\s*\n', txt.strip())
    out = []
    for b in blocks:
        lines = [x for x in b.strip().split('\n') if x.strip()]
        if len(lines) >= 3:
            out.append(''.join(lines[2:]).strip())
    return out


def norm(s):
    return (s or '').replace(' 万,个', ' 万').replace(' 千,个', ' 千').replace(',个', ' 个').replace(' ', '')


def main():
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    bad = []
    for it in idx:
        md = PACK / f"{it['i']+1:03d}-{it['dir']}.md"
        if not md.exists():
            bad.append((it['repo'], 'no copy'))
            continue
        txt = md.read_text(encoding='utf-8')
        sents = read_srt_text(ROOT / it['dir'] / 'audio/vo1.srt')
        if not sents:
            bad.append((it['repo'], 'no srt'))
            continue

        title = txt.split('## 标题')[1].split('\n')[1].strip()
        sub = txt.split('## 副标题（画面第二行）')[1].split('\n')[1].strip()
        body = txt.split('## 正文')[1].split('———')[0].strip()

        want_title = norm(sents[0]).rstrip('。')
        want_sub = norm(sents[1]).rstrip('。') if len(sents) > 1 else ''
        want_body = norm(''.join(sents))

        errs = []
        if norm(title) != want_title:
            errs.append(f'标题「{title}」≠ 解说「{want_title}」')
        if want_sub and norm(sub) != want_sub:
            errs.append(f'副标题「{sub}」≠ 解说「{want_sub}」')
        if norm(body) != want_body:
            errs.append('正文与解说全文不一致')
        if errs:
            bad.append((it['repo'], '; '.join(errs)[:110]))

    for r, e in bad[:10]:
        print(f'  {r:<38} {e}')
    print(f'\n解说/文案一致：{len(idx)-len(bad)}/{len(idx)}')


if __name__ == '__main__':
    main()
