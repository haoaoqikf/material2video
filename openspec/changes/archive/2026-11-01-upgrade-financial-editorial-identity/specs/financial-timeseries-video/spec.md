## ADDED Requirements

### Requirement: 可选金融设计档案

`request.json` MAY 提供可选 `design` 对象；缺省时 MUST 使用 `profile: "signal"`、`titleMode: "subject"`、`personality: "corporate"`、无 accent。`design` 不改变投资计算、数据映射、红绿语义、布局边界、裁剪探针或自动验收。

`profile` MUST 为 `ledger`、`signal` 或 `archive`；`titleMode` MUST 为 `subject` 或 `premise`；`personality` MUST 为 `premium`、`corporate` 或 `calm`。`accent` 如提供 MUST 为 `#RRGGBB`，且 MUST NOT 与正收益 `#FF5A4E` 或负收益 `#4BD39A` 完全相同。非法枚举、非法颜色或未知 accent 值 MUST 阻断准备与渲染。

accent MUST 只用于背景径向光晕或极低透明度色场（约 3%–5%），MUST NOT 出现在市值、曲线、端点、坐标、轴标签、标题或底部说明中。红/绿/中性暖白仍只表达收益方向。

#### Scenario: 缺省设计档案
- **WHEN** request 没有 `design`
- **THEN** 使用 signal/subject/corporate，作品正常渲染

#### Scenario: 非法设计档案
- **WHEN** profile、titleMode、personality 或 accent 不合法
- **THEN** 材料校验失败并指出字段，不静默回退

#### Scenario: accent 不进入数据层
- **WHEN** 使用非空 accent 渲染任意帧
- **THEN** accent 只出现在背景，市值、曲线、端点、坐标和文字颜色不变

### Requirement: 金融画面运动分层与开场编排

金融画面 SHALL 按三层组织运动：

- Primary：曲线揭示，完全由日期/投资价值数据驱动，MUST NOT 套装饰性缓动或插值；
- Secondary：市值出现、坐标扩展、年份标签、端点；
- Ambient：背景光晕与噪点。

开场 1 秒 SHALL 形成一次编排：主体名先出现，条件句随后，图表框/网格/本金线淡入，市值与日期在可见时入场。入场 MAY 使用淡入 + 小位移；图表框/网格只改透明度以保持坐标对齐。MUST NOT 使用整屏淡入、扫光、粒子或装饰性运动。

推进段坐标扩展 SHALL 使用共享命名缓入缓出曲线；年份标签 SHALL 淡入并伴随小位移；端点呼吸 SHALL 为低频 ambient，并在结尾前收回。结尾 2 秒 MUST 保持曲线、坐标、市值与日期冻结，不退场、不淡出、不移动。

市值数值 MUST 显示对应真实收盘值，MUST NOT 插值、滚动或平滑到非真实值；动画只作用于出现/退场，不作用于数值本身。

#### Scenario: 开场编排
- **WHEN** 播放第 0–30 帧
- **THEN** 主体名、条件句、图表框和市值按顺序入场，没有整屏淡入或装饰运动

#### Scenario: 坐标扩展
- **WHEN** 日期接近年度阶段边界
- **THEN** 横轴在 15 帧内使用共享缓入缓出曲线扩展，历史点保持完整

#### Scenario: 结尾冻结
- **WHEN** 进入结尾段
- **THEN** 曲线、坐标、市值和日期保持静止，端点呼吸已收回

## MODIFIED Requirements

### Requirement: 手机可读布局与统一说明

画面 MUST 使用注册字体 `M2V Inter` 与 `M2V Sans`，数字 MUST 使用等宽数字样式。顶部 MUST NOT 再显示独立的 64px 大年份。当 `request.design.titleMode` 为 `premise` 时，投资假设标题 MUST 使用 40px、字重 700、字距约 -0.02em、左对齐，无法在安全区保持 26px 时阻断。当 `titleMode` 为 `subject`（默认）时，标题 MUST 分两行：主体名 `displayName` 使用 56px，放不下时降到 48px，仍放不下则阻断；条件句使用 32px，放不下时降到 28px，仍放不下则阻断；主体在上、条件句在下。当前市值 MUST 作为右对齐 hero 金额，字号从 72px 起，按 72/64/56 固定档位适配右侧宽度；其下方 MUST 使用 24px 次文字显示“当前市值 · 最近实际收盘日期”。投资起点前 MUST 隐藏金额与日期。推进阶段 MUST 不显示收益金额或收益率。结尾 MUST 冻结完整曲线与坐标，并与最后推进帧保持相同的金额与日期，期间静止且不淡入。金额 MUST 使用中文数量级并以“元”结尾，数字与单位之间无空格、无千分位。正收益 MUST 为红色 `#FF5A4E`，负收益 MUST 为绿色 `#4BD39A`，持平 MUST 为中性暖白 `#D8D4CC`，市值与曲线同色。背景 MAY 使用 `design.accent` 作为 3%–5% 透明度色场；accent MUST NOT 出现在市值、曲线、端点、坐标、轴标签、标题或底部说明中。绘图区 MUST 为 x=200～920、y=500～1280。纵轴 MUST 只显示 3 个刻度（底、中、顶），字号 24px，右对齐于 x=188，数量级单位 MUST 只在轴顶标注一次，刻度小数位 MUST 按间距决定且不得重复。网格 MUST 只保留 3 条约 9% 透明度的横线，MUST NOT 绘制竖网格或坐标轴线。横轴 MUST 只显示已到达的年份，字号 28px。底部说明 MUST 位于横轴之下，统计口径字号不大于 24px，风险提示不大于 22px。背景 MUST 使用近黑 `#0A0A0B` 径向渐变并叠加极细噪点。标题、金额、图表、端点与底部说明 MUST 作为统一内容组垂直居中于画布 y=960，越界或内容超高 MUST 阻断。统一项目布局边界 MUST 仍为 x=140～940、y=180～1740。核心内容 MUST 通过 360×640 手机缩放检查，纵轴刻度实际高度 MUST NOT 低于约 7px。

#### Scenario: 顶部编辑式层级
- **WHEN** 查看任意推进帧
- **THEN** 顶部只有主体优先或单行投资标题与右对齐 hero 金额，没有独立大年份；金额下方一行小字显示当前市值与日期

#### Scenario: 主体优先标题
- **WHEN** `titleMode` 为 `subject`
- **THEN** 主体名在上、条件句在下，市值与日期仍在右侧，所有文字位于布局边界内

#### Scenario: 单行公式标题
- **WHEN** `titleMode` 为 `premise`
- **THEN** 保留“假如你＋年份＋买入＋本金＋标的”的单行公式，无法保持 26px 时阻断

#### Scenario: 金额档位与颜色
- **WHEN** 当前市值位数变化或收益为正、负、零
- **THEN** 金额在 72/64/56 档位间切换且不逐帧抖动；正收益红、负收益绿、持平中性暖白，曲线同色，accent 不参与数据颜色

#### Scenario: 去轴化后的可读性
- **WHEN** 在 360×640 缩放下检查
- **THEN** 3 个纵轴刻度、单位、横轴年份与底部说明均可辨，纵轴刻度不低于约 7px

#### Scenario: 结尾冻结
- **WHEN** 进入结尾
- **THEN** 曲线、金额与日期冻结，端点呼吸停止，画面静止且不淡入

#### Scenario: 安全区与居中
- **WHEN** 逐帧检查画面
- **THEN** 标题、金额、图表、端点与说明位于 x=140～940、y=180～1740，整体包围盒垂直中心对齐 y=960，越界时阻断

### Requirement: 左侧绘图区空间与折线视觉重量

金融时间序列画面的绘图区 MUST 为 x=200～920、y=500～1280。所有文字 MUST 位于 x=140～940、y=180～1740 的统一布局边界。纵轴刻度 MUST 使用 24px 字号并右对齐于 x=188，超宽标签 MUST 在保持字号的情况下水平压缩。投资价值 MUST 以主曲线与日线双层呈现：主曲线 MUST 按月取真实收盘点并用单调插值连接，线宽 3px；日线 MUST 保留全部真实交易日并以 2px、0.26 透明度绘制。端点半径 MUST 为 7px，外侧增加 14px 同心外环；外环与端点的组合不得越过布局边界。该留白为项目保守默认值，不声明为抖音官方规范。

#### Scenario: 绘图区与端点
- **WHEN** 渲染任意推进帧
- **THEN** 绘图区为 x=200～920、y=500～1280，端点在绘图区右缘内完整显示

#### Scenario: 双层曲线
- **WHEN** 曲线显示已揭示的投资价值
- **THEN** 平滑主曲线与全量日线同时可见，主曲线末点与顶部金额对应同一真实收盘日
