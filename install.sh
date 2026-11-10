#!/usr/bin/env bash
# 一键装环境
set -e

echo "==> 检查 ffmpeg"
command -v ffmpeg >/dev/null || { echo "缺 ffmpeg，请先安装（winget install ffmpeg / brew install ffmpeg）"; exit 1; }

echo "==> 检查 node"
command -v node >/dev/null || { echo "缺 Node.js 18+"; exit 1; }

echo "==> 安装 Python 依赖"
python -m pip install --quiet playwright pillow numpy scipy pyyaml edge-tts

echo "==> 安装 Playwright Chromium"
python -m playwright install chromium

echo "==> 下载中文字体（约 43MB）"
python engine/get_fonts.py

echo
echo "装好了。试跑一条："
echo "  python tools/shot-github.py https://github.com/owner/repo -o assets/repo.png"
echo "  node tools/make-video.mjs --repo https://github.com/owner/repo --out . --jobs 4"
