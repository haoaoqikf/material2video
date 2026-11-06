# 太阳系之旅：一次连续的旅程

后续重制按[素材选择规范](../../../.agents/skills/material2video/references/visual-material-selection.md#视频优先与代码适用场景)判断：跨尺度旅程、路径与关系适合代码合成；若引入真实天体观测素材，优先找对应视频，静态观测原件可直接用图片，不把模拟运动当作实拍证据。本说明不改变现有素材与评审状态。

1920×1080、60 fps、统一制作，单幕连续经过15个站点，保留地球、土星与奥尔特云三个hero。新版路径与逐段预算已生成10473帧（174.55秒），31个时间窗首尾相接；完整动态粗预演已生成；复核使用全片时间标注帧序列、风险加密帧、路径/屏幕量测和自动音频信号报告，不要求播放视频、连续收听声音或试听音色。历史13230帧（220.5秒）版本及其记录保留作旧版基线，版本状态见[VERIFICATION.md](VERIFICATION.md)。

当前修订针对两个反馈：独立行星画面过近、过场等待过长。当前交付已调整行星布局与路径预算，并完成完整候选。以当前准备指纹和交付SHA绑定的全片时间标注帧序列、过场加密帧、路径/屏幕量测和自动音频信号完成复核；木星→土星画面分离清楚，行星与卫星关系保留，过场呈连续移动且未发现拖沓等待必改项。制作记录分别列出帧序列、接触表索引、路径/屏幕量测和自动音频信号。路径端点相接与技术QA通过不作为空间表达或节奏自然的充分证据；QA中claims可见性未自动判定，内容可见性按静帧人工复核记录。复核明细见交付目录`visual-notes.md`（视频内容根目录中，不入库）。

新版帧预算：`360开场 + 4554实测TTS + 14段独立预算 + 759收尾 = 10473`。空间过场按路径长度生成3.5～5秒，另分别保留站点离场、接近与hero观察；木星→土星空间过场3.5秒，完整段间窗口5.25秒。参数与节奏问题关闭证据分开记录：结论由全片帧序列、过场加密帧和量测共同支持。帧预算与实际窗口由生成器及prepare分别核对，旁白原文、语速和音色保持；配乐长度随分镜生成，音乐/音效均为原创合成CC0。

源文见[article.md](article.md)，材料见[storyboard.json](storyboard.json)，设计与风险见[DESIGN.md](DESIGN.md)，来源许可见[SOURCES.md](SOURCES.md)。大小与距离分别压缩，所有天体与外层结构为艺术示意，奥尔特云明确为推测性结构。

## 重现制作

示例媒体不入库；首次重建先运行恢复入口，按配方下载观测图并生成程序化材质，逐项校验摘要、尺寸与时长，已正确的文件直接复用。下载或生成失败会明确报错且不改写已有素材。

```powershell
uv run python examples/spatial-3d/solar-system-journey/assets/fetch.py
node examples/spatial-3d/solar-system-journey/scripts/generate-paths.mjs --merge
node examples/spatial-3d/solar-system-journey/scripts/check-motion.mjs
uv run python examples/spatial-3d/solar-system-journey/scripts/render-rough.py
uv run python examples/spatial-3d/solar-system-journey/assets/sound/generate.py
uv run m2v validate --project examples/spatial-3d/solar-system-journey
uv run m2v prepare --project examples/spatial-3d/solar-system-journey
uv run python examples/spatial-3d/solar-system-journey/scripts/render-risk.py
uv run m2v lookdev --project examples/spatial-3d/solar-system-journey --stills 5 --sample-seconds 24
# 可选片段检查，默认前十秒且严格短于全片
uv run m2v preview --project examples/spatial-3d/solar-system-journey
uv run m2v assets audit --project examples/spatial-3d/solar-system-journey
uv run m2v render --project examples/spatial-3d/solar-system-journey
uv run m2v qa --project examples/spatial-3d/solar-system-journey
```

路径生成器默认只写outputs下提案，加`--merge`合并镜头与已核定时间预算，保留旁白原文与claims，文本变化时拒绝静默回退。运动诊断逐帧执行真实相机，记录有限数值、穿模余量、速度与加减速、转向、FOV变化、每个镜头的主体屏幕尺度与轨迹，`observation=not-evaluated`，不自动生成审美通过结论。`render-risk.py`从当前准备片段采集全片正式画幅风险帧，重跑会先清空旧采样。粗预演只用于设计，不授权正式导出；有当前准备产物时直接复用其完整母版音轨，没有时退回原创循环底并明确标注为临时声音。

准备媒体在本例outputs，交付为examples/spatial-3d/solar-system-journey/outputs/video.mp4；生成媒体、粗预演和复核证据不入库。最终记录绑定当前准备指纹与交付摘要，流程见[制作阶段](../../../.agents/skills/material2video/references/production-workflow.md)。

## 旁白与场景对应

场景`solar-journey`采用Three.js / React Three Fiber / Drei绘制同一三维世界。旁白依次为：`sun-line`太阳、`mercury-line`水星、`venus-line`金星、`earth-line`地球、`moon-line`月球、`mars-line`火星、`ceres-line`谷神星、`jupiter-line`木星、`saturn-line`土星、`uranus-line`天王星、`neptune-line`海王星、`pluto-line`冥王星、`kuiper-line`柯伊伯带、`heliopause-line`日球层顶、`oort-line`奥尔特云。正文与字幕按实际配音窗口，导航按当前镜头推进。

本示例的画面组件与参数保存在本作品 `scenes/`，可独立重建。
