# 分镜脚本结构 v4

`storyboard.json` 是内容、时长和画面声明的单一真源。校验、准备、预览、评审和渲染只接受 `version: 4`、`schemaVersion: 4` 与 `directingVersion: 2`。v1–v3 输入明确拒绝，必须重新编排；没有迁移命令、兼容模式或运行时回退。

## 根字段

- `version` / `schemaVersion` / `directingVersion`：固定为 `4` / `4` / `2`。
- `fps`、`width`、`height`、`title`：全片帧率、画布与标题；标准示例使用 30fps、1080×1920。
- `visual`：声明 `preset: "keynote"`，`theme` 为 `dark` 或 `light`。
- `visualDirection`：全片母题、构图倾向、密度、节奏与禁止项。
- `directingBrief`：核心论点、受众认知变化、情绪弧线、视觉母题、风格包和避免项。
- `world`：唯一持续视觉世界，含 `id`、`claim`、`metaphor`、全局 `objects`、唯一 `renderer`、基础 `data`、`stateTracks`、`motions` 与必需的 `camera`。
- `stages`：一个或多个叙事时间阶段；阶段只声明 `id`、`durationInFrames`、`data`、`visualIntent`、可选 `narrationSegments` 与 `beats`。阶段不能声明 `renderer`、`sceneTree`、`camera` 或 `transition`。
- `soundtrack`：可选受控音乐及音效声明。

这里的 world 是整条视频持续存在的视觉世界；stage 是口播与推理的时间分段。多个阶段可以推动同一世界中的对象变化，不意味着换场景。镜头推拉、焦点移动也不构成场景切换。

## 世界、对象和轨道

`world.objects` 是稳定对象目录。每个对象有唯一 `id`、`role`（`primary` / `supporting` / `annotation`）和说明；至少声明一个 primary。tree renderer 的对象必须映射到全局场景树节点，code renderer 的对象必须被全局代码模块探针观察到。

`world.data` 提供对象基础状态和作品数据。`stateTracks` 以 `id`、`target`、`property`、`binding`、`to` 和 `interpolation` 声明确定性变化；绑定使用 `{ "beatId": "..." }` 或 `{ "stageId": "...", "phase": "change" }`，禁止手写 `startFrame`。起始值由基础数据或前一条轨道终态派生，不维护第二份真源。属性和值类型遵循场景树/代码场景契约和严格校验。

图表数据来自分镜引用的 `{label, value}` 数组；`value: null` 表示缺测，保留类别标签与横向位置但不绘制该点。折线只连接有值的数据点，不能补造缺失数值。

镜头仅在 `world.camera` 声明一次：包括 `shot`、`composition`、`depth`、初始 `focus` 与非空 `segments`。镜头段以全局 beat 或阶段 phase 绑定。世界只允许一种 renderer：`{ "kind": "tree", "sceneTree": { ... } }` 所用的全局 `world.sceneTree`，或 `{ "kind": "code", "module": "..." }` 指向作品 `scenes/<module>.tsx`。两者互斥。

## 阶段、口播和视觉论证

每个有口播的 stage 都要声明 `narrationSegments` 与 `beats`。每段 `{id,text,beatId}`，每个 beat `{id,action,targets,meaning}`；id 在全片唯一。完整口播是所有阶段口播段按顺序直接拼接的结果。动作、状态、镜头和字幕引用同一全局时间轴；媒体准备后生成 `resolvedBeats`，源分镜不能写它。

每阶段的 `visualIntent` 完整声明 `relation`、`focus`、`composition`、`density`、`tone`、`mode`、`claim`、`showWithoutText`、`primaryObject` 和 `motionMeaning`。它解释这一阶段的推理增量，而不是创建另一张完整页面。声明口播的阶段至少有两个 beat，且至少一个动作真实改变对象状态或关系；最后一个 beat 后留至少 12 帧稳定阅读区。

所有轨道、camera 段和 motion 都由 beat 或 phase 绑定；轨道冲突、类型不匹配、未知节点或无效动作在校验阶段失败。tree 原语细节见[视觉原语目录](primitive-catalog.md)，代码模块的确定性与探针协议见[代码场景](code-scenes.md)。

## 标准字数与时长

标准正文和最终拼接口播各为 130～170 字，目标约 150 字。标题不计；Unicode 标点与空白不计，其余 Unicode 码点（包括数字和拉丁字母）逐个计数。输入审查、最终口播长度、声明时长与媒体实际时长分别校验。

声明总时长为 `sum(stages[].durationInFrames) / fps`，须在 35～45 秒（含边界）。配音准备后再以媒体派生全片帧数检查 35～45 秒；配音超限不能截断口播或补静音，须调整文本/正常语速/有意义停顿后重新 prepare。

## 最小字段形状

可运行的完整双轨样例见 [飞镖示例](../../../../examples/darts-trial-and-error/storyboard.json) 与 [发布会设计示例](../../../../examples/keynote-baseline/storyboard.json)。以下只展示字段形状，不能单独通过字数与语义节拍门禁：

```json
{
  "version": 4,
  "schemaVersion": 4,
  "directingVersion": 2,
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "title": "标题",
  "visual": { "theme": "dark", "preset": "keynote" },
  "visualDirection": { "motif": "持续母题", "compositionBias": "centered", "density": "balanced", "rhythm": "steady", "avoid": [] },
  "directingBrief": { "thesis": "核心判断", "audienceShift": "认知变化", "emotionalArc": ["疑问", "理解"], "visualMotif": "同一视觉世界", "stylePack": "cinematic", "avoid": [] },
  "world": {
    "id": "world-id",
    "claim": "核心判断",
    "metaphor": "持续存在的视觉隐喻",
    "objects": [{ "id": "object-id", "role": "primary", "description": "稳定对象" }],
    "renderer": { "kind": "code", "module": "world" },
    "data": { "objects": { "object-id": { "state": "rest" } } },
    "stateTracks": [],
    "motions": [],
    "camera": { "shot": "medium", "composition": "center", "depth": "flat", "focus": "object-id", "segments": [{ "id": "hold", "kind": "hold", "binding": { "stageId": "stage-a", "phase": "establish" }, "focus": "object-id", "intensity": 0 }] }
  },
  "stages": [{
    "id": "stage-a", "durationInFrames": 1080,
    "data": {},
    "visualIntent": { "relation": "focus", "focus": "shape", "composition": "center", "density": "balanced", "tone": "neutral", "mode": "metaphor", "claim": "阶段判断", "showWithoutText": "不看正文仍能观察到的变化", "primaryObject": "稳定对象", "motionMeaning": "状态变化如何推进判断" },
    "narrationSegments": [{ "id": "line-a", "text": "口播句子。", "beatId": "beat-a" }],
    "beats": [{ "id": "beat-a", "action": "establish", "targets": ["object-id"], "meaning": "建立对象" }]
  }],
  "soundtrack": null
}
```

校验命令：

```bash
uv run m2v validate --project videos/<slug>
uv run m2v prepare --project videos/<slug>
```

版本 4 的主规格和边界以 OpenSpec `storyboard-v3-contract`（历史 capability 名称，当前内容定义 v4）为准。输入审查与候选稿采用流程见[输入文章审查](input-review.md)，从文章构建持续世界的流程见[文章生成分镜](article-to-storyboard.md)。
