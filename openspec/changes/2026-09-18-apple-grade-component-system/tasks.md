## 1. 令牌层：补上描边、字重、字距、图形几何四族

- [x] 1.1 新增 `--a2v-stroke-1..5`（1 / 2 / 3 / 4 / 6px），两套主题同值，注释里写清每一档的用途（发丝边界 / 次级结构 / 数据描边 / 图形主体 / 焦点与运动轨迹）。证据：`keynote.css` 的「描边阶」一节；`figures.css` 的 18 处 `stroke-width` 与 4 处 `1px` 边框全部改为 `var(--a2v-stroke-*, 原值)`。
- [x] 1.2 新增 `--a2v-weight-regular|medium|semibold|bold`（400 / 500 / 600 / 700）；原 `.fig-number` 的 800 在预设下收到 `bold`，未启用预设时仍落回 800。证据：`figures.css` 的 10 处 `font-weight` 全部走令牌。
- [x] 1.3 字距不新造同义族：复用既有的 `--a2v-tracking-*`，在其上按语义收出五槽 `--a2v-track-{numeral,display,body,caption,label}`，把 `figures.css` 的 16 处字面字距（0.01 → 0.14 的近似连续分布）逐值映射到最近一槽。证据：`figures.css` 已无字面 `letter-spacing`。
- [x] 1.4 新增图形几何档 `--fig-node-r-min` / `--fig-surface-pad` / `--fig-connector-w` / `--fig-arrow-len` / `--fig-arrow-half`。**箭镞合并（`.vs-head` 与 `placeArrow` 两套写法收成一份）尚未做**，令牌先就位。
- [ ] 1.5 在 `references/keynote-design-system.md` 增加四族令牌表与分档理由（为什么不是一条 2px 走天下、为什么 5px 并入 6px、为什么字重上限收到 700、为什么字距只留四档）。

## 2. 基元层：四个基元类 + 四个状态

- [x] 2.1 在 `keynote.css` 预设作用域内定义 `.a2v-surface` / `.a2v-label` / `.a2v-connector` / `.a2v-frame`；作用域之外没有任何规则。**当前只有飞轮节点挂上了基元类**，其余七个组件的迁移见第 5 组。
- [x] 2.2 定义 `[data-a2v-state="rest|focus|muted|done"]` 与 `.a2v-surface` / `.a2v-label` 的组合，按 `design.md` D2 的表取值（表面 / 描边 / 文字）。**光晕一项改为由组件自绘**（禁用 `filter`，写入注释与文档）。
- [x] 2.3 状态规则块里不出现 `opacity` 与 `transform`；证据：`keynote.css` 第八节。
- [ ] 2.4 在参考文档里写清「状态只有四个、没有 hover/active/disabled」的理由，以及「结构性类名与连续量不进四态」的边界。

## 3. 组件收口：样式属性一律走令牌

- [x] 3.1 `figures.css` 的 13 处 `gap`、6 处 `padding` 与 3 处 `margin-top` 全部改成 `var(--a2v-space-*, 原值)`，共 22 处；不在 8pt 阶上的取值改到阶上：30 → 32、46 → 48、44 → 48、18 → 16、22 → 24、26 → 24、34 → 32、14 → 16、62 → 64、10 → 8、84 → 96、6 → 4。两处**逐处判断**而非就近取整：`.drop-board` 的栏间距 40 距 32 与 48 等远，取 48（= 2×栅格沟槽，两栏因此落在 12 列栅格上）；`.vs-board` 的 84 落在阶的空档里，取 96（下取 64 会把分隔缩掉 20px，与原本的手感差得太远）。`.drop-panel` 原来的 `26px 20px 24px` 上下不等（26 vs 24）是手调出来的偶然差，收成上下 24 + 左右 16。
- [x] 3.2 18 处 `stroke-width` 全部走令牌，2 / 3 / 4 / 5 / 6 归到五档（5px 并入 6px）。
- [x] 3.3 10 处 `font-weight` 与 16 处 `letter-spacing` 全部走令牌。
- [x] 3.4 8 处字面 `border-radius`（含 `0 0 19px 19px` 这类多值写法）走圆角档 + 回落原值。顺带补掉一处漏网：`.drop-fill` 的 `var(--a2v-radius-sm, 19px) 19px 0 0` 第二个角还是字面值——这处正是新测试抓出来的。
- [ ] 3.5 `figures.js` 里内联写样式的部分（`style.strokeWidth` / `style.fill` / `style.fontSize`）收口到令牌或类；几何坐标按 `design.md` D7 保持原样。
- [x] 3.6 量化前后对比（最终口径，含补漏）：`figures.css` 共新增 **86 处**令牌引用——描边阶 22（18 处 `stroke-width` + 4 处 `border: 1px`）、间距阶 25（19 处 `gap`/`padding` 的多值写法 + 3 处 `margin-top`）、字距槽 16、圆角档 13、字重阶 10。这些属性的字面值从 18 / 10 / 16 / 11 / 17 降到 0（只余 `0` / `auto` 复位值与 `var()` 里的原值兜底）。

## 4. 容器内文字：几何由内容驱动

- [x] 4.1 飞轮节点改成按 `getComputedTextLength()` 实测文字宽度定半径：`r = max(--fig-node-r-min, sqrt((w/2)² + (h/2)²) + --fig-surface-pad)`，逐行数试算取所需半径最小的一种装法，再用 `tspan` 写成单行或多行。证据：`loop` 一幕四段标签不再穿出圆；K8 实测 0 越界。
- [ ] 4.2 双向选择节点、冰山标注、天平载物、阶梯柱顶注四处按同一手法处理。
- [x] 4.3 不使用 `textLength` 横向压缩字形；理由写进 `figures.js` 的注释（压缩会让中文看起来被挤扁，比溢出更难看）。
- [x] 4.4 顺带修掉一处同类缺陷：节点文字原先以 `y = 圆心` 作基线（基线压在圆心上，视觉上比圆心低约 0.35em），现在按行盒中心对齐，单行与多行都以圆心为中心。
- [ ] 4.5 显式验证逐帧稳定性：同一帧重复渲染两次，容器几何与字号一致。

## 5. 状态迁移：把三套机制并到一套

- [ ] 5.1 `is-accent`（iceberg / exchange）与逐帧切换的 `is-focus`（stairs）迁到 `data-a2v-state="focus"`。
- [ ] 5.2 `is-fact` / `is-after` / `is-flat` 按语义拆成「结构类 + `done`/`muted`」。
- [ ] 5.3 `--vs-heat` 与 `--a2v-emphasis-mix` 保留，端点色改用状态令牌。
- [ ] 5.4 落差尺的内联 `height/top` 几何动画保留，颜色/线宽改由状态与令牌决定。
- [ ] 5.5 逐个组件过一遍：表达「当前焦点」的元素都挂 `focus`，且同一帧最多一个。

## 6. 闸门：修 K6 采集，新增 K8 与 K9

- [x] 6.1 修 `inspect.py` 的卡片采集范围：从「挂载点的直接子元素」（`[data-a2v-figure] > *`）扩到整幕（`[data-a2v-figure] *`），并加两条边界——只判**被画出来的 HTML 表面**（有填充/边框/投影之一，且宽高 ≥ 40px），**SVG 里的圆角图形不算卡片**。阈值（≥ 3 项特征）一个字没动：这是**采集范围**的问题，不是阈值的问题（design.md D4）。
- [x] 6.2 核对修复后的结论：`compare` 从「没有可识别的卡片表面」变成 **2 张通过**、`cost` **2 张通过**、`freedom` **1 张通过**。曾经失败的 `compare` 两张卡片位于 `host > .vs-board > .vs-side` 的**深度 2**，`cost` 的两张在深度 3——旧范围看不见任何包在包装元素里的卡片。
      顺带修掉一处让这条闸门长期失效的聚合缺陷：`_SEVERITY` 把 `skipped` 排在 `pass` **之上**，于是「入场帧还没出现、中后段量到了」的幕会被整幕降级成「无法判定」。改为 `skipped` 排在 `pass` 之下——它不是严重程度，是「这一帧没有可测的东西」，只有所有采样帧都跳过才报跳过。
      SVG 图形不纳入卡片判定是有证据的：`opening` 的 `load-solid`/`load-hollow`、`attention` 的 `berg-callout`、`freedom` 的 `stair-bar` 都是圆角矩形，但只有圆角 + 描边——SVG 没有投影与内高光这回事，拿 HTML 卡片的四项特征去量必然「缺项」，会制造 3 处假失败。它们是图解对象，图形纪律由 K9 与图形颜色预算测试管。
- [x] 6.3 新增 **K8 容器内溢出（硬判定）**：由组件用 `data-a2v-inside="<容器选择器>"` 声明所属容器，探针按 `getBBox()` 取用户坐标下的文字盒与容器盒，Python 侧按「矩形内接于圆」判定圆周越界（容差 2px，比 K7 的 8px 小——入场变换对文字与容器一致，相对位置不变）。失败并入错误数与退出码（`_HARD_GATES = ("K7", "K8")`）。
- [x] 6.4 圆的判定已实测；矩形分支已实现但尚无组件使用（随第 4 组一起验证）。
- [x] 6.5 新增 **K9 图形描边一致性（提醒）**：同帧线宽去重后要求落在描边阶上且不超过三档。实测 `keynote-baseline`：attention `[2,3,4]`、freedom `[3,4]`、loop `[4,6]`、opening `[4]`、closing `[4,6]`，全部通过。
- [x] 6.6 **K8 的反例证据已取得**：临时让内容驱动几何不生效（复现「先写死半径再塞字」），K8 报「「打开选项」穿出 .loop-node-disc（圆周）16.0px」等四条、体检错误数 1、退出码 1；恢复后回到 0 错误。

## 7. 字号兜底与字号阶对齐

- [ ] 7.1 量出 `examples/declarative-number` 实际用到哪几个 `--a2v-ink-*` 兜底值。
- [ ] 7.2 只对齐数字组件不用到的兜底（body 统一 38、value 统一 46、lead 统一 62）；`--a2v-ink-display` 保留多值并登记为例外。
- [ ] 7.3 数字组件用到的兜底保持原值并登记例外。
- [ ] 7.4 新增测试断言兜底值与登记一致或在例外清单里。

## 8. 机检（新增测试）

- [x] 8.1 新增 `tests/test_figure_token_closure.py::TestTokenClosure`：`figures.css` 的 `stroke-width` / `font-weight` / `letter-spacing` / `gap` / `padding*` / `margin*` / `border-radius` 全部必须引用令牌（只放行 `0` / `auto` 这类复位值）。
- [ ] 8.2 断言八个组件都挂了基元类与状态属性，且状态取值在四个之内（当前只有飞轮一个组件挂了，随第 5 组一起接）。
- [x] 8.3 断言四个基元类的选择器全部带预设作用域（`TestPrimitivesAndStates::test_primitive_is_preset_scoped`），以及状态取值恰好是四个、四态都有样式。
- [x] 8.4 断言状态规则块里不出现 `opacity` / `transform` / `transition` / `animation` / `filter`。
- [ ] 8.5 断言同一帧最多一个 `focus`（需要运行时探针，随第 5 组一起做）。
- [x] 8.6 补 K8 / K9 的单测：`TestContainerOverflowGate`（越界必 `fail` 并点名文字与容器、贴边未越界必 `pass`、容差吸收亚像素舍入、矩形分支、未声明容器必 `skipped` 且写明原因）与 `TestStrokeConsistencyGate`（阶上且 ≤ 3 档通过、阶外提醒、档数过多提醒、无描边跳过）。
- [x] 8.7 新增 `TestGateAggregation`：实测结论不得被 `skipped` 压过、全部跳过仍报跳过、更严重的状态获胜。
- [x] 8.8 新增兜底契约测试：新族的引用必须带原值兜底，判据是「这个令牌非预设页面有没有」（`--a2v-radius-lg` 由 `theme.css` 提供可以不带，`--a2v-radius-pill` 只在预设里定义就必须带）；并有一组**反向**断言——故意缺席的令牌（`--a2v-accent-deep` / `--a2v-accent-soft-solid` / `--a2v-font-sans`）不许被补上兜底，因为它们缺席时声明失效、元素落到继承值，那正是既有非预设画面的样子，补兜底会把画面改掉。

## 9. 文档与工作流同步

- [ ] 9.1 `references/figure-catalog.md` 增加「新增组件必须挂基元与状态、必须为容器内文字声明 `data-a2v-inside`」的硬要求与新增组件检查单。
- [ ] 9.2 `references/visual-spec.md` 的「排版自查」增加两条：容器内文字不溢出、同一帧最多一个焦点。
- [ ] 9.3 `references/design-constitution.md` 新增 C17（组件走令牌）与 C18（状态语汇唯一，待第 5 组落地后再写），并写进「机检与人工的分工」表。
- [ ] 9.4 `SKILL.md` 的制作流程增加一步：组件改动后跑基元与状态的契约检查。
- [ ] 9.5 同步 `README.md` 的当前状态与 `docs/PROJECT_PLAN.md`；不得把未完成项写成已实现。

## 10. 验收

- [x] 10.1 **非预设逐字节回归通过**：`render.py --storyboard examples/declarative-number/storyboard.json --limit-frames 12 --capture-format png` → `A0A94CFC…`（67185 字节）；去掉 `--capture-format png` → `CBEBD8BF…`（58802 字节）。两者与改动前一致。同时发现并修掉一处陈旧记录：`keynote-design-system.md` 一直写着动效升级前的旧值 `DAFDD423…` / `DF1DB75D…`，照它复现不出来；现在改成实测值，并写明「哈希与机器、工具链相关」。
- [ ] 10.2 跨机器等价性另证（同一组帧逐像素比较）。
- [x] 10.3 逐帧看图确认：`loop-68-f1124.png` 里四段标签已回到圆内（改动前「推到明天」明显穿出圆的两侧）。
- [ ] 10.4 `examples/keynote-baseline` 的 K1–K9 改动前后对照数值写进交付说明。
- [x] 10.5 `uv run pytest` 全绿（569 项）；`openspec validate 2026-09-18-apple-grade-component-system --strict` 通过。
- [ ] 10.6 全仓搜索确认旧写法无残留。
- [ ] 10.7 暂存内容不含生成媒体与缓存，按 AGENTS.md 提交。

## 11. 本轮之后仍未做的（不要当成已有能力）

- 基元与状态只落在飞轮一个组件上（第 2.1 / 第 5 组）：另外七个组件仍各写各的状态。
- `figures.css` 的字号兜底与字号阶仍不一致（第 7 组）。
- 八项机检里还剩 8.2（八个组件的基元/状态覆盖）与 8.5（同一帧最多一个 `focus`），两者都要等第 5 组落地。
- K2 的标定问题（见第 12 节）尚未处理，只是把证据记了下来。

## 12. 下一轮的靶子：强调色"几乎不存在"（K2）

`examples/keynote-baseline` 八幕里**七幕**的 K2 报「几乎没有强调色」，
其中 `opening` 与 `attention` 是 **0.0**——一个强调色像素都没有。

先确认这不是使用量的问题：`figures.css` 里引用 `--a2v-accent` 的地方有 **35 处**，
所以问题不在"没写"，而在两处：

1. **形态太细**。强调色几乎只出现在描边、箭头、短横与圆点上，没有一处是块面。
   实测 `attention` 幕：96% 帧能数到 670px 的**纯**强调色（占比 0.00129），
   而 35% 与 68% 帧里**一个都没有**，最接近的像素是 (106,159,212)，
   与纯强调色 (50,214,255) 的通道最大差是 56——比容差 46 只多 10。
   即便按最宽的一帧算，0.00129 仍低于下限 0.002（≈4150px，约一块 64×64）。
2. **贴合时出现**。强调色元素多在入场末段才淡入，前三分之二帧里画面没有任何焦点色。

两件事要分开判断，不能合并成一个"放宽阈值"的动作：

- **该改组件**：每一幕都应当有一个用强调色**块面**表达的焦点，
  这正是第 5 组「状态迁移」要落地的东西——挂 `data-a2v-state="focus"` 的元素
  由基元层给强强调描边，而不是让每个组件临场决定用多细的线。
- **该改标定**：设计系统自己认可 `--a2v-accent-line`（alpha 0.55）与
  `--a2v-accent-soft`（alpha 0.14）是强调色的合法形态，但 K2 只承认
  与纯强调色通道差 ≤ 46 的像素——**半透明的强调色永远量不到**。
  这是 K2 的系统性盲区：按现在的算法，一个完全用 `--a2v-accent-line` 画的焦点
  会被判成"没有强调色"。
  要不要把 K2 改成量「强调色族」（`accent` / `accent-line` 合成后 / `accent-deep`）
  是一个设计判断，**必须先有第 5 组的落地结果再定**——
  否则就成了"把量不准的闸门调松"，而不是"把画面做对"。

顺序：先做第 5 组（让每幕真的有一个强调色焦点），再看 K2 剩多少缺口，
用那时的数据决定标定该怎么改。
