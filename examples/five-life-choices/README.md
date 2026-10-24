# 五种选择，五种人生

30秒 / 1920×1080 / 30fps 的剪纸短片，无旁白，以原创轻节奏音乐和三个动作音带出五种人生选择。暖白纸面、深墨剪影和橙色路径构成全片统一视觉；七段依次呈现共同起点、城市、行业、伴侣、投资、学习与结尾。

## 七段与动作

| 段落 | 时间 | 画面动作 | 文案 |
|---|---:|---|---|
| 开场 | 0–3秒 | 人物从岔路共同起点出发，沿橙色支路前行 | 同样的起点 |
| 城市 | 3–8秒 | 人物沿橙色上升路径穿过机会密度不同的楼群 | 城市，改变机会 |
| 行业 | 8–13秒 | 两条平行路线一平一升，较快路线迅速前移 | 行业，改变速度 |
| 伴侣 | 13–18秒 | 两人共同接合桥板并通过 | 伴侣，影响方向 |
| 投资 | 18–23秒 | 一块积木逐层累积成阶梯 | 投资，积累未来 |
| 学习 | 23–27秒 | 书页展开成阶梯，人物逐级上行越过障碍 | 学习，打开可能 |
| 结尾 | 27–30秒 | 五种道路形状汇聚到人物继续向前 | 每次选择，都在塑造以后 |

行业与投资只使用抽象示意，不表达排名、收益率或回报保证。无旁白，三个动作音依次对应城市机会路径、桥板与翻页。

## 重建

```powershell
uv run python examples/five-life-choices/assets/sound/generate.py
uv run m2v validate --project examples/five-life-choices
uv run m2v prepare --project examples/five-life-choices
uv run m2v preview --project examples/five-life-choices --start-seconds 23 --end-seconds 27
uv run m2v render --project examples/five-life-choices
uv run m2v qa --project examples/five-life-choices
```

片段检查只渲染指定窗口（不带参数时默认前十秒），这里用于在看全片之前检查 23–27 秒学习段的四秒动作与文案。

素材生成脚本和原创合成许可见 `assets/sound/`。画面设计与独立复核证据见[设计与视觉门禁](DESIGN.md)和[交付验证](VERIFICATION.md)；生成媒体与评审包保存在忽略的 `videos/`，不进入 Git。

## 制作评审帧包

使用项目的 `uv` 环境执行脚本。最终评审应在 `render` 后从完整 `outputs/video.mp4` 生成；`--start-seconds` 指定局部窗口在全片中的原始时间，帧说明也保留原时间码。每包包含1920、852、393像素帧、联系表、中性说明和 SHA-256 清单，且拒绝覆盖已有非空目录。

```powershell
uv run python examples/five-life-choices/scripts/create_review_pack.py `
  videos/examples/five-life-choices/outputs/video.mp4 `
  videos/examples/five-life-choices/outputs/review-packs/learning-window `
  --id K-window --start-seconds 23 --seconds 4 --interval 0.1
```

[来源与参考边界](SOURCES.md) · [视觉创意方向](../../.agents/skills/material2video/references/visual-creative-direction.md) · [视觉力量设计](../../.agents/skills/material2video/references/visual-impact-design.md)
