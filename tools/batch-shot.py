# -*- coding: utf-8 -*-
"""批量截图：用 Playwright 拍每个仓库的 GitHub 页 → assets/repo.png

  python tools/batch-shot.py --limit 100 [--workers 3]

用匿名 GitHub 渲染，不需要 API key；每个约 6 秒，3 并发。
"""
import json
import sys
import subprocess
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ROOT = SRC.parent / 'video-batch'


def main():
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 100
    idx = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    todo = []
    for item in idx[:limit]:
        proj = ROOT / item['dir']
        out = proj / 'assets' / 'repo.png'
        if not out.exists():
            todo.append((item['repo'], proj))
    print(f'待截图 {len(todo)} 个（已有 {(out := 0) or sum(1 for i in idx[:limit] if (ROOT / i["dir"] / "assets/repo.png").exists())} 个）')

    shot = SRC / 'tools/shot-github.py'
    script = f'''
import sys
sys.path.insert(0, r"{SRC / 'tools'}")
from pathlib import Path
from playwright.sync_api import sync_playwright
pairs = {[(r, str(p / 'assets/repo.png')) for r, p in todo]!r}
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", args=["--force-color-profile=srgb","--hide-scrollbars"])
    pg = b.new_page(viewport={{"width": 1280, "height": 1000}}, device_scale_factor=2)
    for repo, out in pairs:
        try:
            pg.goto(f"https://github.com/{{repo}}", wait_until="domcontentloaded", timeout=45000)
            pg.wait_for_timeout(2200)
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            pg.screenshot(path=out)
            print("ok", repo, flush=True)
        except Exception as e:
            print("fail", repo, type(e).__name__, flush=True)
    b.close()
'''
    proc = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
    ok = proc.stdout.count('ok ')
    print(f'\n完成 {ok}/{len(todo)}')
    if proc.returncode:
        print(proc.stderr[-800:])


if __name__ == '__main__':
    main()
