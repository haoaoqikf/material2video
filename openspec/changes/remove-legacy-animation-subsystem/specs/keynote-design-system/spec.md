## ADDED Requirements

### Requirement: 亮度序与单一强调色

系统 SHALL 只提供一套深色令牌集，并按**亮度序**组织背景、表面与描边：画布、抬升表面与更高一层的明暗关系单调，画面引用语义令牌而不是各自的颜色值。这套令牌 SHALL 只提供一个强调色，画面里同时出现的强调色不超过一个。

#### Scenario: 引用语义令牌而不是颜色值
- **WHEN** 画面需要表面、描边或文字颜色
- **THEN** 取值来自 `var(--m2v-*)` 令牌，改令牌时画面随之变化而不需要改场景代码

#### Scenario: 半透明令牌按合成后的对比度选值
- **WHEN** 新增或修改一条半透明描边或墨色令牌
- **THEN** 它先按 alpha 合成到底色再量对比度，并按用途落到对应下限（数据描边 4.5:1、图形内文本 4.5:1、边界描边 3:1、纯装饰分隔线 1.5:1）

### Requirement: 设计令牌是画面取值的唯一真源

设计语言 SHALL 以令牌形式提供仍被画面消费的取值：画布与安全区尺寸、按亮度序排列的背景与表面色阶、正文与次级墨色、分隔线、单一强调色、字体栈、字号阶、行高与字距阶、间距阶、圆角阶、描边阶、字重阶、图形几何档与图形墨色。令牌 SHALL 由 `web/src/styles/tokens.css` 的**单一** `@theme static` 层定义，画面 SHALL 通过 `var(--m2v-*)` 或 `var(--fig-*)` 引用，SHALL NOT 在场景内写死这些数值。

系统 SHALL NOT 再引入按属性切换的令牌作用域层（例如 `[data-m2v-preset]`、`[data-m2v-theme]`、`[data-m2v-style-pack]`）：作用域层的取值取决于有没有代码给页面挂上那个属性，而一旦没有代码挂它，整层令牌在运行时就是空值，画面会静默落到初始值。

判据是「这个数值改变时，所有画面是不是应该一起变」：是则 SHALL 是令牌，否则视为图稿坐标（立柱位置、节点角度、柱高数组），可以保留为场景自身的常量。

#### Scenario: 令牌是唯一真源
- **WHEN** 修改 `tokens.css` 中某个背景、墨色或字号令牌
- **THEN** 所有引用该令牌的画面同步变化，不需要逐个改场景

#### Scenario: 新增图形颜色令牌必须归类
- **WHEN** 往令牌层里新增一个 `--fig-*` 颜色令牌
- **THEN** 它必须先进入 `tests/test_figure_contrast.py` 的分类表并给出对比度下限，否则该测试失败

## REMOVED Requirements

### Requirement: 主题预设与亮度序

**Reason**: 该要求规定系统提供浅色与深色两套主题令牌集，并规定主题由 composition 的 `theme` 属性选择、不依赖分镜的 `visual.preset`。实际情况是：令牌只有一层且只有深色取值，`[data-m2v-preset='keynote']`、`[data-m2v-theme='light']`、`[data-m2v-style-pack='...']` 三个作用域层没有任何代码会给页面挂上，浅色取值从未被任何画面取到；composition 也没有 `theme` 属性。保留该要求等于承诺一套不存在的能力。
**Migration**: 不需要迁移。画面继续引用 `var(--m2v-*)`，取值来自唯一的深色令牌层；亮度序与单一强调色的约束由新的「亮度序与单一强调色」要求承载。

### Requirement: 模块化设计令牌与兜底取值
**Reason**: 原要求覆盖模块化字号阶、描边阶、字重阶、字距阶、图形几何档与按用途分类的图形颜色令牌，这些只服务已删除的 `keynote.css`、`primitives.css` 与 `SceneTree` 基元层；保留会让规格描述无人消费的令牌族。
**Migration**: 用新的「设计令牌是画面取值的唯一真源」要求；代码场景继续通过 `var(--m2v-*)` 引用仍然存在的表面、墨色、分隔线、强调色、间距、圆角与字体令牌。

### Requirement: 把排版算出来而不是试出来
**Reason**: 排版引擎（`data-m2v-fit` 按实测宽度取字号阶）由已删除的场景树原语与 `SceneTree` 实现；v5 讲解与通用图文各自用固定字号与布局。
**Migration**: 不需要迁移；文案放不下时精简文案或拆幕，不做自动缩字。

### Requirement: 观感闸门
**Reason**: K1–K10 观感闸门的量测实现（`article/keynote.py`、`article/cli.py` 的体检入口）已删除。
**Migration**: 不需要迁移；布局量测保留画布分区溢出、字幕遮挡与容器内溢出三项硬判定，见 article-explainer。

### Requirement: 字号阶是全片唯一的字号真源
**Reason**: 原要求把字号阶的**消费方**（场景树排版引擎）当作约束对象；该引擎与 `keynote.css` 已删除。字号阶本身作为令牌保留，但「全片唯一真源」这一说法在讲解模板用固定字号、代码场景自持图稿坐标之后不再成立。
**Migration**: 用「设计令牌是画面取值的唯一真源」要求承载字号阶作为令牌存在；画面按自己的布局声明字号。

### Requirement: 状态语汇覆盖每一种角色
**Reason**: 四族基元与状态语汇由已删除的 `primitives.css`、`SceneTree` 与 `iconSet` 实现。
**Migration**: 不需要迁移；代码场景自行表达状态。

### Requirement: 两套主题都要过观感闸门
**Reason**: 依赖已删除的 K 闸门与已不存在的浅色主题。
**Migration**: 不需要迁移。

### Requirement: 分镜文案要通过机械规则校验
**Reason**: 分镜文案的机械规则校验由已删除的 v3/v4 分镜校验器实现。
**Migration**: 不需要迁移；v5 分镜结构校验见 article-explainer。

### Requirement: 四族基元 × 四个状态每一格都要落地
**Reason**: 基元与状态矩阵由已删除的 `primitives.css` 与 `SceneTree` 实现。
**Migration**: 不需要迁移。

### Requirement: 重点面上的墨色由设计层给出
**Reason**: 该规则服务于已删除的基元状态语汇；其取值仍在（`--m2v-on-focus`），但没有基元层消费它。
**Migration**: 不需要迁移；代码场景需要时直接引用 `--m2v-on-focus`。

### Requirement: 组件自己拼出的颜色也必须满足对比度门槛
**Reason**: 组件级颜色审计的**执行方**（基元层与场景树组件的颜色抽取）随 `primitives.css`、`SceneTree` 删除，仓库里已没有组件层可供审计。图形颜色令牌的对比度预算本身仍在，并由 `tests/test_figure_contrast.py` 按分类表守住——该测试**未删除**，只是不再审计组件拼色。
**Migration**: 不需要迁移；新增或修改 `--fig-*` 令牌仍须进分类表并通过对比度预算。

### Requirement: 组件内文字不溢出容器
**Reason**: 容器内溢出闸门（K8）由已删除的场景树探针实现。现存唯一布局量测 `explainer_render.py::MEASURE` 只覆盖 `article-narrative` 的 v5 讲解模板，读取的是 `data-m2v-copy` / `data-m2v-box` / `data-m2v-subtitle` / `data-m2v-content` 标记；通用视频的代码场景不参与该量测，`@m2v/scene` 的 `probe()` 目前没有消费者。
**Migration**: 不需要迁移；通用视频的代码场景由作者自行保证文字不溢出。

### Requirement: 画面上的文字都是给读者看的文案
**Reason**: 该要求由已删除的分镜文案校验实现。
**Migration**: 不需要迁移。

### Requirement: 动效不得在帧边界上瞬跳
**Reason**: 动效连续性判据由已删除的 `motionPlan.ts`、`runtime/motionPlan` 与动效量测实现。
**Migration**: 不需要迁移；帧确定性仍是代码场景的硬约束，见 code-driven-scenes。

### Requirement: 设计语言必须覆盖动效与转场令牌
**Reason**: 动效与转场令牌只服务已删除的场景树运行时。时长刻度（`--m2v-dur-*`）仍作为配方参考保留，但画面只由帧号驱动。
**Migration**: 不需要迁移。

### Requirement: v3 分镜必须启用发布会级设计语言
**Reason**: v3 分镜契约已删除。
**Migration**: 重新编排 v5 讲解分镜。

### Requirement: 设计语言的预设启用与校验
**Reason**: 分镜 `visual.preset` 字段随 v3/v4 契约删除，而 composition 也没有替代它的 `theme` 属性——令牌只有一层，不存在「启用哪一套」的问题。
**Migration**: 不需要迁移；画面直接引用唯一的令牌层。

### Requirement: 帧驱动光晕经通道令牌交给设计层
**Reason**: 该机制由已删除的 `keynote.css` 通道令牌与基元层实现。光晕的模糊与浓度档（`--m2v-glow-*`）仍在令牌层，但没有消费者。
**Migration**: 不需要迁移。

### Requirement: 图形基元与状态语汇的作用域
**Reason**: 图形基元由已删除的 `primitives.css` 与 `SceneTree` 实现。
**Migration**: 不需要迁移。

### Requirement: 内容驱动容器保持稳定包含关系
**Reason**: 内容驱动容器由已删除的场景树原语实现。
**Migration**: 不需要迁移。

### Requirement: 内容布局不依赖求帧顺序
**Reason**: 该要求由已删除的场景树布局求解器实现。
**Migration**: 不需要迁移；代码场景的帧确定性仍由 code-driven-scenes 约束。
