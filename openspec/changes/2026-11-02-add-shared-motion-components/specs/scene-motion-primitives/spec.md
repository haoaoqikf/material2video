## ADDED Requirements

### Requirement: 共享动效组件复用现有原语

共享 L2 组件 SHALL 复用 `primitives.ts` 与 `motion.ts`：`RollingNumber` 使用 `rollNumber`，`BarGrowth` 使用 `growSeries`，L1/L2 的缓动使用 `motion.ts` 的命名曲线或显式 `easing`。MUST NOT 复制一套近似的数字滚动、生长比例或缓动实现。

`primitives.ts` 的五项原语 MUST 继续存在并从 `m2v/code-scene` 导出；本能力 MUST NOT 删除或替换它们。

#### Scenario: 数字滚动
- **WHEN** `RollingNumber` 以 `from`、`to`、`progress` 求值
- **THEN** 其数值与文本来自 `rollNumber`，不再手写取整公式

#### Scenario: 柱状生长
- **WHEN** `BarGrowth` 以进度求值
- **THEN** 各柱比例来自 `growSeries`，不复制 stagger 计算

#### Scenario: 缓动来源
- **WHEN** 共享组件需要缓动
- **THEN** 使用调用方显式传入的 easing 或 `motion.ts` 命名曲线，不内置另一套近似曲线
