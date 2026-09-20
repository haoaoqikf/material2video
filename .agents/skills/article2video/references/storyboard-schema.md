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

- `id`、`type`、`durationInFrames`、`narration`、`data`：内容层。
- `visualIntent`：`relation`、`focus`、`composition`、`density`、`tone`。
- `sceneTree`：唯一根节点；节点 `id` 在幕内唯一稳定。
- `motions`：通过节点 id 绑定 `reveal`、`fade`、`rise`、`count` 或 `draw`。
- `visual.kicker`：可选读者角标。

## 场景树节点

节点只允许 [视觉原语目录](primitive-catalog.md) 中的类型和属性。文字、数字和图表通过 `contentRef: "data.<path>"` 引用内容，图片通过 `sourceRef` 引用本地内容字段。禁止 HTML、CSS、JavaScript、第三方包、任意表达式和 `x/y/transform/style` 自由坐标逃生口。

布局节点最多 12 个直接子节点，树深最多 8；`split` 必须恰好两个子节点。内容和基础图形节点不能带子节点。连接节点的 `from` / `to`、动效的 `target` 必须引用本幕已存在的节点。

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
    "visualIntent": {"relation": "focus", "focus": "text", "composition": "offset", "density": "sparse", "tone": "tense"},
    "sceneTree": {"id": "root", "type": "stack", "children": [{"id": "copy", "type": "text", "contentRef": "data.text", "role": "headline"}]},
    "motions": [{"target": "copy", "recipe": "reveal", "startFrame": 18, "durationFrames": 36}]
  }]
}
```

严格校验：

```bash
uv run python .agents/skills/article2video/scripts/validate.py storyboard.json --declarative --strict --json
```

JSON 输出包含 `diversity`：片内检查总会运行；跨作品检查只在显式重复传入 `--reference <storyboard>` 时运行，绝不扫描内容根。
