# 视觉组件目录

组件库回答一个问题：**这一幕画面用什么表达**。AI 做导演——从目录里挑一个组件、
给几段短标注、指定节奏——而不是每次都从零画一遍。目录里确实没有合适的时候，
再按 [组件契约](#组件契约) 新写一个，并把这个组件沉淀回目录。

- 组件代码：`assets/figures.js`（结构 + 逐帧逻辑）、`assets/figures.css`（样式）
- 挂载方式：网页里写 `<div class="a2v-safe" data-a2v-figure></div>`，
  由 `A2V.figures.renderScene(state, api, { defaults })` 按帧渲染
- 文案来源：分镜的 `data` 与 `data.figure.labels`，组件不保存任何默认文案

## 现有组件

| `kind` | 适合表达 | 默认给 | 标注键 | 容量 |
| --- | --- | --- | --- | --- |
| `balance` | 一边重一边轻，随后证明重的那个是空壳 | `title` | `leftPan`, `rightPan` | 2 侧 |
| `gap` | 量出「真正失去了多少」：一侧从满到空，另一侧从头就没有 | `quote` | `assumption`, `fact`, `dropLabel`, `noDropLabel` | 2 栏 |
| `versus` | 两种反应并排，箭头指出该从哪边转向哪边 | `comparison` | `left`, `right`, `note` | 2 栏 |
| `iceberg` | 看得见的一角与看不见的主体不是一回事 | `list` | `surface` | 1–3 条条目 |
| `loop` | 循环往复、每转一圈积累一点 | `diagram` | `gauge` | 3–6 节点 |
| `stairs` | 次数累积带来的位置变化，并在末段翻转视角 | `timeline` | `axis`, `before`, `after` | 2–5 级 |
| `exchange` | 双向关系，两个端点互相选择 | `conclusion` | `leftNode`, `rightNode` | 2 端 |
| `number` | 数值递增、标签和说明 | `number`（共享页面） | 无 | 1 个数值 |

标注键是**组件真正会画出来的那几个**：`figures.js` 声明什么，就必须用 `ann.<键>`
真正写进画面对应元素，测试要求两者严格相等。声明了却没人画的键会造成
「分镜写了、校验器放行、画面上什么都没有」的静默错位，因此不允许存在。
`iceberg` 的水下主体与 `loop` 的循环次数都没有单独标注，它们的信息由条目文案承担。

「默认给」是页面 `DEFAULT_FIGURES` 里的映射：分镜没有声明 `data.figure.kind` 时用它。
分镜声明了就以分镜为准。容量由组件决定：超出后几何会收缩，但标签会挤在一起读不出来，
因此校验器会提醒。

这份目录在服务端有一份镜像 `scripts/a2v/catalog.py`，校验器用它判断
「这个 kind 存不存在、它认识哪些标注键、能吃下多少条目」。
镜像与 `figures.js` 由测试逐项对照，漂移会直接失败。

## 节奏

分镜用 `motion` 指定整幕的快慢，只写名字，不写帧数：

| `motion` | 速度倍率 | 适合 |
| --- | --- | --- |
| `calm` | 0.82 | 金句、收束：让画面慢慢铺开 |
| `normal` | 1 | 默认 |
| `impact` | 1.24 | 信息密集或需要压迫感的一幕：更快进入，后半段留更长的停留 |

实现方式是把「场景内比例点」的绝对帧号整体前移或后移，
因此组件内部不需要各自调参，节奏对整幕一致生效。

## 在分镜里选组件

```json
{
  "id": "fear-source",
  "type": "list",
  "durationInFrames": 240,
  "data": {
    "title": "真正害怕的是什么",
    "items": [
      { "label": "不是失去", "desc": "这份工作本来也不属于你" },
      { "label": "是暴露", "desc": "自己的不足被别人看见" }
    ],
    "figure": {
      "kind": "iceberg",
      "labels": { "tip": "失去", "mass": "被看见的不足", "surface": "水面" },
      "motion": "normal"
    }
  }
}
```

- `kind` 必填；`labels` 的键必须是该组件声明的标注键（拼错只会让标签空着，
  `tests/test_figures_assets.py` 会静态对照一次）；
- `motion` 是整幕的节奏，见上一节；
- `params` **当前不被任何组件读取**：字段与传递机制已经接通，但写了不会改变画面，
  校验器会明确提醒。需要可调几何时，先在组件里实现再放开；
- 旧分镜用的 `data.annotations` 仍然兼容：它和 `figure.labels` 是同一件事。

## 组件契约

```js
A2V.figures.register(kind, {
  labels: ['tip', 'mass', 'surface'],   // 该组件认识的标注键，供文档与测试对照
  markup: '<svg ...>...</svg>',         // 组件自带的 DOM，页面不写任何图形元素
  create: function (ctx) {              // ctx.host 是挂载点
    return {
      update: function (state, api) {   // 逐帧更新，必须是纯函数
        var node = ctx.host.querySelector('[data-el="x"]');
      }
    };
  }
});
```

新组件必须满足：

- **纯函数**：`update` 的结果只由 `state`（帧号、场景、时长）与组件自己的常量决定；
  禁止 `Date.now`、`performance.now`、`Math.random`，禁止 CSS `animation`/`transition`。
  开渲前的静态扫描会连共享资产一起检查。
- **动效走配方层**：入场用 `api.motion.enter` / `api.motion.enterSvg`，弹性用
  `api.motion.spring(api.since(f, start), 'firm')` 这类**具名预设**
  （弹簧收的是秒数，不是进度），幕内微动用 `api.motion.idle`。
  组件里不写自然周期、阻尼比、呼吸周期这些数字——它们决定整支片子的手感，
  只写在 `timeline.js`，见[动效配方层](visual-spec.md#动效配方层-azvmotion)。
- **不读实时布局**：几何由常量与 `params` 推导。确需测量（如 `getTotalLength`、
  `getComputedTextLength`）只在 `buildOnce` 的构建回调里做一次并缓存，
  **不能每帧测**。例外是**容器内文字**：装文字的容器（节点圆、托盘、卡片）
  必须按实测文字宽度定形，不能先写死尺寸再把字塞进去——
  飞轮节点就是反例：半径 76px（直径 152px）配 44px 的四字标签约 183px，文字必然穿出圆。
  测量只在构建时做，运行时的每帧仍只读缓存结果。详见
  [发布会级设计语言](keynote-design-system.md) 的「容器内文字」一节。
- **文案全部来自分镜**：组件可以决定排版，不能决定写什么。
- **容量自适应**：节点/条目数量变化时按数量收缩间距与半径，而不是溢出。
- **自带样式**：样式写在 `figures.css`；颜色、间距、线宽、字重、字距、圆角一律引用令牌
  （`var(--令牌, 原值)`），不写死数值——见设计宪法的 C17。样式要随预设变化时，
  优先挂**基元类**（`.a2v-surface` / `.a2v-label` / `.a2v-connector` / `.a2v-frame`）
  并声明状态（`data-a2v-state="rest|focus|muted|done"`），不要在组件里另发明一套强调写法。
- **容器内文字必须声明容器**：装在某个形状里的文字要写
  `data-a2v-inside="<容器选择器>"`（例如飞轮节点的 `".loop-node-disc"`）。
  观感闸门 K8 据此判定文字有没有穿出容器，而且是**硬判定**。
  只能由组件声明——阶梯的注写在柱子**上方**，同为近邻却不装在容器里，
  几何上无法自动区分。未声明的文字不参与 K8 判定（该幕跳过并写明原因）。

新增后要做四件事：在 `figures.js` 里 `register`（含基元与状态、必要的 `data-a2v-inside`）、
在 `figures.css` 里补样式、在本文档的表格里加一行，
并在 `tests/test_figures_assets.py` 的 kind 列表里登记，确认测试仍然通过。

启用设计语言预设后，`figures.css` 引用的全部 `--fig-*` 令牌由 `keynote.css` 的
两套主题（`keynote-dark` / `keynote-light`）提供；缺一个令牌**不会报错**，
浏览器只会安静地画出透明图形，成片之后才会发现。因此
`tests/test_keynote_assets.py::TestFigureTokenCoverage` 会逐个核对
`figures.css` 用到的每个 `--fig-*` 令牌在两套主题里都有定义。默认（未启用预设）时
这些令牌来自 `theme.css`（深色默认值），预设层不参与。
