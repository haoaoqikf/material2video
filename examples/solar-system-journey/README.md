# 太阳系之旅：一次连续的旅程

1920×1080、60 fps、cinematic，单幕连续经过15个站点，保留地球、土星与奥尔特云三个hero。当前版本为13230帧（220.5秒），31个时间窗首尾相接；用户已观看完整预演并确认通过，按指令不执行正式 render，交付版本为 `videos/examples/solar-system-journey/outputs/previews/video.mp4`，摘要见[VERIFICATION.md](VERIFICATION.md)。旧版135秒仅作问题基线。

本次解决两个必改反馈：S01天体之间快速掠过、缺乏持续穿行；S02局部转向与切换突兀。速度隆起在整个阶段展开，视线贯穿跨站过程，远点在近景同侧延伸以避开天顶翻转。`scenes/flight.ts`对位置作跨边界帧驱动滤波，并计算连续朝向；真实相机、动态粗预演与数值诊断共用该函数。路径端点相接和技术QA通过不作为运动自然的充分证据。

帧预算：`360开场 + 4551真实TTS + 14×540段间运动/观察 + 759收尾 = 13230`。每个段间9秒预算含上一站1.5秒尾留白、5.5秒空间过场、下一站2秒接近；三个hero自身为8～12秒，不把前置赶路算作观察时间。帧预算与实际窗口由生成器及prepare分别核对，旁白原文、语速和音色保持；配乐长度随分镜生成，音乐/音效均为原创合成CC0。

源文见[article.md](article.md)，材料见[storyboard.json](storyboard.json)，设计与风险见[DESIGN.md](DESIGN.md)，来源许可见[SOURCES.md](SOURCES.md)。大小与距离分别压缩，所有天体与外层结构为艺术示意，奥尔特云明确为推测性结构。

## 重现制作

```powershell
node examples/solar-system-journey/scripts/generate-paths.mjs --merge
node examples/solar-system-journey/scripts/check-motion.mjs
uv run python examples/solar-system-journey/scripts/render-rough.py
uv run python examples/solar-system-journey/assets/sound/generate.py
uv run m2v validate --project examples/solar-system-journey
uv run m2v prepare --project examples/solar-system-journey
uv run python examples/solar-system-journey/scripts/render-risk.py
uv run m2v lookdev --project examples/solar-system-journey --stills 5 --sample-seconds 24
# 可选片段检查，默认前十秒且严格短于全片
uv run m2v preview --project examples/solar-system-journey
uv run m2v assets audit --project examples/solar-system-journey
uv run m2v render --project examples/solar-system-journey
uv run m2v qa --project examples/solar-system-journey
```

路径生成器默认只写outputs下提案，加`--merge`合并镜头与已核定时间预算，保留旁白原文与claims，文本变化时拒绝静默回退。运动诊断逐帧执行真实相机，记录有限数值、穿模余量、速度与加减速、转向、FOV变化、每个镜头的主体屏幕尺度与轨迹，`observation=not-evaluated`，不自动生成审美通过结论。`render-risk.py`从当前准备片段采集全片正式画幅风险帧，重跑会先清空旧采样。粗预演只用于设计，不授权正式导出；有当前准备产物时直接复用其完整母版音轨，没有时退回原创循环底并明确标注为临时声音。

准备媒体在本例outputs，交付为videos/examples/solar-system-journey/outputs/video.mp4；生成媒体、粗预演和复核证据不入库。最终记录绑定当前准备指纹与交付摘要，流程见[制作阶段](../../.agents/skills/material2video/references/creative-production.md)。

## 旁白与场景对应

场景`solar-journey`采用Three.js / React Three Fiber / Drei绘制同一三维世界。旁白依次为：`sun-line`太阳、`mercury-line`水星、`venus-line`金星、`earth-line`地球、`moon-line`月球、`mars-line`火星、`ceres-line`谷神星、`jupiter-line`木星、`saturn-line`土星、`uranus-line`天王星、`neptune-line`海王星、`pluto-line`冥王星、`kuiper-line`柯伊伯带、`heliopause-line`日球层顶、`oort-line`奥尔特云。正文与字幕按实际配音窗口，导航按当前镜头推进。
