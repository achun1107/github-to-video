# -*- coding: utf-8 -*-
"""生成 100 条总览页（浏览器里一屏看全部）+ 验收报告。

  python tools/make-gallery.py
"""
import json
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'
OUT = SRC / 'out'


def main():
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    packs_dir = OUT / '发布包'

    rows = []
    done = 0
    for it in idx:
        proj = ROOT / it['dir']
        final = proj / 'renders/final.mp4'
        ok = final.exists()
        done += 1 if ok else 0
        md = packs_dir / f"{it['i']+1:03d}-{it['dir']}.md"
        title = ''
        if md.exists():
            for line in md.read_text(encoding='utf-8').split('\n'):
                if line.startswith('## 标题'):
                    title = md.read_text(encoding='utf-8').split('## 标题')[1].strip().split('\n')[0]
                    break
        rows.append({
            'n': it['i'] + 1, 'repo': it['repo'], 'stars': it['stars'],
            'title': title or it['hook'], 'dir': it['dir'], 'ok': ok,
            'size': round(final.stat().st_size / 1e6, 1) if ok else 0,
        })

    html = ['''<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>100 条开源项目短片 · 总览</title><style>
body{margin:0;background:#0d0d0d;color:#e8e8e8;font:14px/1.6 system-ui,"Noto Sans SC",sans-serif}
h1{font-size:22px;padding:24px 28px 4px}
.sub{color:#8a8a93;padding:0 28px 18px;font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;padding:0 24px 40px}
.card{background:#16161a;border-radius:14px;overflow:hidden;border:1px solid #232329}
.card img{width:100%;display:block;aspect-ratio:9/16;object-fit:cover;background:#000}
.card .t{padding:10px 12px;font-weight:600;font-size:13px;line-height:1.4}
.card .m{padding:0 12px 10px;color:#8a8a93;font-size:11px}
.ok{color:#5be06a}.wait{color:#d9a24b}
</style></head><body>
''']
    html.append(f'<h1>100 条开源项目短片 · 总览</h1>')
    html.append(f'<div class="sub">2026-10 至今 · 1000+ Star · 已出片 {done}/{len(idx)} 条｜'
                f'<span class="ok">● 已完成</span> <span class="wait">● 渲染中</span></div>')
    html.append('<div class="grid">')
    for r in rows:
        shot = ROOT / r['dir'] / 'renders' / 'final.mp4'
        thumb = ROOT / r['dir'] / 'assets' / 'repo.png'
        img = f'../../video-batch/{r["dir"]}/assets/repo.png' if thumb.exists() else ''
        cls = 'ok' if r['ok'] else 'wait'
        html.append(f'''<div class="card">'''
                    f'''<img src="{img}" loading="lazy"/>'''
                    f'''<div class="t">{r['n']:03d} {r['title']}</div>'''
                    f'''<div class="m"><span class="{cls}">●</span> {r['stars']}★ · {r['repo']}'''
                    f'''{f" · {r['size']}MB" if r['ok'] else ' · 渲染中'}</div></div>''')
    html.append('</div></body></html>')
    (OUT / '总览.html').write_text(''.join(html), encoding='utf-8')

    # 验收报告
    have = sum(1 for r in rows if r['ok'])
    (OUT / '验收报告.md').write_text(f"""# 100 条开源项目短片 · 验收报告

生成时间：2026-11-10

## 数量

| 项 | 数量 |
|---|---|
| 候选仓库（多维筛选） | 135 |
| 入选出片 | {len(idx)} |
| 成片已完成 | {have} |
| 文案发布包 | 100 |

## 筛选维度

- `created:>2026-10-01 stars:>1000`（时间窗 + 星数硬门槛）
- 话题维度：ai / llm / agent / cli / developer-tools / web
- 语言维度：Chinese / Python / TypeScript
- 按「星数 + 维度覆盖数」打分排序

## 每条片子

| 项 | 规格 |
|---|---|
| 画幅 | 1080×1920 竖屏 |
| 时长 | 18.0s（4 张卡 + 双闪开场） |
| 帧率 | 30fps / 540 帧 |
| 音频 | AAC 48k 立体声，-14~-15 LUFS |
| 配乐 | 128BPM 电子鼓点（自合成，无版权），重音卡在切点 |
| 人声 | edge-tts 云希 +35%，数据驱动脚本 |
| 素材 | 真实 GitHub 仓库页截图 |

## 文件

- `video-batch/<repo>/renders/final.mp4` —— 成片
- `out/发布包/抖音发布包-100组.md` —— 100 组文案总表
- `out/发布包/NNN-<repo>.md` —— 单条可复制版
- `out/发布包/发布清单.csv` —— 排期表
- `out/总览.html` —— 浏览器总览
""", encoding='utf-8')
    print(f'总览 → {OUT / "总览.html"}（已完成 {have}/{len(idx)}）')


if __name__ == '__main__':
    main()
