# -*- coding: utf-8 -*-
"""把所有产物收进一个显眼的交付目录：00-交付-100条视频/

  python tools/build-delivery.py

做的事：
  1. 建 00-交付-100条视频/（放在 achun 根目录，一眼能看到）
  2. 200 个 mp4 用硬链接放进去（同一磁盘不占额外空间），文件名可读
  3. 播放器/总览/文案/清单一起搬进去，路径改成相对本目录
  4. 生成「▶ 双击这里打开播放器.bat」和「说明-先看这个.md」
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent          # video-goofish/
ROOT = SRC.parent                                      # achun/
BATCH = ROOT / 'video-batch'
OUT = ROOT / '00-交付-100条视频'


def hardlink_or_copy(src, dst):
    if dst.exists():
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def adur(p):
    o = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=nw=1:nk=1', str(p)], capture_output=True, text=True)
    try:
        return round(float(o.stdout.strip()), 2)
    except ValueError:
        return 0.0


def main():
    idx = json.loads((BATCH / 'index.json').read_text(encoding='utf-8'))
    (OUT / 'videos').mkdir(parents=True, exist_ok=True)
    (OUT / '文案').mkdir(parents=True, exist_ok=True)

    items = []
    for it in idx:
        n = it['i'] + 1
        d = it['dir']
        name = it['repo'].split('/')[-1]
        owner = it['repo'].split('/')[0]
        base = f"{n:03d}-{owner}-{name}"
        a = BATCH / d / 'renders' / 'final.mp4'
        b = BATCH / d / 'renders' / 'final-blank.mp4'
        if not a.exists():
            continue
        hardlink_or_copy(a, OUT / 'videos' / f'{base}-带配乐.mp4')
        if b.exists():
            hardlink_or_copy(b, OUT / 'videos' / f'{base}-留白版.mp4')

        md_src = SRC / 'out' / '发布包' / f'{n:03d}-{d}.md'
        copy_text = ''
        if md_src.exists():
            shutil.copy2(md_src, OUT / '文案' / f'{n:03d}-{name}.md')
            copy_text = md_src.read_text(encoding='utf-8')

        c = json.loads((BATCH / d / 'content.json').read_text(encoding='utf-8'))
        items.append({
            'n': n, 'repo': it['repo'], 'stars': it['stars'], 'title': it['hook'],
            'file': f'videos/{base}-带配乐.mp4',
            'blank': f'videos/{base}-留白版.mp4',
            'copy': f'文案/{n:03d}-{name}.md',
            'copyText': copy_text,
            'url': c['url'],
            'voice': adur(BATCH / d / 'audio' / 'vo1.mp3'),
            'video': 18.0,
            'size': round(a.stat().st_size / 1e6, 1),
        })

    (OUT / 'items.json').write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')

    html = '''<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><title>100 条开源项目短片</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0b0b0d;color:#e9e9ee;
font:14px/1.6 system-ui,"Noto Sans SC",sans-serif;display:flex;height:100vh;overflow:hidden}
#list{width:360px;overflow-y:auto;border-right:1px solid #22222a;background:#101014;flex:none}
.hdr{padding:14px 16px 10px;position:sticky;top:0;background:#101014;border-bottom:1px solid #22222a;z-index:2}
.hdr b{font-size:15px}.hdr .s{color:#8a8a93;font-size:12px;margin-top:4px}
.row{padding:9px 14px;border-bottom:1px solid #191920;cursor:pointer;display:flex;gap:10px}
.row:hover{background:#17171e}.row.on{background:#1e1e28;box-shadow:inset 3px 0 0 #e8613c}
.no{color:#6a6a75;font:600 11px/1 ui-monospace,monospace;min-width:26px}
.t{font-size:12.5px;line-height:1.35}.m{color:#7c7c88;font-size:11px;margin-top:2px}
#stage{flex:1;display:flex;flex-direction:column;padding:20px 24px;min-width:0}
#title{font-size:18px;font-weight:700}#meta{color:#8a8a93;font-size:12px;margin-top:6px}
#meta a{color:#5fa8b2;text-decoration:none}
#videoWrap{flex:1;display:flex;justify-content:center;align-items:center;min-height:0}
video{max-height:100%;max-width:100%;border-radius:14px;background:#000;box-shadow:0 18px 60px rgba(0,0,0,.6)}
#bar{display:flex;gap:10px;justify-content:center;padding:12px 0 4px;flex-wrap:wrap}
button{background:#1d1d26;color:#dcdce4;border:1px solid #2f2f3b;border-radius:9px;padding:8px 16px;
font-size:13px;cursor:pointer}button:hover{background:#262633}
button.pri{background:#e8613c;border-color:#e8613c;color:#fff;font-weight:600}
button.on{background:#5fa8b2;border-color:#5fa8b2;color:#04202a;font-weight:600}
.vbadge{padding:1px 7px;border-radius:9px;font-size:10.5px;font-family:ui-monospace,monospace}
.vok{background:rgba(91,224,106,.14);color:#5be06a;border:1px solid rgba(91,224,106,.35)}
#copy{position:absolute;inset:0;background:rgba(6,6,8,.95);padding:34px 60px;overflow:auto;display:none;z-index:9}
#copy pre{white-space:pre-wrap;font:13px/1.8 ui-monospace,"Noto Sans SC",monospace;color:#d8d8e0}
#copy .x{position:fixed;right:26px;top:20px;font-size:26px;cursor:pointer;color:#8a8a93}
</style></head><body>
<div id="list"><div class="hdr"><b>100 条开源项目短片</b>
<div class="s" id="stat">点击左侧播放 · 可切留白版 · 可看文案</div></div><div id="rows"></div></div>
<div id="stage">
  <div><div id="title">选一条开始播放</div><div id="meta"></div></div>
  <div id="videoWrap"><video id="v" controls playsinline preload="metadata"></video></div>
  <div id="bar">
    <button id="prev">← 上一条</button><button id="play" class="pri">播放 / 暂停</button>
    <button id="next">下一条 →</button><button id="mode" class="on">带配乐版</button>
    <button id="copyshow">看文案</button>
  </div>
</div>
<div id="copy"><span class="x" id="copyclose">✕</span><pre id="copytext"></pre></div>
<script>
const ITEMS = __DATA__;
let cur=0, blank=false;
const rows=document.getElementById('rows'), v=document.getElementById('v');
const titleEl=document.getElementById('title'), metaEl=document.getElementById('meta');
ITEMS.forEach((it,i)=>{
  const d=document.createElement('div'); d.className='row';
  const ok = it.voice>=15.5 && it.voice<=18.6;
  d.innerHTML=`<span class="no">${String(it.n).padStart(3,'0')}</span>
  <span style="flex:1"><span class="t">${it.title}</span>
  <span class="m">${it.stars}★ · ${it.repo}
  <span class="vbadge vok">🔊 ${it.voice.toFixed(1)}s</span></span></span>`;
  d.onclick=()=>show(i); rows.appendChild(d);
});
function show(i){
  cur=(i+ITEMS.length)%ITEMS.length; const it=ITEMS[cur];
  v.src = blank?it.blank:it.file; v.load();
  titleEl.textContent=it.title;
  metaEl.innerHTML=`${it.repo} · ${it.stars}★ · <span class="vbadge vok">🔊 ${it.voice.toFixed(2)}s / 片长 ${it.video}s</span> · <a href="${it.url}" target="_blank">${it.url}</a>`;
  [...rows.children].forEach((r,k)=>r.classList.toggle('on',k===cur));
  rows.children[cur].scrollIntoView({block:'nearest'});
}
v.onended=()=>show(cur+1);
document.getElementById('prev').onclick=()=>show(cur-1);
document.getElementById('next').onclick=()=>show(cur+1);
document.getElementById('play').onclick=()=>v.paused?v.play():v.pause();
document.getElementById('mode').onclick=e=>{blank=!blank;
  e.target.textContent=blank?'留白版（挂站内BGM）':'带配乐版';
  e.target.classList.toggle('on',!blank); show(cur);};
document.getElementById('copyshow').onclick=()=>{
  document.getElementById('copytext').textContent = ITEMS[cur].copyText || '（无文案）';
  document.getElementById('copy').style.display='block';};
document.getElementById('copyclose').onclick=()=>document.getElementById('copy').style.display='none';
document.addEventListener('keydown',e=>{
  if(e.code==='Space'){e.preventDefault();v.paused?v.play():v.pause();}
  if(e.code==='ArrowLeft')show(cur-1); if(e.code==='ArrowRight')show(cur+1);
  if(e.code==='Escape')document.getElementById('copy').style.display='none';});
document.getElementById('stat').textContent=`共 ${ITEMS.length} 条 · 点击左侧播放 · 可切留白版 · 可看文案`;
show(0);
</script></body></html>'''

    (OUT / '▶ 播放器.html').write_text(html.replace('__DATA__', json.dumps(items, ensure_ascii=False)),
                                       encoding='utf-8')

    # 一键打开
    (OUT / '▶ 双击这里打开播放器.bat').write_text(
        '@echo off\r\nchcp 65001 >nul\r\ncd /d "%~dp0"\r\n'
        'start "" "▶ 播放器.html"\r\n', encoding='utf-8')

    # 清单 CSV
    import csv
    with open(OUT / '视频清单.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(['序号', '仓库', '星数', '标题', '带配乐版', '留白版', '文案', '网址', '配音时长'])
        for i in items:
            w.writerow([i['n'], i['repo'], i['stars'], i['title'],
                        i['file'], i['blank'], i['copy'], i['url'], i['voice']])

    print(f'交付目录 → {OUT}')
    print(f'  视频 {len(items)*2} 个（硬链接，不占额外空间）')
    print(f'  文案 {len(list((OUT / "文案").glob("*.md")))} 个')


if __name__ == '__main__':
    main()
