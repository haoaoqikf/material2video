# 分镜脚本结构

分镜 JSON 是内容层的唯一真源：网页读它绘制画面，渲染脚本读它推导总帧数。
修改内容时**只改这一个文件**，不要在两处维护同一份文案。

## 顶层字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `version` | `number` | 是 | 结构版本，当前固定为 `1` |
| `fps` | `number` | 是 | 帧率，建议 `30`（也接受 24/25/60）|
| `width` | `number` | 否 | 画面宽度，默认 `1080`，必须是偶数 |
| `height` | `number` | 否 | 画面高度，默认 `1920`，必须是偶数 |
| `title` | `string` | 否 | 视频标题，用于日志与文件命名，不参与画面 |
| `scenes` | `array` | 是 | 非空场景数组 |

宽高必须是偶数：H.264 的 `yuv420p` 像素格式要求宽高可被 2 整除，奇数会导致编码失败。

## 场景字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | `string` | 是 | 场景唯一标识，只允许字母、数字、`_`、`-`；同时作为网页中 `data-scene-id` 的值 |
| `type` | `string` | 是 | 场景类型，决定网页使用哪个渲染分支 |
| `durationInFrames` | `number` | 是 | 该场景持续帧数，正整数 |
| `narration` | `string` | 否 | 口播文案，供 prepare.py 合成配音；省略或空字符串表示静音。未传 --media 时不渲染口播 |
| `data` | `object` | 是 | 该场景的内容，字段由 `type` 决定 |

场景在时间轴上的起点由其前面所有场景的 `durationInFrames` 累加得到，
**不需要也不应该手写起始帧**，避免两处数据不一致。

秒数与帧数的换算：`帧数 = 秒数 × fps`。30fps 下 5 秒 = 150 帧。

## 已知场景类型

| `type` | 必填字段 | 可选字段 | 适用内容 |
| --- | --- | --- | --- |
| `title` | `text` | `subtitle`, `emphasis`, `annotations`, `figure` | 开场命题、主题 |
| `quote` | `text` | `attribution`, `emphasis`, `annotations`, `figure` | 核心判断、金句 |
| `comparison` | `left`, `right` | `title`, `annotations`, `figure` | 两种选择、前后对照 |
| `timeline` | `items`（非空数组） | `title`, `annotations`, `figure` | 事件顺序、尝试过程 |
| `diagram` | `nodes`（非空数组） | `edges`, `title`, `annotations`, `figure` | 因果、约束、反馈模型 |
| `number` | `value` | `label`, `caption`, `annotations`, `figure` | 数量、频次、收益变化 |
| `list` | `items`（非空数组） | `title`, `annotations`, `figure` | 要点、行动步骤 |
| `conclusion` | `text` | `action`, `emphasis`, `annotations`, `figure` | 收束、行动建议 |

`emphasis` 是要在画面中强调的短语列表（非空数组，元素为非空字符串）。
网页负责把它渲染成强调样式，例如把第一处出现的短语包进 `<span class="key">`。
把重点放在数据里而不是硬编码进网页，可以避免同一条文案在分镜与页面两处维护。
短语必须能在该场景的文本字段里**原样命中**（网页只替换第一处出现），
否则校验器会警告「强调色不会生效」。

`annotations` 是可选的对象，给网页的图形组件提供**短标注**：键与值都必须是非空字符串，
值建议不超过 12 个汉字（超长只警告）。它回答的是「这幅图里的标签分别写什么」，
例如天平两侧托盘的名字、落差尺两端的写法。键的取值由网页实现决定，
当前各场景类型的约定键见 [竖屏视觉规范](visual-spec.md) 的「图形标注」一节。
文案仍然只存在于分镜里，网页不得为标注写默认文案。

## 选择视觉组件

`figure` 是可选的对象，声明这一幕**用哪个视觉组件来画**。不写时用网页给出的
「场景类型 → 默认组件」映射，因此旧分镜不需要改动：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `kind` | 是 | 组件名，取值见 [视觉组件目录](figure-catalog.md) |
| `labels` | 否 | 画在图上的短标签，规则与 `annotations` 完全相同 |
| `motion` | 否 | 动效节奏：`calm` / `normal` / `impact`，默认 `normal` |
| `params` | 否 | 覆盖组件的几何常量，键由组件自己声明 |

```json
"figure": {
  "kind": "iceberg",
  "motion": "impact",
  "labels": { "tip": "失去", "mass": "被看见的不足", "surface": "水面" }
}
```

`figure.labels` 与顶层的 `annotations` 是同一件事：前者是新写法，后者是过渡期兼容写法，
两者同时存在时以 `figure.labels` 为准。校验器负责结构与取值合法性（`kind` 非空、
`motion` 在三者之内、`labels` 每项非空且不过长），**组件是否存在**由组件目录决定，
网页在挂载时发现未注册的 `kind` 会立即报错，而不是画出空白。

分镜里的换行符是硬换行：把长句按语义手动断成每行不超过 14 个汉字，
比让浏览器自动折行更可控，也避免重点词被拆开。校验器会对超长行给出警告，
并按 [竖屏视觉规范](visual-spec.md) 的排版层级判断上限。

`nodes` 的每一项可以是字符串，也可以是含 `id` 的对象。
`edges` 的每一项可以是 `[from, to]` 数组，也可以是含 `from`/`to` 的对象；
`from` 与 `to` 必须引用 `nodes` 中已存在的节点，否则校验失败。

类型不在上表内时校验会给出**警告**（不是错误），以便扩展新组件；
但网页必须实现对应分支，否则渲染时 `render` 会抛错。

## 完整示例

```json
{
  "version": 1,
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "title": "为什么努力没结果",
  "scenes": [
    {
      "id": "opening",
      "type": "title",
      "durationInFrames": 150,
      "narration": "明明比以前更努力，结果却几乎没变？",
      "data": {
        "text": "为什么努力没结果？",
        "subtitle": "问题不在努力的程度"
      }
    },
    {
      "id": "loop",
      "type": "diagram",
      "durationInFrames": 390,
      "data": {
        "title": "约束会移动",
        "nodes": ["问题", "约束", "行动", "反馈"],
        "edges": [
          ["问题", "约束"],
          ["约束", "行动"],
          ["行动", "反馈"],
          ["反馈", "约束"]
        ]
      }
    }
  ]
}
```

## 校验规则

渲染前会对分镜做两级检查：

**错误**（阻止渲染）

- `version` 缺失或不是当前版本
- `fps` 不是 1..120 的整数
- `width` / `height` 不是正整数，或为奇数
- `scenes` 缺失、为空或不是数组
- 场景缺少 `id`、`id` 含非法字符、`id` 重复
- `durationInFrames` 不是正整数
- 场景缺少 `type`，或已知类型缺少 `data`
- 已知类型缺少必填字段或必填字段类型不对
- `items` / `nodes` 存在但不是非空数组
- `emphasis` 存在但不是非空数组，或元素不是非空字符串
- `edges` 引用了不存在的节点

**警告**（默认放行）

- `type` 不在已知清单中
- `fps` 不是 24/25/30/60
- 总时长超过 180 秒
- 宽度大于高度（与竖屏定位不符）
- `data` 中出现该类型未定义的字段
- 单行文本超过上限（正文/注释 20 字，小节标题 16 字，对比标签 8 字，
  列表项 14 字）：按 [竖屏视觉规范](visual-spec.md) 应拆场景或手动换行
- 场景短于 24 帧：入场动效会被压缩到看不清，通常应该并入相邻场景
- `emphasis` 的短语没有出现在该场景的文本里：画面上不会生效

使用 `validate.py --strict` 可以把警告也视为失败，适合定稿前检查。
视觉类警告只做提醒，不阻止渲染：文案长度属于表达取舍，由作者决定是否拆分。

## 校验命令

```bash
uv run python .agents/skills/article2video/scripts/validate.py examples/why-effort-fails/storyboard.json
uv run python .agents/skills/article2video/scripts/validate.py examples/why-effort-fails/storyboard.json --json
```

`--json` 输出 `{ok, errors[], warnings[], summary{}}`，便于自动修正循环。

## 配音派生时间轴

分镜版本仍为 1。`durationInFrames` 在有声模式中是最短时长；实际时长来自独立媒体清单。
不向源分镜写入音频路径、字幕时间戳或派生时长。
`validate.py <storyboard.json> --media <media.json>` 可同时检查清单是否过期及音轨时长。
详见 [配音与字幕](media-contract.md)。
