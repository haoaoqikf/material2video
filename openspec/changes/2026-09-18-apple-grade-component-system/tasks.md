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

- [ ] 3.1 `figures.css` 的 13 处 `gap` 与 4 处 `padding` 改成 `var(--a2v-space-*, 原值)`；**30 / 46 / 18 / 22 / 26 / 34 这些不在 8pt 阶上的取值要改到阶上**。这一组需要逐处判断（不能就近取整了事），留给下一轮。
- [x] 3.2 18 处 `stroke-width` 全部走令牌，2 / 3 / 4 / 5 / 6 归到五档（5px 并入 6px）。
- [x] 3.3 10 处 `font-weight` 与 16 处 `letter-spacing` 全部走令牌。
- [x] 3.4 8 处字面 `border-radius`（含 `0 0 19px 19px` 这类多值写法）走圆角档 + 回落原值。
- [ ] 3.5 `figures.js` 里内联写样式的部分（`style.strokeWidth` / `style.fill` / `style.fontSize`）收口到令牌或类；几何坐标按 `design.md` D7 保持原样。
- [x] 3.6 量化前后对比：`figures.css` 新增 **56 处**令牌引用（`--a2v-stroke/weight/track/radius`），四组属性的字面值从 18 / 10 / 16 / 11 降到 0 / 0 / 0 / 0（圆角 3 处原本已走令牌）。

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

- [ ] 6.1 修 `inspect.py` 的卡片采集范围（从挂载点直接子元素扩到整幕，并对 SVG 元素改用图形自身几何特征）。
- [ ] 6.2 核对修复后 `compare` 一幕的 K6 不再报「没有可识别的卡片表面」。
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

- [ ] 8.1 新增 `tests/test_figure_token_closure.py`：断言 `figures.css` 的 `stroke-width` / `font-weight` / `letter-spacing` / `border-radius` / `padding` / `gap` 全部走令牌（`gap`/`padding` 随第 3 组一起接）。
- [ ] 8.2 断言八个组件都挂了基元类与状态属性，且状态取值在四个之内。
- [ ] 8.3 断言基元与状态规则只存在于预设作用域内。
- [ ] 8.4 断言状态规则块里不出现 `opacity` / `transform`。
- [ ] 8.5 断言同一帧最多一个 `focus`。
- [ ] 8.6 补 K8 / K9 的单测：给 `gate_container_overflow` 喂一个越界的盒必须 `fail`，喂一个贴边但未越界的盒必须 `pass`，没有声明容器的场景必须 `skipped` 且写明原因。

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

- 间距与内边距仍未走 8pt 阶（第 3.1 组）：组件里的 `gap` / `padding` 还是字面值。
- 基元与状态只落在飞轮一个组件上（第 2.1 / 第 5 组）：另外七个组件仍各写各的状态。
- K6 的卡片采集仍未修（第 6.1 组）：`compare` 一幕画面上两张卡片，闸门照旧报「没有可识别的卡片表面」。
- `figures.css` 的字号兜底与字号阶仍不一致（第 7 组）。
- 新增机检测试尚未写（第 8 组）。
