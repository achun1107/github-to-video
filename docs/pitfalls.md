# 踩坑记录

这套流水线在真跑 100 条的过程中踩到的坑。全部已修在代码里。

---

## 1. GitHub Search 返回 422

**现象**：`q=stars:>1000 topic:ai OR topic:llm` 直接 422 Unprocessable Entity。

**原因**：GitHub Search 的布尔 OR **不能**混在 qualifier 内部；多个 topic 必须拆成多次查询。

**解法**：

```python
queries = [
    base + ' topic:ai',
    base + ' topic:llm',
    base + ' topic:agent',
]
# 分别请求，结果合并去重
```

---

## 2. 渲染失败：页面三次都没能 READY

**现象**：某条片子的 `render.py` 超时报 `RuntimeError: 页面三次都没能 READY`。

**原因**：仓库英文简介里带单引号（`you'd`），生成 `film.js` 时用
`.replace("'", "\\'")` 转义，后面又 `.replace('\\', '')` 清理反斜杠，
把转义符也吃掉了 → 输出非法 JS → 页面脚本报错 → 永远不到 READY。

**解法**：写成两步，先转义反斜杠再转义单引号。

```python
def _jsq(text):
    return (text or '').replace('\\', '\\\\').replace("'", "\\'").replace('\n', ' ')
```

---

## 3. Windows 并行渲染撞端口

**现象**：`--jobs 4` 时随机一条子进程卡 180 秒，日志里 `ERR_CONNECTION_REFUSED`。

**原因**：Python `HTTPServer` 默认 `allow_reuse_address = 1`（SO_REUSEADDR）。
Windows 上这个标志**允许另一个进程抢占同一端口**。4 个子进程各起一个内置
HTTP 服务器（端口 0 让系统分配），有两个拿到同一端口。

**解法**：

```python
class Handler(http.server.SimpleHTTPRequestHandler):
    if sys.platform == "win32":
        allow_reuse_address = False
```

再加页面加载 3 次重试，吸收偶发失败。

---

## 4. 混音调好人声，一归一化又回去了

**现象**：把人声调到 -12.5 dB、音乐 -17.9 dB，跑完 `loudnorm` 变成
人声 -13.3、音乐 -12.2 —— 音乐反而更响。

**原因**：`loudnorm` 是**整体响度归一化**，会按峰值重新分配各层的比例。
你在它之前做的所有增益调整都会被部分抵消。

**解法**：去掉 `loudnorm`，改成固定增益 + `alimiter` 只做峰值限制。

```bash
... amix=inputs=N:normalize=0 [a0];
[a0]alimiter=limit=0.85:attack=5:release=60:level=disabled [an]
```

---

## 5. 100 条里有 5 条「渲染失败」，其实是脚本自己崩了

**现象**：`batch-render.py` 报 5 条 FAIL，但单独跑 `render.py` 是成功的。

**原因**：`subprocess.run(..., capture_output=True, text=True)` 在 Windows 上
默认用 GBK 解码子进程输出；渲染日志里有 UTF-8 字节 → `UnicodeDecodeError`
→ 被当成「渲染失败」。

**解法**：

```python
subprocess.run(cmd, capture_output=True, text=True,
               encoding='utf-8', errors='replace')
```

---

## 6. 配音写短了，后半段没人声

**现象**：18 秒的画面，第 10 秒之后完全没声音。

**实测数据**（100 条片子逐段测 RMS）：

```
 0- 2s : -11.6 dB      10-12s : -43.1 dB   ← 断档开始
 2- 4s : -12.5 dB      12-14s : -40.8 dB
 4- 6s : -12.4 dB      14-16s : -40.7 dB
 6- 8s : -14.2 dB      16-18s : -40.0 dB
 8-10s : -17.1 dB
```

配音文件 `vo1.mp3` 只有 **9.07 秒**。

**原因**：配音模板只写了「钩子 + 名字 + 星数 + 上线日期」，约 90 字；
片子是 18 秒 4 张卡，后两张卡没有旁白。

**两次修正**：

| 版本 | 文案字数 | 实测时长 | 结果 |
|---|---|---|---|
| v1 | ~90 字 | 9.1 秒 | ❌ 第 10 秒起静音 |
| v2 | ~180 字 | 21–24 秒 | ❌ 超出画面 |
| **v3** | **~130 字** | **17.2–18.5 秒** | ✅ 100/100 覆盖 |

**解法**（`tools/batch-tts3.py`）：

1. 文案砍到 4 句、约 130 字（按 4 张卡的节奏写）
2. 起始 rate `+30%`，合成一次后用 `ffprobe` 测实际时长
3. 超长 → 计算 `(dur/17-1)*100` 再提速重合成；偏短 → 降到 `+18%`
4. 收尾用 `check-voice.py` 把 18 秒切 9 段，任一段低于 -30dB 即判失败

修复后复测：`配音覆盖检查：通过 100/100`，每段稳定在 -11.6 ~ -15.3 dB。

---

## 7. 混音脚本串行跑 100 条太慢

**现象**：`remix-all.py` 串行跑，50 分钟只推进 1 条（被前面的 ffmpeg 僵尸进程拖住）。

**解法**：改并发。`remix-fast.py --workers 8` → **18 秒**跑完 64 条。

> 并发前先确认没有残留的 `ffmpeg` / `python` 进程在等输入。

---

## 8. 输出文件损坏：moov atom not found

**现象**：某条 `final.mp4` 只有 1.8MB（正常 2.9MB），ffprobe 报
`moov atom not found`，播放器打不开。

**原因**：ffmpeg 在写入时被中断（进程被杀或并发抢资源），文件没写完。

**解法**：`verify-batch.py` 逐条 ffprobe，`streams` 为空即判缺失，重渲该条。
