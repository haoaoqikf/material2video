# 太阳系之旅：从太阳到奥尔特云

1920×1080、60 fps 的 cinematic 逐站导览，15幕，总预算135秒；短介绍与独立观察窗口分开。以安静而壮阔的深空旅行为美术方向，地球、土星与奥尔特云为三个hero。其他两个固定示例保持standard。

全片使用同一压缩太阳系模型，各幕缓慢推进或绕行，跨尺度以0.75秒叠化承接；不宣称一镜到底。主体身份来自幕的语义配置，镜头不再依赖旧固定全片帧号切换。名称与单一印象替代密集特征卡，平均日距读取天体登记值，大小、距离、亮度及外层结构是艺术示意。

源文见[article.md](article.md)，分镜见[storyboard.json](storyboard.json)，设计见[DESIGN.md](DESIGN.md)，来源及许可见[SOURCES.md](SOURCES.md)，当前检查状态见[VERIFICATION.md](VERIFICATION.md)。

## 逐站预算

重叠已经计入以下有效时长，实际TTS必须容纳于定位与观察留白之间；不足时prepare拒绝而不截断。

| 幕 | 主体 | 有效秒数 | 简短导览 |
|---|---|---:|---|
| sun-stop / sun-line | sun | 13 | 从太阳出发吧。这颗恒星，照亮了我们的整个旅程。 |
| mercury-stop / mercury-line | mercury | 8 | 第一站，水星。离太阳最近，满身古老的陨坑。 |
| venus-stop / venus-line | venus | 8 | 接着是金星。厚厚的云，把这个世界藏了起来。 |
| earth-stop / earth-line | earth | 10 | 这一颗，你一定认识。蓝色的地球，是我们的家。 |
| moon-stop / moon-line | moon | 8 | 月球，是地球的天然卫星。一路陪伴着我们。 |
| mars-stop / mars-line | mars | 9 | 再往外，是火星。红色尘土，给它披上了一件外衣。 |
| ceres-stop / ceres-line | ceres | 6 | 经过谷神星，我们来到稀疏的小行星带。 |
| jupiter-stop / jupiter-line | jupiter | 12 | 木星到了，太阳系最大的行星。看看它身上，一道道宽阔的云带。 |
| saturn-stop / saturn-line | saturn | 12 | 下一站，土星。先别急着走，看看它慢慢展开的光环。 |
| uranus-stop / uranus-line | uranus | 9 | 这是天王星。一颗几乎侧躺着自转的冰巨星。 |
| neptune-stop / neptune-line | neptune | 9 | 更远处，是海王星。八颗行星中，它离太阳最远。 |
| pluto-stop / pluto-line | pluto | 8 | 冥王星，是一颗矮行星。它身上，还藏着一颗心。 |
| kuiper-stop / kuiper-line | kuiper | 5 | 这里是柯伊伯带，冰质小天体的家园。 |
| heliopause-stop / heliopause-line | heliopause | 9 | 再向外，是日球层顶。太阳风，在这里与星际介质相遇。 |
| oort-stop / oort-line | oort | 9 | 更远处，是推测中的奥尔特云。太阳，已成一个亮点。 |

## 重现制作

```powershell
uv run python examples/solar-system-journey/assets/sound/generate.py
uv run m2v validate --project examples/solar-system-journey
uv run m2v general input-review --storyboard examples/solar-system-journey/storyboard.json
# 实际阅读原文、完成语义审查；先制作整片动态粗预演与风险样片，记录证据后再精制
uv run m2v prepare --project examples/solar-system-journey
uv run m2v lookdev --project examples/solar-system-journey
uv run m2v preview --project examples/solar-system-journey
uv run m2v assets audit --project examples/solar-system-journey
uv run m2v render --project examples/solar-system-journey
uv run m2v qa --project examples/solar-system-journey
```

音乐及少量音效由版本控制内的生成器原创合成、CC0分发，生成WAV不入库。135秒score包含中频旋律与巨行星段落起伏，旁白时降低、观察时恢复。当前服务返回晓晓Warm标签，基于完整导览重新选择，不以标签冒充试听。保留语速和停顿。

准备媒体在本例outputs，交付在videos/examples/solar-system-journey/outputs；生成物不入库。粗预演使用仓库忽略的临时作品，不增加第四个example，也不能授权正式导出。帧驱动录制与最终版本绑定规则见[制作流程](../../.agents/skills/material2video/references/creative-production.md)。

## 当前复核

改进版已完成 135 秒完整预演、全片帧序列、14 处交界加密帧与自动音频检查，并完成正式导出（成片 SHA-256 `1e157633…`，详见 [VERIFICATION.md](VERIFICATION.md)）。关键画面、粗预演、风险样片及最终文件的版本、摘要与问题闭环见 [VERIFICATION.md](VERIFICATION.md) 与 `outputs/visual-notes.md`。未连续播放、实际试听或设备检查的项目已在记录中披露，不以技术通过代替审美与音乐可感知性结论。
