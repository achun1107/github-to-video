# -*- coding: utf-8 -*-
"""生成「手机发布包」：视频 + 纯文本文案成对，直接微信发手机、复制粘贴发抖音。

  python tools/build-mobile-pack.py

产出 00-交付-100条视频/手机发布包/
  ├── 001-Gathin23-cleanyourtv.mp4     ← 带配乐版（可直接发）
  ├── 001-Gathin23-cleanyourtv.txt     ← 文案，纯文本，手机上长按即可复制
  └── ...
以及
  全部文案-一次复制.txt    ← 100 条全在一起，方便挑
  手机上怎么看.html        ← 手机浏览器打开，带「一键复制」按钮
"""
import json
import os
import shutil
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent
BATCH = ROOT / 'video-batch'
DELIV = ROOT / '00-交付-100条视频'
PACK = DELIV / '手机发布包'


def hardlink_or_copy(src, dst):
    if dst.exists():
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def plain_text(p):
    """把发布包 md 压成手机友好的纯文本：标题 → 空行 → 正文 → 空行 → 话题"""
    txt = p.read_text(encoding='utf-8')
    def grab(head, stop=None):
        seg = txt.split(head)[1]
        if stop:
            seg = seg.split(stop)[0]
        return seg.strip()
    title = grab('## 标题', '## 副标题').split('\n')[0].strip()
    body = grab('## 正文', '## 话题')
    # 正文里去掉「———」分隔线以下的技术补充（手机上太长）
    if '———' in body:
        body = body.split('———')[0].strip()
    tags = grab('## 话题', '## 封面三行').split('\n')[0].strip()
    # 按句断行：抖音描述区支持换行，手机上更易读
    lines = [x.strip() for x in body.replace('。', '。\n').split('\n') if x.strip()]
    pretty = '\n'.join(lines)
    return f'{pretty}\n\n{tags}'


def main():
    idx = json.loads((BATCH / 'index.json').read_text(encoding='utf-8'))
    PACK.mkdir(parents=True, exist_ok=True)

    made, all_txt = 0, []
    for it in idx:
        n = it['i'] + 1
        d = it['dir']
        owner, name = it['repo'].split('/')
        base = f'{n:03d}-{owner}-{name}'

        video = BATCH / d / 'renders' / 'final.mp4'
        md = SRC / 'out' / '发布包' / f'{n:03d}-{d}.md'
        if not video.exists() or not md.exists():
            continue

        hardlink_or_copy(video, PACK / f'{base}.mp4')
        text = plain_text(md)
        (PACK / f'{base}.txt').write_text(text, encoding='utf-8')

        # 留白版也放，命名加 -留白版
        blank = BATCH / d / 'renders' / 'final-blank.mp4'
        if blank.exists():
            hardlink_or_copy(blank, PACK / f'{base}-留白版.mp4')

        all_txt.append(f'{base}\n{text}\n')
        made += 1

    header = (
        '100 条开源项目短片 · 全部文案\n'
        '用法：找到编号，全选该段文字 → 复制 → 粘到抖音描述框\n'
        '视频在「手机发布包」文件夹，文件名编号与本文件一一对应\n'
        + '=' * 40 + '\n\n'
    )
    (PACK / '全部文案-一次复制.txt').write_text(header + ('\n' + '-' * 40 + '\n\n').join(all_txt),
                                               encoding='utf-8')

    print(f'手机发布包 → {PACK}')
    print(f'  {made} 组（每组 mp4 + txt），留白版另放')


if __name__ == '__main__':
    main()
