# 示例

`examples/samples/` 里是三支真实产出，都是用本仓库的流水线做出来的。

| 文件 | 仓库 | 星数 | 时长 |
|---|---|---|---|
| `sample-01-cleanyourtv.mp4` | [Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv) | 5.5w | 18s |
| `sample-02-deepinfer.mp4` | [deepseek-ai/DeepInfer](https://github.com/deepseek-ai/DeepInfer) | 2.6w | 18s |
| `sample-03-tokeneconomizer.mp4` | [microsoft/TokenEconomizer](https://github.com/microsoft/TokenEconomizer) | 3k+ | 18s |

规格：1080×1920 · 30fps · AAC 48k 立体声 · −13 LUFS。

## 想看效果

```bash
# 生成一个本地播放器（可连播、可切留白版、可看文案）
python tools/make-player.py
# 然后用浏览器打开 out/播放器.html
```

## 每条的发布文案

`copy.md`（单条）与发布包目录里的 `.md`，格式：

```markdown
## 标题
手机界最省的优化工具来了｜cleanyourtv

## 正文
...

## 话题
#开源项目 #GitHub #程序员 #Python #涨知识 #一天一个开源项目

## 封面三行
第一行：手机界最省的优化工具
第二行：5.5w Star 才一个月
第三行：cleanyourtv
```

> 截图版权归各仓库所有者，仅作演示用途。
