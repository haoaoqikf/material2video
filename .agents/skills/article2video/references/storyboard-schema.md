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
| `visual` | `object` | 否 | 共享页面的主题与可选预设：`{"theme":"dark","preset":"keynote"}`，`theme` 默认 `dark`，`preset` 省略即不启用 |

宽高必须是偶数：H.264 的 `yuv420p` 像素格式要求宽高可被 2 整除，奇数会导致编码失败。

`visual` 的子字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `theme` | 否 | `dark` 或 `light`，默认 `dark` |
| `preset` | 否 | 设计语言预设，目前唯一取值 `"keynote"`（发布会级设计语言，见[发布会级设计语言](keynote-design-system.md)） |

`preset` 是可选字段：**省略时行为逐帧不变**。共享页面仍会引入设计语言层的样式与
脚本，但它们全部受 `[data-a2v-preset="keynote"]` 作用域约束，排版引擎也不会被调用，
因此画面与不引入该层时完全一致。
未知取值报错，并指出 `visual.preset` 字段路径。

## 场景字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | `string` | 是 | 场景唯一标识，只允许字母、数字、`_`、`-`；同时作为网页中 `data-scene-id` 的值 |
| `type` | `string` | 是 | 场景类型，决定网页使用哪个渲染分支 |
| `durationInFrames` | `number` | 是 | 该场景持续帧数，正整数 |
| `narration` | `string` | 否 | 口播文案，供 prepare.py 合成配音；省略或空字符串表示静音。未传 --media 时不渲染口播 |
| `data` | `object` | 是 | 该场景的内容，字段由 `type` 决定 |
| `visual` | `object` | 否 | 共享页面布局与幕角标：`{"layout":"center"}` 或 `{"layout":"lower"}`，默认 `center`；可选 `kicker`（读者用的定位词，最多 8 个字） |

场景在时间轴上的起点由其前面所有场景的 `durationInFrames` 累加得到，
**不需要也不应该手写起始帧**，避免两处数据不一致。

### `visual.kicker`：幕角标是文案，不是类型名

```json
{ "id": "attention", "type": "list", "visual": { "layout": "center", "kicker": "注意力" } }
```

`kicker` 是画面左上角的**定位词**（右上角是 `04 / 08` 幕号）。规则：非空、单行、
最多 8 个字、不能等于该幕的 `type`。**没写就留空**，不会回落到 `type`——
分镜的类型标识符（`TITLE`、`LIST`、`TIMELINE`）是 schema 字段名，
不是给读者看的字，不该出现在画面上。详见
[视觉规范](visual-spec.md#幕角标-visualkicker)。

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
| `chart` | `values`（非空数组） | `title`, `chart`, `annotations`, `figure` | 数据序列：占比、趋势、构成 |
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

`chart` 的 `data.values` 是图表的数据序列，每项形如 `{"label": "四月", "value": 12}`：
标签非空（建议 ≤ 12 字，超长只警告；重复标签会警告），数值必须是有限数字。
条目建议 2–6 个，超出组件舒适区会警告。可选的 `data.chart` 选择图表类型：
`bar`（柱状，默认）/ `line`（折线）/ `pie`（饼图）。
**组件里没有任何默认数据**：`values` 缺失或非法时渲染直接报错，不画示例值。
图表内部的文字画在 canvas 上，探针量不到；组件会把每个数值以**最终值**同步
输出为 DOM 文本（`data-el="value-<序号>"`），观感闸门据此判定。

## 选择视觉组件

`figure` 是可选的对象，声明这一幕**用哪个视觉组件来画**。不写时用网页给出的
「场景类型 → 默认组件」映射，因此旧分镜不需要改动：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `kind` | 否 | 组件名（见 [视觉组件目录](figure-catalog.md)）；省略时按场景类型取默认组件，写了就必须是非空字符串 |
| `labels` | 否 | 画在图上的短标签，规则与 `annotations` 完全相同 |
| `motion` | 否 | 动效节奏：`calm` / `normal` / `impact`，默认 `normal` |
| `params` | 否 | 预留的几何覆盖：**当前没有组件读取它**，写了不会改变画面，校验器会提醒 |
| `schematic` | 否 | 示意标记：`true` 表示这组数值没有来源。图表组件会自动在画面画出「示意」标；其它组件要求文案里出现「示意」二字，否则校验器会提醒 |

```json
"figure": {
  "kind": "iceberg",
  "motion": "impact",
  "labels": { "tip": "失去", "mass": "被看见的不足", "surface": "水面" }
}
```

`figure.labels` 与顶层的 `annotations` 是同一件事：前者是新写法，后者是过渡期兼容写法，
两者同时存在时以 `figure.labels` 为准。校验器负责结构与取值合法性（`kind` 缺省允许、
写了必须非空；`motion` 在三者之内；`labels` 每项非空且不过长），**组件是否存在**由组件目录决定，
网页在挂载时发现未注册的 `kind` 会立即报错，而不是画出空白。

## 声明式画面模式

新视频可以只提交 `article.md` 和 `storyboard.json`，由共享页面创建场景。使用
`validate.py <分镜> --declarative --strict` 预校验；`render.py --storyboard <分镜>`
或 `preview.py --declarative --storyboard <分镜>` 使用共享页面。旧的专属 `index.html`
路径仍可用。完整示例见 [declarative-number](../../../../examples/declarative-number/storyboard.json)。

声明式模式使用 `data.figure.kind`、`labels` 和 `motion`，未写 `kind` 时按场景类型
取目录默认值。未知组件、布局、主题、预设、动效、额外字段和未实现的 `figure.params` 均为错误，
错误包含分镜字段路径。当前 `params` 没有可用键；分镜不能声明 HTML、CSS、JS 或第三方包。
`number` 的基础组件读 `value`、`label`、`caption`；数值型 `value` 按帧递增显示。

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
