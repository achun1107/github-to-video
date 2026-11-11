---
name: github-to-video
description: |
  把一个 GitHub 仓库变成一支能发的竖屏知识短片（标题、文案、话题一起出）。
  输入仓库 URL、用户名/仓库名，或一批仓库清单；输出 18 秒 1080×1920 竖屏视频 + 抖音/小红书/B站发布包。
  触发场景：想把开源项目做成短视频、要用 GitHub 项目日更、要批量生产开源项目介绍视频、
  想知道「GitHub 项目怎么做成抖音视频」、要复刻某支知识类短视频的版式。
  关键词：github to video / 开源项目短视频 / repo 转视频 / 批量做开源视频 / 抖音知识类视频 / 短视频自动生成
metadata:
  author: achun
  version: "1.0.0"
  license: MIT
---

# github-to-video — 仓库链接 → 竖屏知识短片

把一个 GitHub 仓库，变成一支 18 秒、1080×1920、带解说配音与卡点配乐的竖屏短片，
外加一套可发布的标题 / 正文 / 话题。

---

## 一、这套东西能做什么

| 输入 | 输出 |
|---|---|
| `https://github.com/owner/repo` | `renders/final.mp4`（带配乐）+ `renders/final-blank.mp4`（留白，挂平台曲库） |
| 一批仓库（JSON 或候选清单） | N 条成片 + N 组文案 + 总览页 + 播放器 |

每条片子的结构（4 张卡，18 秒）：

1. **开场证据卡** —— 真实 GitHub 仓库页截图 + 「★ Star 5.5w」白胶囊
2. **数字卡** —— Star / Fork / 上线日期 三个真实数字
3. **可用卡** —— `git clone <url>` 命令 + 完全开源/本地可跑/随便改
4. **结论卡** —— 钩子 + 星数 + 语言 + 上线月份 + 仓库名

画面是 **t 的纯函数**（可任意 seek、可乱序渲染），确定性可校验。

---

## 二、最快跑通一条（5 分钟）

```bash
# 0. 装依赖
python -m pip install playwright pillow numpy scipy pyyaml edge-tts
python -m playwright install chromium

# 1. 拉仓库
git clone --depth 1 https://github.com/<owner>/<repo> _repos/<repo>

# 2. 抽内容 + 截仓库页
python tools/extract-content.mjs _repos/<repo> -o content.json
python tools/shot-github.py https://github.com/<owner>/<repo> -o assets/repo.png

# 3. 一键出片
node tools/make-video.mjs --repo https://github.com/<owner>/<repo> --out . --jobs 4
```

> 字体：`engine/fonts/` 需要 43MB 中文字体，仓库不带，首次运行 `python engine/get_fonts.py` 自动下载。

---

## 三、批量跑 100 条

```bash
python tools/batch-all.py --limit 100
```

8 步全自动、每步幂等（断了可续跑）：

| 步骤 | 脚本 | 做什么 |
|---|---|---|
| 1 | `harvest.py` | 多维筛选候选仓库 |
| 2 | `batch-build.py` | 建工程（content + film.js + 文案骨架） |
| 3 | `batch-deps.py` | 补 engine / recipe / assets / BGM |
| 4 | `batch-shot.py` | 截 GitHub 仓库页（Playwright） |
| 5 | `batch-tts2.py` | 合成配音（edge-tts） |
| 6 | `batch-render.py` | 渲染 + 混音 |
| 7 | `batch-copy.py` | 生成发布包（标题/正文/话题/封面） |
| 8 | `make-gallery.py` | 总览页 + 验收报告 |

---

## 四、筛选候选（运营视角）

```bash
python tools/harvest.py --min-stars 1000 --since 2026-10-01
```

硬门槛 `created:>2026-10-01 stars:>1000`，再按 5 个维度拆分：

- **热度**：不限话题
- **AI**：`topic:ai` / `topic:llm` / `topic:agent`
- **语言**：`language:Chinese` / `Python` / `TypeScript`
- **工具**：`topic:cli` / `topic:developer-tools`
- **Web**：`topic:web`

> ⚠️ GitHub Search **不支持** `a OR b` 混在 qualifier 里（会返回 422），必须拆成多次独立查询。

打分 = `stars + 维度覆盖数 × 800`，取前 N。

---

## 五、配音

```bash
python tools/batch-tts3.py --limit 100 --workers 5   # 推荐（自动校准时长）
python tools/batch-tts.py  --limit 100                # 旧版（文案偏短，会留静音）
```

- 音色 `zh-CN-YunxiNeural`，起始 `--rate=+30% --pitch=+5Hz`
- 文案模板（4 句、约 130 字，数据驱动、不编造）：

  ```
  「<钩子>。<副标题>。
    <仓库名>，GitHub 上 <星数> 个 Star，<Fork> 个 Fork，<月> 月 <日> 号才上线。
    它是 <语言> 写的，不是概念，是 clone 下来就能跑的仓库。
    现在完全开源、本地就能部署，代码随便改。仓库名 <名>，GitHub 搜得到。」
  ```

> **关键约束**：配音时长必须覆盖片子时长（18 秒）。
>
> | 文案 | 时长 | 结果 |
> |---|---|---|
> | ~90 字（v1） | 9.1 秒 | ❌ 第 10 秒起完全无人声 |
> | ~180 字（v2） | 21–24 秒 | ❌ 超出画面，混音被截断 |
> | **~130 字（v3）** | **17.2–18.5 秒** | ✅ 实测 100/100 覆盖全片 |
>
> `batch-tts3.py` 会先合成一次，再按实测时长自动调 rate（超长 +2~60%，偏短降到 +18%），
> 保证每条贴在 17 秒左右。**跑完务必用 `check-voice.py` 复核**。

```bash
python tools/check-voice.py     # 把 18 秒切 9 段，任一段 < -30dB 即判断档
```

---

## 五之二、文案必须与解说同源（否则会「不对版」）

**踩过的坑**：`batch-copy.py` 和 TTS 是两套独立逻辑——

| 项 | 解说（观众听到） | 旧文案（发出去） |
|---|---|---|
| 标题 | 手机界最省的优化工具来了 | 5.5w★ 的开源神作：cleanyourtv |
| 数字 | 5.5 万 Star | 5.5w |
| 有而对方无 | 「不是概念，是 clone 下来就能跑的仓库」 | 「原文简介：…」「想看我拆哪一类…」 |

同一条视频两套话术，观众听着 A 看着 B。

**解法**：以 `vo1.srt`（配音字幕）为**唯一事实源**，反推文案。

```bash
python tools/copy-from-voice.py --limit 100   # 生成「解说即文案」的发布包
python tools/check-copy-sync.py               # 校验标题/副标题/正文与 srt 完全一致
```

规则：
- 标题 = 解说第 1 句（去句号）
- 副标题 = 解说第 2 句
- 正文 = **解说全文**（原样，不重写）+ 分隔线 + 补充信息
- 封面 = 标题 / 星数与月份 / 仓库名

校验输出 `解说/文案一致：100/100` 才算过。

---

## 六、配乐（两套，按平台规则选）

| 版本 | 文件 | 用途 |
|---|---|---|
| 带配乐 | `renders/final.mp4` | 自合成 128BPM 电子鼓点，**无版权**，可直接发 |
| 留白 | `renders/final-blank.mp4` | 只有人声，音乐轨 −180dB，发布时挂平台曲库 |

```bash
python tools/make-edm.py audio/bgm/edm-cut.wav --bpm 128 --dur 18 --at 1.15
python tools/make-blanktrack.py --workers 8
```

**为什么要留白版**：抖音星图官方规则——只有站内「品牌精选」曲库免授权，站外内嵌火爆原曲属未授权，发布后有下架限流风险。
留白版让用户在 App 里挂曲，既用上平台热门 BGM，又不侵权。

配乐卡点：`offset = 首个镜头时刻 % 拍长`，保证重音落在切点上。

---

## 七、混音（别用 loudnorm）

```bash
python tools/mix-batch.py <工程目录>
```

三层电平：人声 +10dB（110–4500Hz 带通）｜BGM 0.20｜音效 0.07。
人声做侧链源压 BGM（`threshold 0.010 / ratio 12 / attack 4 / release 320`）。

> **坑**：`loudnorm` 会**重新平衡各层**，把刚调好的人声/音乐比例拉回去。
> 改成固定增益 + `alimiter` 峰值限制后才稳定。

实测目标：人声比纯音乐段高 **4–6 dB**。可用 `tools/levels2.py` 分频测量核对。

---

## 八、验收

```bash
python tools/verify-batch.py      # 规格 / 电平 / 素材 / 文案完整性
python tools/qc-frames.py         # 每条抽 4 帧，查黑屏与空卡
python tools/verify-candidates.py # 回查 GitHub 确认 created/star 合规
python tools/make-player.py       # 生成本地播放器（可点播、连播、看文案）
```

全部通过的标准：`OK=N / CHECK=0`，画面质检 `N/N`。

---

## 九、常见坑（都踩过）

| 症状 | 原因 | 解法 |
|---|---|---|
| GitHub Search 返回 422 | `OR` 混在 qualifier 里 | 拆成多次查询 |
| 渲染失败「页面没 READY」 | 英文简介里的 `'` 转义被吃掉 | 用 `_jsq()` 先转义反斜杠再转义单引号 |
| 并行渲染 180s 超时 | Windows `SO_REUSEADDR` 允许端口抢占 | `allow_reuse_address=False` + 3 次重试 |
| 混音人声被压回去 | `loudnorm` 重新平衡 | 换固定增益 + `alimiter` |
| subprocess 中文解码崩 | Windows 默认 GBK | `encoding='utf-8', errors='replace'` |
| 后半段没人声 | 配音写短了 | 目标 16–18 秒 / 130 字 |

---

## 十、目录

```
skills/github-to-video/SKILL.md   本文件
tools/                            流水线脚本
engine/                           vk 渲染引擎（每帧是 t 的纯函数）
examples/samples/                 样例成片
docs/                             详细文档
```
