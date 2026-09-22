# 分镜脚本结构 v2

`storyboard.json` 是内容、时长和画面声明的单一真源。新版入口只接受 `version: 2`、`schemaVersion: 2`；旧 `data.figure.kind` 分镜需先运行：

```bash
uv run python .agents/skills/article2video/scripts/migrate_storyboard.py old.json new.json
```

## 根字段

- `version` / `schemaVersion`：固定为 `2`。
- `fps`、`width`、`height`、`title`、`visual`：时间、画布和主题。
- `visualDirection`：全片视觉策略，包含 `motif`、`compositionBias`、`density`、`rhythm`、`avoid`。
- `scenes`：非空场景数组。

## 场景字段

- `id`、`type`、`durationInFrames`、`data`：内容层。
- `narration`：字符串口播。与 `narrationSegments` **互斥**，二者只能有一个。
  它仍是旧作品与静音幕的写法；当前不直接渲染（预留给配音）。
- `narrationSegments`：新作品的分段口播，每项 `{id, text, beatId}`。
  完整口播就是各段按顺序拼接，因此不存在第二份完整文本。每段的 `id` 在幕内唯一，
  `text` 非空，`beatId` 必须指向本幕声明的 beat；同一 beat 的引用必须**相邻**，
  否则时间轴会倒退或重叠。见[语义节拍与字幕同步](#语义节拍与字幕同步)。
- `beats`：语义节拍，每项 `{id, action, targets, meaning}`。`action` 取受控动作
  （见[视觉原语目录](primitive-catalog.md)的语义动作表）；`targets` 至少一个本幕节点，
  且**每个**目标原语都要支持该动作；`meaning` 非空，说明这条节拍解释了什么。
  只有声明了 `narrationSegments` 的幕可以声明 `beats`。
- `resolvedBeats`：**派生字段，不要在源分镜里写**。它由 `prepare.py` 按真实词边界
  解析后写入媒体清单，再经有效分镜传给画面；源分镜里的它会被校验器拒绝。
  字段形状为 `{id, action, targets, meaning, startFrame, endFrame}`，区间开始包含、
  结束不包含。
- `visualIntent`：`relation`、`focus`、`composition`、`density`、`tone`，
  以及视觉论证字段 `mode`、`claim`、`showWithoutText`、`primaryObject`、`motionMeaning`。
  `mode` 取 `metaphor`、`process`、`comparison`、`cycle`、`chart`、`image`、`typography`
  之一（`typography` 表示主要论点依赖文字成立）；其余四个字段分别是该幕唯一核心论点、
  无正文视觉表达（移除标题与正文后仍能看见的关系或变化）、承担论证的主要视觉对象，
  以及主要动效推进了什么理解。判据与正反例见
  [文章生成场景树分镜](article-to-storyboard.md)。
  旧分镜缺这些字段时，普通校验只给兼容警告、预览与渲染照常，`--strict` 才报错。
- `sceneTree`：唯一根节点；节点 `id` 在幕内唯一稳定。
- `motions`：通过节点 id 绑定 `reveal`、`fade`、`rise`、`count` 或 `draw`。
- `renderer`：可选画面双轨开关，默认 `{ "kind": "tree" }`（走 `sceneTree`）；
  声明 `{ "kind": "code", "module": "<稳定模块标识>" }` 时整幕交给作品的
  `scenes/<module>.tsx` 模块渲染（契约、白名单与确定性纪律见
  [代码场景](code-scenes.md)）。二者互斥。
- `visual.kicker`：可选读者角标。

## 语义节拍与字幕同步

字符串口播能让字幕和配音对齐，却说不清「画面正在解释哪一步推理」。分段口播把
同一段话切成可绑定 beat 的若干段，于是字幕、配音和画面共用同一批边界：

```json
{
  "narrationSegments": [
    {"id": "n1", "text": "先看投入的起点。", "beatId": "b1"},
    {"id": "n2", "text": "再看它一路累积。", "beatId": "b2"}
  ],
  "beats": [
    {"id": "b1", "action": "establish", "targets": ["flow-a"], "meaning": "先交代流程的起点"},
    {"id": "b2", "action": "accumulate", "targets": ["meter"], "meaning": "量级随口播累积"}
  ]
}
```

三条硬规则：

1. **严格验收**：非文字幕在 `--strict` 下至少要两条 beat，且至少一条动作真正改变
   对象状态或关系（`establish` / `highlight` 只是出现或更醒目，不算）。
2. **结尾留白**：最后一条 beat 完成后至少留 12 帧稳定阅读时间；无声预览按同一
   下限把口播预算与阅读余量分开，有声路径由真实词边界决定（作者把声明时长留足即可）。
3. **单一焦点**：任一帧最多一个对象处于焦点（显式 `state: "focus"`，或关系容器里
   被当前 beat 点亮的那个阶段）。

旧字符串口播的作品继续按原样预览与渲染，A 系列闸门对它们如实记为「跳过」。
逐条判据、错误措辞与人工裁决方式见[设计宪法](design-constitution.md)的
「动画论证 A 系列」与[视觉评审量表](visual-review-rubric.md)。


## 场景树节点

节点只允许 [视觉原语目录](primitive-catalog.md) 中的类型和属性。文字、数字和图表通过 `contentRef: "data.<path>"` 引用内容，图片通过 `sourceRef` 引用本地内容字段。禁止 HTML、CSS、JavaScript、第三方包、任意表达式和 `x/y/transform/style` 自由坐标逃生口。

布局节点最多 12 个直接子节点，树深最多 8；`split` 必须恰好两个子节点。内容和基础图形节点不能带子节点。连接节点的 `from` / `to`、动效的 `target` 必须引用本幕已存在的节点。五个中层原语（`flow`、`cycle`、`timeline`、`gauge`、`pictogram`）的容量、受控属性和动作支持清单由注册表唯一声明，见[视觉原语目录](primitive-catalog.md)。

关系容器（`flow` / `cycle` / `timeline`）的 `direction` 取 `ltr`、`rtl`、`ttb`、`btt`（`cycle` 取 `cw`、`ccw`），子节点数量在 2–6 之间；`gauge` 与 `pictogram` 必须用 `contentRef` 指向 `data` 里的 0–100 数值。`pictogram` 的 `icon` 只能取注册表登记的受控图标名，未登记的图标在读取阶段就失败（不会静默回退到占位图）。

## 最小示例

```json
{
  "version": 2,
  "schemaVersion": 2,
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "visualDirection": {
    "motif": "边界",
    "compositionBias": "asymmetric",
    "density": "sparse",
    "rhythm": "restrained",
    "avoid": ["repeated-center"]
  },
  "scenes": [{
    "id": "claim",
    "type": "quote",
    "durationInFrames": 150,
    "data": {"text": "真正害怕的是被否定"},
    "visualIntent": {
      "relation": "focus",
      "focus": "text",
      "composition": "offset",
      "density": "sparse",
      "tone": "tense",
      "mode": "typography",
      "claim": "真正害怕的不是失败，而是被否定",
      "showWithoutText": "整屏只有一块偏置的文字，四周留白把这句话单独托住",
      "primaryObject": "偏置的标题文字块",
      "motionMeaning": "标题上浮入场，把这句判断推到视线中心"
    },
    "sceneTree": {"id": "root", "type": "stack", "children": [{"id": "copy", "type": "text", "contentRef": "data.text", "role": "headline"}]},
    "motions": [{"target": "copy", "recipe": "reveal", "startFrame": 18, "durationFrames": 36}]
  }]
}
```

严格校验：

```bash
uv run python .agents/skills/article2video/scripts/validate.py storyboard.json --declarative --strict --json
```

上面是单幕示例，只演示字段形状。`--strict` 还会执行**全片**视觉叙事预算
（文字幕占比、相邻文字幕、非文字模式覆盖、声明与结构一致性），单幕作品无法满足
模式覆盖门槛，因此它不能作为交付物通过严格校验——完整可交付的例子见
[文章生成场景树分镜](article-to-storyboard.md) 的正例与反例。

JSON 输出包含 `diversity`：片内检查总会运行；跨作品检查只在显式重复传入 `--reference <storyboard>` 时运行，绝不扫描内容根。严格校验失败时逐条给出路径与原因，例如
`scenes[2].visualIntent.mode`：声明为 `chart` 但场景树只有文字与包装节点。
