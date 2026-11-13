# -*- coding: utf-8 -*-
"""从 vo1.srt 生成 vo-subs.js，让画面说明条 = 解说原句。

  python tools/gen-vo-subs.py [--limit 100]

说明条时间码直接用 srt 的句子时间，跟配音严丝合缝。
"""
import json
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'


def parse_srt(p):
    if not p.exists():
        return []
    txt = p.read_text(encoding='utf-8-sig', errors='replace')
    out = []
    for b in re.split(r'\n\s*\n', txt.strip()):
        lines = [x for x in b.strip().split('\n') if x.strip()]
        if len(lines) < 3:
            continue
        m = re.search(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)', lines[1])
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        a = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        b2 = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        text = ''.join(lines[2:]).strip()
        # 清掉 TTS 在数字后插入的逗号：「5.5 万,个」→「5.5 万」
        text = text.replace(' 万,个', ' 万').replace(' 千,个', ' 千').replace(',个', ' 个')
        out.append({'a': round(a, 3), 'b': round(b2, 3), 'zh': text})
    return out


def main():
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 100
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))[:limit]
    made = miss = 0
    for it in idx:
        proj = ROOT / it['dir']
        subs = parse_srt(proj / 'audio/vo1.srt')
        body = 'window.VO_SUBS = ' + json.dumps(subs, ensure_ascii=False, indent=2) + ';\n'
        (proj / 'vo-subs.js').write_text(body, encoding='utf-8')
        if subs:
            made += 1
        else:
            miss += 1
    print(f'生成 vo-subs.js：{made} 条，缺字幕 {miss} 条')
    if made:
        s = parse_srt(ROOT / idx[0]['dir'] / 'audio/vo1.srt')
        print('示例（第一条）：')
        for x in s:
            print(f"  {x['a']:>5.2f}-{x['b']:>5.2f}s  {x['zh']}")


if __name__ == '__main__':
    main()
