# 视觉组件目录

组件库回答一个问题：**这一幕画面用什么表达**。AI 做导演——从目录里挑一个组件、
给几段短标注、指定节奏——而不是每次都从零画一遍。目录里确实没有合适的时候，
再按 [组件契约](#组件契约) 新写一个，并把这个组件沉淀回目录。

- 组件代码：`web/src/components/<Kind>.tsx`（结构 + 逐帧逻辑），
  样式在 `web/src/styles/figures.css`，共享几何与动效原语在 `web/src/runtime/figures.tsx`
- 挂载方式：共享 React composition（`web/src/compositions/A2VComposition.tsx`）
  按分镜逐幕挂载组件；组件从 `useFigure()` 取帧号与场景，作品不需要任何页面代码
- 文案来源：分镜的 `data` 与 `data.figure.labels`，组件不保存任何默认文案
- 组件集合的唯一真源：`web/src/registry/registry.json`（本目录的组件表由它生成）

## 现有组件

<!-- >>> generated:figures-table >>> -->
| `kind` | 状态 | 适合表达 | 默认给 | 标注键 | 容量 |
| --- | --- | --- | --- | --- | --- |
| `balance` | 已实现 | 一边重一边轻，随后证明重的那个是空壳 | `title` | `leftPan`, `rightPan` | 2–2 侧 |
| `gap` | 已实现 | 量出真正失去了多少：一侧从满到空，另一侧从头就没有 | `quote` | `assumption`, `fact`, `dropLabel`, `noDropLabel` | 2–2 栏 |
| `iceberg` | 已实现 | 看得见的一角与看不见的主体不是一回事 | `list` | `surface` | 1–3 条条目 |
| `loop` | 已实现 | 循环往复，每转一圈积累一点 | `diagram` | `gauge` | 3–6 节点 |
| `stairs` | 已实现 | 次数累积带来的位置变化，并在末段翻转视角 | `timeline` | `axis`, `before`, `after` | 2–5 级 |
| `exchange` | 已实现 | 双向关系，两个端点互相选择 | `conclusion` | `leftNode`, `rightNode` | 2–2 端 |
| `versus` | 已实现 | 两种反应并排，箭头指出该从哪边转向哪边 | `comparison` | `left`, `right`, `note` | 2–2 栏 |
| `number` | 已实现 | 按帧递增显示数值，并展示标签与说明 | `number` | 无 | 1–1 个数值 |
| `chart` | 已实现 | 柱状/折线/饼图：数据序列随帧显影，关键数值同步输出为 DOM 文本 | `chart` | `unit`, `note` | 2–6 个数据点 |
| `flow` | 已实现 | 因果链/流程步骤：dagre 分层布局，自上而下逐步连线，节点文字按实测宽度定形 | — | 无 | 2–6 节点 |
<!-- <<< generated:figures-table <<< -->

（这张表由 `web/src/registry/registry.json` 生成：`uv run python .agents/skills/article2video/scripts/sync_catalog.py`。手改会被 `--check` 判为落后。）

`chart` 的实现在 React 工程（`web/src/components/Chart.tsx` 与 `web/src/charts/`），
用 ECharts 按需引入画在 **canvas** 上：轴与范围由完整数据一次算定、不参与动画，
每帧只把新的显影进度换算成数据切片重画（`animation: false`，同一帧求值两次逐像素一致）。
canvas 内部的文字探针量不到，因此组件把每个数值以**最终值**同步输出为 DOM 文本
（`data-el="value-<序号>"`），K7/K8 对图表内部的判定范围会在体检报告里写明。
分镜声明 `figure.schematic: true` 时，画面自动出现「示意」标——
无来源数值不许长得像实测结果。

`flow` 的实现同样只在 React 工程（`web/src/components/Flow.tsx` 与 `web/src/flow/`）：
分层布局由 dagre 的**纯函数外壳**算出（同一份节点与连线布局两次逐值相同），
节点与连线自绘 SVG，节点盒子按实测文字宽度定形（K8 硬判定有真实的量测对象），
连线长度是解析值、在布局确定时算好缓存，每帧只把帧号换成描边进度——
不调用 `getTotalLength()`。没有声明 `edges` 时按节点顺序连成链；
声明了就以声明为准（空数组就是不要连线）。

标注键是**组件真正会画出来的那几个**：组件声明什么，就必须把对应的键真正写进
画面对应元素。声明了却没人画的键会造成「分镜写了、校验器放行、画面上什么都没有」
的静默错位，因此不允许存在——`tests/test_web_registry.py` 会把注册表里声明的键
与组件实现源码逐个对照，漂移直接失败。
`iceberg` 的水下主体与 `loop` 的循环次数都没有单独标注，它们的信息由条目文案承担。

`loop` 的环上**每个节点占一个位置**：一圈的停位数等于节点数，弧线按相邻节点
逐段拼接（四节点就是四段 90° 弧闭合成整圆），小球走满 `节点数 × 2` 格正好
两整圈、回到起点。停位数不许写死——写死会让节点数不同的分镜出现两点重合，
整步论证在画面上消失。

`versus` 的**右栏是焦点**：它挂 `a2v-surface` + `data-a2v-state="focus"`，
底色来自表面基元（左栏是 `rest`）。它曾经只用一条 1px 暖边框加光晕表达焦点，
底色永远不变，整幕强调色占比 0.0016（门槛 0.002）——焦点只有描边、没有块面。
随 `--vs-heat` 升温的边框与光晕保留，那是"箭头到达"的强调，与状态无关。

`versus` 的**两栏是这一幕的载荷**，在预设下均分安全区宽度（板面 100%），
选项文字取 `lead`（60px）这一档、由 autofit 按可用宽度自减——**不能低于幕标题
的量级**，否则"要看的东西比问题还小"，层级是倒的。左栏是基准态、右栏是焦点，
两栏等宽并排才读得出"从哪边转向哪边"。

「默认给」是注册表 `defaultKindByScene` 里的映射：分镜没有声明 `data.figure.kind`
时用它。分镜声明了就以分镜为准。容量由组件决定：超出后几何会收缩，但标签会
挤在一起读不出来，因此校验器会提醒。

这份目录在服务端有一份镜像 `scripts/a2v/catalog.py`，校验器用它判断
「这个 kind 存不存在、它认识哪些标注键、能吃下多少条目」。镜像由
`web/src/registry/registry.json` 生成（`scripts/sync_catalog.py`），
不是第二份手抄——手改派生文件会被机检判为落后。

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
      "labels": { "surface": "水面" },
      "motion": "normal"
    }
  }
}
```

- `kind` 必填；`labels` 的键必须是该组件声明的标注键（拼错只会让标签空着，
  `tests/test_web_registry.py` 的标注键机检会拦下「声明了却不画」的键）；
- `motion` 是整幕的节奏，见上一节；
- `params` **当前不被任何组件读取**：字段与传递机制已经接通，但写了不会改变画面，
  校验器会明确提醒。需要可调几何时，先在组件里实现再放开；
- 旧分镜用的 `data.annotations` 仍然兼容：它和 `figure.labels` 是同一件事。

## 组件契约

一个组件是一个 React 函数组件：从 `useFigure()` 取帧号与场景声明，
把「这一帧该长什么样」完整地算出来。分镜不需要写任何挂载代码——
composition 按注册表把组件挂到对应场景上。

```tsx
export function LoopFigure() {
  const { frame, fps, data, spec, active } = useFigure();
  const sceneDuration = useVideoConfig().durationInFrames;
  // …由 frame 推导每个元素的进度，再交给动效原语换算成样式
  return (
    <svg …>
      <g className="a2v-connector" data-a2v-state={state}>…</g>
    </svg>
  );
}
```

新组件必须满足：

- **纯函数**：画面的每一项只由帧号、场景与时长决定。禁止 `Date.now`、
  `performance.now`、`Math.random`，禁止 CSS `animation`/`transition`——
  渲染前的静态扫描会拒绝。
- **动效走配方层**：入场用 `enterStyle` / `drawPathStyle` 这类原语，弹性用
  `spring(f, start, SPRINGS['enter'])` 这类**具名预设**（弹簧收的是秒数，不是进度），
  节奏用 `beat(fig, fraction)` 换算比例点。组件里不写自然周期、阻尼比、
  呼吸周期这些数字——它们决定整支片子的手感，只写在
  `web/src/runtime/motion.ts`，见[动效配方层](visual-spec.md#动效配方层)。
- **不拿阶跃量驱动显著元素**：曲线再自然，被驱动的量本身是阶跃的，画面上
  就是一次瞬跳。数字幕的滚动因此有最小步数门槛——步数不足就不滚，
  直接显示最终值。同理，画面上**可读**（不透明度 ≥ 0.5）的文字必须等于它的最终值。
- **不读实时布局**：几何由常量推导；确需测量（文字宽度、换行）只在挂载时做一次
  并缓存（`useLayoutEffect` + 依赖签名），**不能每帧测**。
  例外是**容器内文字**：装文字的容器（节点圆、托盘、卡片）
  必须按实测文字宽度定形，不能先写死尺寸再把字塞进去——
  飞轮节点就是反例：半径 76px（直径 152px）配 44px 的四字标签约 183px，文字必然穿出圆。
  测量只在挂载时做，运行时的每帧仍只读缓存结果。详见
  [发布会级设计语言](keynote-design-system.md) 的「容器内文字」一节。
- **文案全部来自分镜**：组件可以决定排版，不能决定写什么。
- **容量自适应**：节点/条目数量变化时按数量收缩间距与半径，而不是溢出。
- **自带样式**：样式写在 `web/src/styles/figures.css`；颜色、间距、线宽、字重、字距、
  圆角一律引用令牌（`var(--令牌, 原值)`），不写死数值——见设计宪法的 C17。
  样式要随状态变化时，优先挂**基元类**（`.a2v-surface` / `.a2v-label` /
  `.a2v-connector` / `.a2v-frame`）并声明状态
  （`data-a2v-state="rest|focus|muted|done"`），不要在组件里另发明一套强调写法。
- **容器内文字必须声明容器**：装在某个形状里的文字要写
  `data-a2v-inside="<容器选择器>"`（例如飞轮节点的 `".loop-node-disc"`）。
  观感闸门 K8 据此判定文字有没有穿出容器，而且是**硬判定**。
  只能由组件声明——阶梯的注写在柱子**上方**，同为近邻却不装在容器里，
  几何上无法自动区分。未声明的文字不参与 K8 判定（该幕跳过并写明原因）。

新增组件的完整登记清单见
[文章生成分镜](article-to-storyboard.md#组件不足时的处理)：
在 `registry.json` 登记元数据、在 `web/src/registry/index.ts` 接上组件本体、
写实现与样式，然后运行生成命令并让机检通过：

- `tests/test_web_registry.py`：注册表与生成物一致、标注键声明与绘制两向对照、
  默认映射自洽；
- `pnpm -C web test`：渲染层消费注册表的自洽性（`web/src/registry/registry.test.ts`）；
- `tests/test_figures_assets.py`：旧资产与新目录的交集仍逐项一致；
- `tests/test_keynote_assets.py::TestFigureTokenCoverage`：组件样式用到的每个
  `--fig-*` 令牌在 `keynote.css` 的两套主题里都有定义——缺一个令牌**不会报错**，
  浏览器只会安静地画出透明图形，成片之后才会发现。默认（未启用预设）时
  这些令牌来自 `theme.css`（深色默认值），预设层不参与。
