# 太阳系之旅：一次连续的旅程

1920×1080、60 fps 的 cinematic **一镜到底**：单幕 `solar-journey` 8100 帧（135 秒），28 个镜头首尾相接，相机从太阳系上方连续俯冲到太阳，再沿向外螺旋依次经过 15 个站点直到奥尔特云。全片没有切换、叠化或停顿；地球、土星与奥尔特云是三个 hero。其他两个固定示例保持 standard。

天体仍在同一压缩坐标模型中，但主序天体的方位角按轨道半径单调递增排成螺旋，镜头因此可以一路向外而不反复横穿太阳系。15 段旁白之间各保留 3 秒静默观察窗，由分镜的 `holdFrames` 声明；段间静默是单幕内保留观察时间且不打断口播的唯一方式。主体身份、章节与信息面板由当前镜头和旁白窗口推导，不再依赖幕级配置。压缩距离、放大天体与外层结构均为艺术示意。

源文见[article.md](article.md)，分镜见[storyboard.json](storyboard.json)，设计见[DESIGN.md](DESIGN.md)，来源及许可见[SOURCES.md](SOURCES.md)，当前检查状态见[VERIFICATION.md](VERIFICATION.md)。

## 帧预算

`360（开场俯冲）+ 4551（15 段 TTS）+ 14×180（段间静默）+ 669（奥尔特云收尾）= 8100`。

| 站点 | 旁白段 | 旁白帧 | 静默帧 | 站点镜头窗口 |
|---|---|---:|---:|---|
| 太阳 | sun-line | 309 | 180 | 360–669 |
| 水星 | mercury-line | 300 | 180 | 849–1149 |
| 金星 | venus-line | 285 | 180 | 1329–1614 |
| 地球 | earth-line | 297 | 180 | 1614–2121（hero） |
| 月球 | moon-line | 289 | 180 | 2271–2560 |
| 火星 | mars-line | 313 | 180 | 2740–3053 |
| 谷神星 | ceres-line | 225 | 180 | 3233–3458 |
| 木星 | jupiter-line | 373 | 180 | 3638–4011 |
| 土星 | saturn-line | 339 | 180 | 4011–4530（hero） |
| 天王星 | uranus-line | 294 | 180 | 4710–5004 |
| 海王星 | neptune-line | 316 | 180 | 5184–5500 |
| 冥王星 | pluto-line | 307 | 180 | 5680–5987 |
| 柯伊伯带 | kuiper-line | 216 | 180 | 6167–6383 |
| 日球层顶 | heliopause-line | 356 | 180 | 6563–6919 |
| 奥尔特云 | oort-line | 332 | 尾留白 669 | 6919–7431（hero） |

站点之间另有 11 个独立过场镜头；金星→地球、木星→土星、日球层→奥尔特云三段过场被对应 hero 吸收，因此总数是 28 个镜头。镜头窗口严格首尾相接，路径末点与下一镜首点完全相同，全部使用 `linear` 缓动。

## 重现制作

```powershell
node examples/solar-system-journey/scripts/generate-paths.mjs   # 只产出路径提案与检查报告
uv run python examples/solar-system-journey/assets/sound/generate.py
uv run m2v validate --project examples/solar-system-journey
uv run m2v prepare --project examples/solar-system-journey
uv run m2v lookdev --project examples/solar-system-journey
uv run m2v preview --project examples/solar-system-journey
uv run m2v qa --project examples/solar-system-journey
uv run m2v render --project examples/solar-system-journey
```

`generate-paths.mjs` 读取 `scenes/layout.tsx`，生成 `outputs/path-proposal.json` 与 `outputs/storyboard.generated.json`，并用与运行时相同的 CatmullRomCurve3 检查穿模、位置连续与边界速度；它**不直接改** `storyboard.json`，人工复核报告后再合并。

音乐及少量音效由版本控制内的生成器原创合成、CC0分发，生成WAV不入库。135秒score包含中频旋律与巨行星段落起伏，旁白时降低、观察时恢复。当前服务返回晓晓Warm标签，基于完整导览重新选择，不以标签冒充试听。保留语速和停顿。

准备媒体在本例outputs，交付在videos/examples/solar-system-journey/outputs；生成物不入库。帧驱动录制与最终版本绑定规则见[制作流程](../../.agents/skills/material2video/references/creative-production.md)。

## 当前复核

一镜到底版本已重写分镜、场景代码与路径生成器，并通过 `m2v validate`、相机数据测试与 900/2200 帧风险样片。完整 prepare、lookdev、preview/QA 与导出结果见 [VERIFICATION.md](VERIFICATION.md)；在实跑之前不把旧版记录当作本版本通过。旧 15 幕逐站导览与 63.73 秒版本均标为历史。
