# -*- coding: utf-8 -*-
"""生成可直接播放的本地播放器（100 条连播 + 单条点播）。

  python tools/make-player.py

产出 out/播放器.html：
  - 点任意缩略图 → 右侧大屏播放该条
  - 空格播放/暂停、←/→ 上一条/下一条、Esc 回到列表
  - 可切换「带配乐版 / 留白版」
  - 双击文件名用系统播放器打开
"""
import json
import subprocess
from pathlib import Path

def adur(p):
    """读音频时长（秒），读不到返回 0"""
    o = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=nw=1:nk=1', str(p)], capture_output=True, text=True)
    try:
        return round(float(o.stdout.strip()), 2)
    except ValueError:
        return 0.0

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'
OUT = SRC / 'out'


def main():
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    packs = OUT / '发布包'

    items = []
    for it in idx:
        d = it['dir']
        c = json.loads((ROOT / d / 'content.json').read_text(encoding='utf-8'))
        md = packs / f"{it['i']+1:03d}-{d}.md"
        title = it['hook']
        if md.exists():
            txt = md.read_text(encoding='utf-8')
            if '## 标题' in txt:
                title = txt.split('## 标题')[1].strip().split('\n')[0] or title
        items.append({
            'n': it['i'] + 1,
            'repo': it['repo'],
            'stars': it['stars'],
            'title': title,
            'hook': it['hook'],
            'file': f'../../video-batch/{d}/renders/final.mp4',
            'blank': f'../../video-batch/{d}/renders/final-blank.mp4',
            'shot': f'../../video-batch/{d}/assets/repo.png',
            'copy': f'发布包/{it["i"]+1:03d}-{d}.md',
            'url': c['url'],
            'voice': adur(ROOT / d / 'audio/vo1.mp3'),
            'video': 18.0,
        })

    html = '''<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>100 条开源项目短片 · 播放器</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#0b0b0d;color:#e9e9ee;font:14px/1.6 system-ui,"Noto Sans SC",sans-serif;
     display:flex;height:100vh;overflow:hidden}
#list{width:340px;overflow-y:auto;border-right:1px solid #22222a;background:#101014;flex:none}
#list .hdr{padding:14px 16px 10px;position:sticky;top:0;background:#101014;border-bottom:1px solid #22222a;z-index:2}
#list .hdr b{font-size:15px}
#list .hdr .s{color:#8a8a93;font-size:12px;margin-top:4px}
.row{padding:9px 14px;border-bottom:1px solid #191920;cursor:pointer;display:flex;gap:10px;align-items:center}
.row:hover{background:#17171e}
.row.on{background:#1e1e28;box-shadow:inset 3px 0 0 #e8613c}
.row .no{color:#6a6a75;font:600 11px/1 ui-monospace,monospace;min-width:26px}
.row .t{font-size:12.5px;line-height:1.35}
.row .m{color:#7c7c88;font-size:11px;margin-top:2px}
#stage{flex:1;display:flex;flex-direction:column;padding:20px 24px;min-width:0}
#top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:12px}
#title{font-size:18px;font-weight:700;line-height:1.4}
#meta{color:#8a8a93;font-size:12px;margin-top:6px}
#meta a{color:#5fa8b2;text-decoration:none}
#videoWrap{flex:1;display:flex;justify-content:center;align-items:center;min-height:0}
video{max-height:100%;max-width:100%;border-radius:14px;background:#000;
      box-shadow:0 18px 60px rgba(0,0,0,.6)}
#bar{display:flex;gap:10px;align-items:center;justify-content:center;padding:12px 0 4px;flex-wrap:wrap}
button{background:#1d1d26;color:#dcdce4;border:1px solid #2f2f3b;border-radius:9px;
       padding:8px 16px;font-size:13px;cursor:pointer}
button:hover{background:#262633}
button.pri{background:#e8613c;border-color:#e8613c;color:#fff;font-weight:600}
button.on{background:#5fa8b2;border-color:#5fa8b2;color:#04202a;font-weight:600}
#tip{color:#6a6a75;font-size:12px;text-align:center;padding-bottom:6px}
#copy{position:absolute;inset:0;background:rgba(6,6,8,.94);padding:34px 60px;overflow:auto;
      display:none;z-index:9}
#copy pre{white-space:pre-wrap;font:13px/1.8 ui-monospace,"Noto Sans SC",monospace;color:#d8d8e0}
#copy .x{position:fixed;right:26px;top:20px;font-size:26px;cursor:pointer;color:#8a8a93}
</style></head><body>

<div id="list">
  <div class="hdr">
    <b>100 条开源项目短片</b>
    <div class="s" id="stat">2026-10 至今 · 1000+ Star · 点击左侧任意一条播放</div>
  </div>
  <div id="rows"></div>
</div>

<div id="stage">
  <div id="top">
    <div>
      <div id="title">选一条开始播放</div>
      <div id="meta"></div>
    </div>
  </div>
  <div id="videoWrap">
    <video id="v" controls playsinline preload="metadata"></video>
  </div>
  <div id="bar">
    <button id="prev">← 上一条</button>
    <button id="play" class="pri">播放 / 暂停</button>
    <button id="next">下一条 →</button>
    <button id="mode" class="on">带配乐版</button>
    <button id="copyshow">看文案</button>
  </div>
  <div id="tip">空格 播放/暂停 · ← → 上/下一条 · Esc 关闭文案</div>
</div>

<div id="copy"><span class="x" id="copyclose">✕</span><pre id="copytext"></pre></div>

<script>
const ITEMS = __DATA__;
let cur = 0, blank = false;
const rows = document.getElementById('rows');
const v = document.getElementById('v');
const titleEl = document.getElementById('title');
const metaEl = document.getElementById('meta');

ITEMS.forEach((it, i) => {
  const div = document.createElement('div');
  div.className = 'row';
  div.dataset.i = i;
  const vok = it.voice >= 15.5 && it.voice <= 18.6;
  const vtxt = it.voice ? it.voice.toFixed(1) + 's' : '无配音';
  div.innerHTML = `<span class="no">${String(it.n).padStart(3,'0')}</span>
    <span style="flex:1"><span class="t">${it.title}</span>
      <span class="m">${it.stars}★ · ${it.repo}
        <span class="vbadge ${vok ? 'vok' : 'vbad'}">🔊 ${vtxt}</span></span></span>`;
  div.onclick = () => show(i);
  rows.appendChild(div);
});

function show(i) {
  cur = (i + ITEMS.length) % ITEMS.length;
  const it = ITEMS[cur];
  v.src = blank ? it.blank : it.file;
  v.load();
  titleEl.textContent = it.title;
  const vok = it.voice >= 15.5 && it.voice <= 18.6;
  metaEl.innerHTML = `${it.repo} · ${it.stars}★ · `
    + `<span class="vbadge ${vok ? 'vok' : 'vbad'}">🔊 配音 ${it.voice ? it.voice.toFixed(2) + 's' : '缺失'}`
    + ` / 片长 ${it.video}s</span> · <a href="${it.url}" target="_blank">${it.url}</a>`;
  [...rows.children].forEach((r, k) => r.classList.toggle('on', k === cur));
  rows.children[cur].scrollIntoView({block:'nearest'});
}

v.onended = () => show(cur + 1);
document.getElementById('prev').onclick = () => show(cur - 1);
document.getElementById('next').onclick = () => show(cur + 1);
document.getElementById('play').onclick = () => v.paused ? v.play() : v.pause();
document.getElementById('mode').onclick = e => {
  blank = !blank;
  e.target.textContent = blank ? '留白版（挂站内BGM）' : '带配乐版';
  e.target.classList.toggle('on', !blank);
  show(cur);
};
document.getElementById('copyshow').onclick = () => {
  const it = ITEMS[cur];
  fetch(it.copy).then(r => r.ok ? r.text() : '（文案文件读不到，可能被移动）')
    .then(t => { document.getElementById('copytext').textContent = t;
                 document.getElementById('copy').style.display = 'block'; })
    .catch(() => { document.getElementById('copytext').textContent = '读取失败'; });
};
document.getElementById('copyclose').onclick = () =>
  document.getElementById('copy').style.display = 'none';

document.addEventListener('keydown', e => {
  if (e.code === 'Space') { e.preventDefault(); v.paused ? v.play() : v.pause(); }
  if (e.code === 'ArrowLeft') show(cur - 1);
  if (e.code === 'ArrowRight') show(cur + 1);
  if (e.code === 'Escape') document.getElementById('copy').style.display = 'none';
});

// 汇总配音合格率
(() => {
  const bad = ITEMS.filter(x => !(x.voice >= 15.5 && x.voice <= 18.6)).length;
  const el = document.getElementById('stat');
  const base = '2026-10 至今 · 1000+ Star · 点击左侧任意一条播放';
  el.innerHTML = base + `　｜　配音合格 <b style="color:#5be06a">${ITEMS.length - bad}</b>/${ITEMS.length}`
    + (bad ? `　<b style="color:#ff8b6a">${bad} 条待修</b>` : '');
})();

show(0);
</script>
</body></html>'''

    (OUT / '播放器.html').write_text(html.replace('__DATA__', json.dumps(items, ensure_ascii=False)),
                                      encoding='utf-8')
    print(f'播放器 → {OUT / "播放器.html"}（{len(items)} 条）')


if __name__ == '__main__':
    main()
