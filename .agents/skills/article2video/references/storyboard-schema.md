# 分镜脚本结构 v3

`storyboard.json` 是内容、时长和画面声明的单一真源。所有读取、校验、预览、配音准备、评审与渲染入口只接受 `version: 3`、`schemaVersion: 3`。v1/v2 分镜统一拒绝并提示「不支持 v3 之前分镜」；没有迁移命令、兼容模式或运行时回退。

## 根字段

- `version` / `schemaVersion`：都必须为 `3`。
- `fps`、`width`、`height`、`title`：时间、画布与标题。
- `visual`：必须含 `preset: "keynote"`，主题可选 `dark` / `light`。
- `visualDirection`：完整全片策略 `motif`、`compositionBias`、`density`、`rhythm`、`avoid`。
- `directingVersion`：固定 `1`。
- `directingBrief`：必填，包含 `thesis`、`audienceShift`、至少两个阶段的 `emotionalArc`、`visualMotif`、`stylePack` 与 `avoid`。
- `scenes`：非空场景数组。

## 每幕字段

- `id`、`type`、`durationInFrames`、`data`：内容层。
- `renderer`：必填；场景树幕声明 `{ "kind": "tree" }`，代码幕声明 `{ "kind": "code", "module": "..." }`。
- `visualIntent`：必填并完整声明 `relation`、`focus`、`composition`、`density`、`tone`、`mode`、`claim`、`showWithoutText`、`primaryObject`、`motionMeaning`。论证字段含义见[文章生成场景树分镜](article-to-storyboard.md)。
- `camera`：必填 `shot`、`composition`、`depth`、`focus` 与非空 `segments`。每段以 `beatId` 或 `phase` 绑定同一时间轴，并声明 `kind`；不接受单一 `movement`。
- `transition`：第一幕不得声明，第二幕起每幕必填，必须给 `meaning`。`inherit` / `transform` 使用 `source` + `target`，`decompose` 使用 `source` + 2–6 个 `targets`，`recompose` 使用 2–6 个 `sources` + `target`，`break` 使用 `source`，`dissolve` 不建立节点身份。
- `sceneTree`：`tree` renderer 必须有唯一根节点；节点 `id` 在幕内唯一稳定。`code` renderer 不得声明场景树。
- `narrationSegments` 与 `beats`：只要有口播，两者都必填；不接受字符串 `narration`。每项 `{id,text,beatId}` 与 `{id,action,targets,meaning}`，完整口播由段落拼接。静音幕可以不声明两者。
- `resolvedBeats`：媒体准备生成的派生字段，源分镜不得写。帧区间左闭右开，并与字幕 cue、镜头与动作共用时间轴。
- `motions`：必填数组，可为空。每条必须使用 `target` 或 `targets` 之一、受控 `recipe`，并且恰好绑定 `phase` 或 `beatId`。禁止 `startFrame`。编组动作必须配 `stagger`，错峰支持 `forward` / `reverse` / `center` / `path`。
- `visual.kicker`：可选短角标。

## 语义节拍、镜头与动作共用时间轴

```json
{
  "narrationSegments": [
    {"id": "n1", "text": "先看投入的起点。", "beatId": "b1"},
    {"id": "n2", "text": "再看它一路累积。", "beatId": "b2"}
  ],
  "beats": [
    {"id": "b1", "action": "establish", "targets": ["flow-a"], "meaning": "交代起点"},
    {"id": "b2", "action": "accumulate", "targets": ["meter"], "meaning": "量级随口播累积"}
  ],
  "motions": [
    {"target": "flow-a", "recipe": "reveal", "beatId": "b1", "durationFrames": 18},
    {"targets": ["step-a", "step-b"], "recipe": "rise", "beatId": "b2", "stagger": {"kind": "path", "path": ["step-a", "step-b"], "intervalFrames": 4}}
  ],
  "camera": {
    "shot": "medium", "composition": "center", "depth": "layered", "focus": "flow-a",
    "segments": [
      {"kind": "hold", "beatId": "b1", "focus": "flow-a"},
      {"kind": "push-in", "beatId": "b2", "focus": "meter"},
      {"kind": "settle", "phase": "settle", "focus": "meter"}
    ]
  }
}
```

严格验收要求非文字幕至少两个 beat，且至少一个动作改变对象状态或关系；最后一个 beat 后留至少 12 帧稳定阅读区。所有 motion 与 camera segment 都在 beat 或阶段时间轴内解析，编组错峰按声明顺序传播，不能越过稳定阅读区。

## 跨幕连续性

连续性窗口由风格包决定。窗口内，上一幕只保留映射源节点及其布局祖先，当前幕渲染映射目标；几何与状态均按当前帧号确定性求值。转场必须明确表达两幕关系，不从相似 id 推断。代码场景没有可静态核对的场景树节点，不能作为映射端点。

## 场景树节点

节点只允许[视觉原语目录](primitive-catalog.md)登记的类型和属性。文字、数字和图表通过 `contentRef: "data.<path>"` 引用内容，图片通过 `sourceRef` 引用本地内容字段。禁止 HTML、CSS、JavaScript、第三方包、任意表达式和 `x/y/transform/style` 自由坐标。

布局节点最多 12 个直接子节点，树深最多 8；`split` 必须恰好两个子节点。连接节点、镜头焦点和动效目标必须引用本幕节点。五个中层原语 `flow`、`cycle`、`timeline`、`gauge`、`pictogram` 的容量、属性与动作支持清单由注册表唯一声明。

## 完整最小示例

```json
{
  "version": 3,
  "schemaVersion": 3,
  "directingVersion": 1,
  "directingBrief": {"thesis": "方向决定努力效果", "audienceShift": "由投入转向反馈", "emotionalArc": ["疑问", "确认"], "visualMotif": "偏置路径", "stylePack": "editorial", "avoid": []},
  "visual": {"theme": "dark", "preset": "keynote"},
  "fps": 30, "width": 1080, "height": 1920,
  "visualDirection": {"motif": "路径", "compositionBias": "asymmetric", "density": "sparse", "rhythm": "restrained", "avoid": []},
  "scenes": [{
    "id": "claim", "type": "quote", "durationInFrames": 150,
    "data": {"text": "真正害怕的是被否定"},
    "renderer": {"kind": "tree"},
    "visualIntent": {"relation": "focus", "focus": "text", "composition": "offset", "density": "sparse", "tone": "tense", "mode": "typography", "claim": "真正害怕的不是失败，而是被否定", "showWithoutText": "偏置文字块周围留下大面积空白", "primaryObject": "偏置标题文字", "motionMeaning": "标题从边缘进入后停在视觉中心"},
    "camera": {"shot": "wide", "composition": "left", "depth": "flat", "focus": "copy", "segments": [{"phase": "establish", "kind": "hold", "focus": "copy"}]},
    "sceneTree": {"id": "root", "type": "stack", "children": [{"id": "copy", "type": "text", "contentRef": "data.text", "role": "headline"}]},
    "motions": [{"target": "copy", "recipe": "reveal", "phase": "establish", "durationFrames": 36}]
  }]
}
```

```bash
uv run python .agents/skills/article2video/scripts/validate.py storyboard.json --declarative --strict --json
```

上例只演示字段结构；完整交付还要满足严格模式下的全片模式覆盖。可运行的完整样例见[文章生成场景树分镜](article-to-storyboard.md)。
