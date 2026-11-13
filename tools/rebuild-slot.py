# -*- coding: utf-8 -*-
"""把某些序号的风险仓库，换成安全候选，并重建该条。

  python tools/rebuild-slot.py --slot 7 --repo Motionsites-AI/claude-skill

做：删旧工程 → 建新工程（content/film/index）→ 补依赖 → 截图 → 配音 → 字幕 → 渲染 → 混音 → 留白版
"""
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'
sys.path.insert(0, str(SRC / 'tools'))

ns = {'__file__': str(SRC / 'tools/batch-make.py')}
exec((SRC / 'tools/batch-make.py').read_text(encoding='utf-8-sig').split('if __name__ ==')[0], ns)
build_content = ns['build_content']
pick_hook = ns['pick_hook']
slug = ns['slug']
human = ns['human']


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def main():
    a = sys.argv
    slot = int(a[a.index('--slot') + 1])
    repo = a[a.index('--repo') + 1]

    cand = json.loads((SRC / 'data/candidates.json').read_text(encoding='utf-8'))
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    rec = next((c for c in cand if c['full_name'] == repo), None)
    if not rec:
        sys.exit(f'候选里没有 {repo}')

    entry = next(e for e in idx if e['i'] == slot - 1)
    old_dir = ROOT / entry['dir']
    d = build_content(rec)
    new_dir_name = slug(rec['full_name'])
    proj = ROOT / new_dir_name

    print(f'[{slot:03d}] {entry["repo"]}  ->  {rec["full_name"]}')
    if old_dir.exists() and old_dir != proj:
        shutil.rmtree(old_dir, ignore_errors=True)
    proj.mkdir(parents=True, exist_ok=True)

    # content
    (proj / 'content.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    (proj / 'content.js').write_text('window.CONTENT = ' + json.dumps(d, ensure_ascii=False, indent=2) + ';\n',
                                     encoding='utf-8')

    # film.js 从模板生成
    hook, sub = pick_hook(d)
    days = (date(2026, 11, 10) - date(*[int(x) for x in rec['created'].split('-')])).days
    tpl = (SRC / 'tools/film-batch.js').read_text(encoding='utf-8')

    def jsq(t):
        return (t or '').replace('\\', '\\\\').replace("'", "\\'").replace('\n', ' ')

    film = (tpl.replace('__HOOK__', jsq(hook))
               .replace('__SUB__', jsq(sub))
               .replace('__STAR__', d['starHuman'])
               .replace('__FORKS__', d['forkHuman'])
               .replace('__NAME__', jsq(d['name']))
               .replace('__OWNER__', jsq(d['owner']))
               .replace('__LANG__', jsq(d['lang'] or 'Multi'))
               .replace('__CREATED__', d['created'])
               .replace('__DESC__', jsq(d['desc']))
               .replace('__TOPICS__', json.dumps(d['topics'], ensure_ascii=False))
               .replace('__DAYS__', str(days)))
    (proj / 'film.js').write_text(film, encoding='utf-8')

    # 依赖
    for f in ('index.html', 'recipe.js'):
        shutil.copy(SRC / f, proj / f)
    if not (proj / 'engine').exists():
        import os
        try:
            (proj / 'engine').symlink_to(SRC / 'engine', target_is_directory=True)
        except OSError:
            shutil.copytree(SRC / 'engine', proj / 'engine', dirs_exist_ok=True)
    for sub_dir in ('assets', 'audio', 'audio/bgm', 'renders'):
        (proj / sub_dir).mkdir(parents=True, exist_ok=True)
    for f in ('score.wav',):
        src_f = SRC / 'audio' / f
        if src_f.exists() and not (proj / 'audio' / f).exists():
            shutil.copy(src_f, proj / 'audio' / f)
    bed = SRC / 'audio/bgm/edm-cut.wav'
    dst_bed = proj / 'audio/bgm/edm-cut.wav'
    if bed.exists() and not dst_bed.exists():
        shutil.copy(bed, dst_bed)

    # 截图
    print('  截图…')
    r = run([sys.executable, str(SRC / 'tools/shot-github.py'), ('https://github.com/' + rec['full_name']),
             '-o', str(proj / 'assets/repo.png')], SRC / 'tools')
    if r.returncode:
        print('   截图失败:', (r.stderr or '')[-120:])

    # 配音（单条，走 batch-tts3 的逻辑）
    print('  配音…')
    tn = {'__file__': str(SRC / 'tools/batch-tts3.py')}
    exec((SRC / 'tools/batch-tts3.py').read_text(encoding='utf-8-sig').split('if __name__ ==')[0], tn)
    ok = tn['do']({'repo': rec['full_name'], 'dir': new_dir_name,
                   'hook': hook, 'sub': sub, 'i': slot - 1, 'stars': rec['stars']})
    print('   ', ok)

    # 字幕
    sn = {'__file__': str(SRC / 'tools/gen-vo-subs.py')}
    exec((SRC / 'tools/gen-vo-subs.py').read_text(encoding='utf-8-sig').split('if __name__ ==')[0], sn)
    subs = sn['parse_srt'](proj / 'audio/vo1.srt')
    (proj / 'vo-subs.js').write_text(
        'window.VO_SUBS = ' + json.dumps(subs, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
    print(f'    字幕 {len(subs)} 句')

    # 渲染 + 混音
    print('  渲染…')
    r = run([sys.executable, 'engine/render.py', '.'], proj)
    if r.returncode:
        sys.exit('渲染失败: ' + (r.stderr or '')[-300:])
    print('  混音…')
    r = run([sys.executable, str(SRC / 'tools/mix-batch.py'), '.'], proj)
    if r.returncode:
        sys.exit('混音失败: ' + (r.stderr or '')[-300:])

    # 留白版
    print('  留白版…')
    bn = {'__file__': str(SRC / 'tools/make-blanktrack.py')}
    exec((SRC / 'tools/make-blanktrack.py').read_text(encoding='utf-8-sig').split('if __name__ ==')[0], bn)
    bn['do']({'repo': rec['full_name'], 'dir': new_dir_name})

    # 更新 index.json
    entry.update({
        'repo': rec['full_name'], 'stars': rec['stars'], 'dir': new_dir_name,
        'hook': hook, 'sub': sub, 'title': hook + '｜' + d['name'],
    })
    (ROOT / 'index.json').write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'  完成 → {proj}')


if __name__ == '__main__':
    main()
