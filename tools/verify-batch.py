# -*- coding: utf-8 -*-
"""100 条成片批量验收：规格 / 音频电平 / 素材真实性 / 文案完整度。

  python tools/verify-batch.py
"""
import json
import random
import subprocess
from pathlib import Path

import numpy as np

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'


def probe(f):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                          'stream=codec_type,codec_name,width,height,r_frame_rate:format=duration,size',
                          '-of', 'json', str(f)], capture_output=True, text=True)
    try:
        return json.loads(out.stdout or '{}')
    except Exception:
        return {'streams': [], 'format': {'duration': 0}}


def rms(f, a, b):
    p = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(a), '-to', str(b), '-i', str(f),
                        '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True)
    x = np.frombuffer(p.stdout, dtype=np.float32)
    return round(float(20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9)), 1) if len(x) else None


def main():
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    rows, bad = [], []
    for it in idx:
        proj = ROOT / it['dir']
        fin = proj / 'renders/final.mp4'
        rec = {'repo': it['repo'], 'dir': it['dir']}
        if not fin.exists():
            rec['status'] = 'MISSING'
            bad.append(rec)
            rows.append(rec)
            continue
        p = probe(fin)
        v = [s for s in p['streams'] if s.get('codec_type') == 'video'][0]
        a = [s for s in p['streams'] if s.get('codec_type') == 'audio']
        rec['size_mb'] = round(fin.stat().st_size / 1e6, 2)
        rec['dur'] = round(float(p['format']['duration']), 2)
        rec['wh'] = f"{v.get('width')}x{v.get('height')}"
        rec['fps'] = v.get('r_frame_rate')
        rec['audio'] = bool(a)
        rec['has_shot'] = (proj / 'assets/repo.png').exists()
        rec['has_vo'] = (proj / 'audio/vo1.mp3').exists()
        rec['copy'] = (SRC / 'out/发布包' / f'{it["i"]+1:03d}-{it["dir"]}.md').exists()
        ok = (rec['dur'] == 18.0 and rec['wh'] == '1080x1920' and rec['fps'] == '30/1'
              and rec['audio'] and rec['has_shot'] and rec['has_vo'] and rec['copy'])
        rec['status'] = 'OK' if ok else 'CHECK'
        if not ok:
            bad.append(rec)
        rows.append(rec)

    # 抽 10 条测电平
    random.seed(7)
    sample = random.sample([r for r in rows if r.get('status') == 'OK'], min(10, len([r for r in rows if r.get('status') == 'OK'])))
    lv = []
    for r in sample:
        f = ROOT / r['dir'] / 'renders/final.mp4'
        lv.append((r['dir'][:26], rms(f, 2, 4), rms(f, 0, 0.5)))

    total_mb = sum(r.get('size_mb', 0) for r in rows)
    lines = ['# 100 条成片验收报告', '', f'生成时间：2026-11-10', '',
             '## 总览', '',
             f'| 项 | 值 |', '|---|---|',
             f'| 目标条数 | 100 |',
             f'| 实际出片 | {sum(1 for r in rows if r.get("status")=="OK")} |',
             f'| 需复核 | {sum(1 for r in rows if r.get("status")=="CHECK")} |',
             f'| 缺失 | {sum(1 for r in rows if r.get("status")=="MISSING")} |',
             f'| 总大小 | {total_mb/1000:.2f} GB |', '',
             '## 抽检音频电平（10 条）', '',
             '| 片子 | 人声 2–4s | 纯音乐 0–0.5s | 差值 |', '|---|---|---|---|']
    for name, v, m in lv:
        lines.append(f'| {name} | {v} dB | {m} dB | {(v - m) if v and m else 0:.1f} dB |')
    lines += ['', '> 人声应比纯音乐高 3 dB 以上。', '',
              '## 逐条状态', '', '| # | 仓库 | 时长 | 画幅 | 音频 | 截图 | 配音 | 文案 | MB | 状态 |',
              '|---|---|---|---|---|---|---|---|---|---|']
    for i, r in enumerate(rows, 1):
        lines.append(f"| {i} | {r['repo']} | {r.get('dur','-')} | {r.get('wh','-')} | "
                     f"{'✓' if r.get('audio') else '✗'} | {'✓' if r.get('has_shot') else '✗'} | "
                     f"{'✓' if r.get('has_vo') else '✗'} | {'✓' if r.get('copy') else '✗'} | "
                     f"{r.get('size_mb','-')} | {r['status']} |")
    (SRC / 'out/验收报告-100条.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f"验收完成：OK={sum(1 for r in rows if r.get('status')=='OK')} "
          f"CHECK={sum(1 for r in rows if r.get('status')=='CHECK')} "
          f"MISSING={sum(1 for r in rows if r.get('status')=='MISSING')}  总 {total_mb/1000:.2f} GB")
    for name, v, m in lv[:5]:
        print(f'  {name:<28} 人声 {v} dB | 音乐 {m} dB')


if __name__ == '__main__':
    main()
