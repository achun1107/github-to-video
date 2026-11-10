# github-to-video

**把任意 GitHub 仓库变成一支能发的竖屏知识短片。**

输入一个仓库链接，输出一支 18 秒 · 1080×1920 · 带解说配音与卡点配乐的竖屏视频，
外加一套可直接粘贴的标题 / 正文 / 话题。

> repo → reel。开箱即用，无需剪辑软件。

---

## 它解决什么问题

做开源项目内容的人都有同一个困境：

- 项目更新快，一条条手剪根本追不上
- 截图、打码、配字幕、卡点配乐，每题 40 分钟起
- 批量做 100 条时，人已经不想活了

这套东西把流程压成**一条命令**。我给一个仓库链接，它给出：

| 产出 | 说明 |
|---|---|
| `renders/final.mp4` | 带自合成卡点配乐，无版权，直接能发 |
| `renders/final-blank.mp4` | 留白人声版，发布时挂平台曲库 BGM |
| `copy.md` | 标题 / 正文 / 话题 / 封面三行 |

---

## 快速开始

```bash
pip install playwright pillow numpy scipy pyyaml edge-tts
python -m playwright install chromium

git clone --depth 1 https://github.com/owner/repo _repos/repo
python tools/extract-content.mjs _repos/repo -o content.json
python tools/shot-github.py https://github.com/owner/repo -o assets/repo.png

node tools/make-video.mjs --repo https://github.com/owner/repo --out . --jobs 4
```

产出的 `renders/final.mp4` 就是成片。

---

## 一条片子的结构

| 时间 | 卡片 | 画面 |
|---|---|---|
| 0.15–1.15s | 双闪 | Star 数大字闪过 |
| 1.15–4.05s | 开场证据卡 | **真实 GitHub 仓库页截图** + 「★ Star 5.5w」白胶囊 |
| 4.05–8.30s | 数字卡 | Star / Fork / 上线日期 |
| 8.30–12.60s | 可用卡 | `git clone <url>` + 完全开源 / 本地可跑 / 随便改 |
| 12.60–18.0s | 结论卡 | 钩子 + 星数 + 语言 + 上线月份 + 仓库名 |

固定头部：钩子 + 副标题；卡内底部说明条，关键词上色。
版式常量集中在 `recipe.json`——换版式改参数，不动画面代码。

---

## 批量生产

```bash
python tools/batch-all.py --limit 100
```

从多维筛选（10 月至今 / 1000+ Star / AI·工具·语言·Web 4 个维度）到 100 条成片，
全流程幂等，断了可以续跑。

**实测成本**：单条约 87 秒，100 条约 2.4 小时，占用 0.5 GB。

---

## 关于配乐（重要）

平台规则：**站内曲库免授权，站外内嵌的爆火原曲属未授权**（会被限流/下架）。

所以每条片子出两个版本：

- `final.mp4` —— 自合成 128BPM 电子鼓点，无版权
- `final-blank.mp4` —— 只有人声，发布时在 App 里挂平台「品牌精选」曲库

---

## 验证

```bash
python tools/verify-batch.py    # 规格 / 电平 / 素材 / 文案
python tools/qc-frames.py       # 每条抽 4 帧查黑屏
python tools/make-player.py     # 生成本地播放器
```

---

## 目录

```
skills/github-to-video/SKILL.md   给 AI agent 用的完整说明
tools/                            流水线脚本（筛选 / 截图 / 配音 / 渲染 / 混音 / 文案）
engine/                           vk 渲染引擎（每帧是 t 的纯函数）
examples/samples/                 3 支样例成片
docs/pitfalls.md                  踩坑记录
```

---

## License

MIT。样例成片中的仓库截图版权归各仓库所有者，仅作演示用途。
