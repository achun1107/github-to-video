# 依赖

```bash
# Python
python -m pip install playwright pillow numpy scipy pyyaml edge-tts

# Playwright 浏览器（截图 + 逐帧渲染都要用）
python -m playwright install chromium

# 字体（43MB 中文字体，不入仓库，首次运行下载）
python engine/get_fonts.py
```

## 可选

- **ffmpeg**：混音、编码、抽帧全部依赖它。确认在 PATH 里：
  ```bash
  ffmpeg -version
  ```
  Windows 可用 `winget install ffmpeg`，macOS `brew install ffmpeg`。

- **Node.js 18+**：`make-video.mjs` / `extract-content.mjs` / `recipe.mjs` 需要。

## 系统要求

| 项 | 要求 |
|---|---|
| 系统 | Windows / macOS / Linux |
| 内存 | 渲染时约 1.5 GB（并行 `--jobs 4` 时约 4 GB） |
| 磁盘 | 单条约 3 MB，100 条约 0.5 GB |
| 网络 | 截图与配音需要外网（GitHub / edge-tts） |
