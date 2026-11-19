## REMOVED Requirements

### Requirement: 共享动效组件复用现有原语

**Reason**: L1/L2 展示包装已经退役。
**Migration**: 作品可在本地继续采用确定性原语。

### Requirement: 共享动效组件以进度为唯一时间输入

**Reason**: 本条列出的 L1/L2 展示包装退役。通用确定性和进度约束由原语与代码场景规格覆盖。

### Requirement: 现有风格组件复用共享动效组件

**Reason**: 风格包装和该条引用的通用展示组件均已退役。

### Requirement: 文本排版组件

**Reason**: 专属文本包装无现行作品调用。
**Migration**: 作品按字体和语言需要验证其本地排版。

### Requirement: 图形变换、遮罩与仪表

**Reason**: 展示包装退役，实际采用的圆弧路径由参考原语规格覆盖。

### Requirement: 时间轴与章节轨

**Reason**: Timeline 与 ChapterTrack 包装无现行作品调用。

## MODIFIED Requirements

### Requirement: 共享动效组件提供明确的使用边界

主项目 SHALL 保留仍有消费者的圆弧路径、CSS 样式与 Canvas 绘制参考。CSS 插值与变换可复用 `@remotion/animation-utils`，Canvas 点列、粒子或辉光可复用本地 Painter 或确定性原语。作品直接采用外部实现时 MUST 核对许可、上下文和逐帧适配，并在作品本地声明依赖。

#### Scenario: SVG 路径生长
- **WHEN** 作品需要按进度描绘 SVG 路径
- **THEN** 使用可按显式参数求值的作品本地实现或直接依赖。

#### Scenario: 文本测量
- **WHEN** 作品本地组件根据字体度量排版
- **THEN** 等待实际字体就绪，并按作品的语言与画幅核对结果。

#### Scenario: 图表几何
- **WHEN** 作品绘制纯时间折线或面积
- **THEN** 使用作品本地可重复求值的几何与坐标映射。

#### Scenario: 圆弧路径
- **WHEN** 场景使用 `arcPath` 绘制仪表弧线
- **THEN** 路径仅由几何参数决定，整圆由两段半圆组成。

#### Scenario: Canvas 绘制
- **WHEN** 作品选择沿用参考的 Canvas 点列、粒子或辉光
- **THEN** 使用作品本地的 Painter 或确定性原语，也可采用经验证的本地实现。

### Requirement: 纯时间安全图表

作品采用纯时间图表时，绘制 MUST 由受控时间和显式数据求值，MUST NOT 使用自走的 ECharts 或 `Chart` 封装。图表的坐标、揭示与标注由作品本地实现。可采用本地共享曲线几何或在作品独立声明并锁定合适的外部依赖。

#### Scenario: pure-time 场景使用图表
- **WHEN** 纯时间场景采用本地确定性图表
- **THEN** 场景通过静态闸门，正序与倒序的同一帧得到一致结果。

#### Scenario: ECharts 仍被禁止
- **WHEN** pure-time 场景引入 ECharts 或 `Chart`
- **THEN** 静态闸门拒绝自走动画。

### Requirement: 图表几何统一来源

金融来源参考 SHALL 复用共享点列几何的单调曲线。几何原语支持直线、单调、阶梯与 Catmull-Rom 曲线。金融的业务时间轴与坐标映射由金融来源场景负责。

#### Scenario: 风格平滑曲线
- **WHEN** 金融来源场景绘制按日期排序的价格点列
- **THEN** 使用公共几何生成单调曲线，业务时间与读数沿用金融来源的实际数据口径。
