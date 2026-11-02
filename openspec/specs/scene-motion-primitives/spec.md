# scene-motion-primitives Specification

## Purpose

为通用作品提供一组不内置视觉主题的共享动效原语，把作品给出的 `progress` 映射成可绘制的数值与几何。原语只负责运动本身，降低单条片子的手写动效成本，同时保持逐帧录制的确定性：同一进度与参数在逐帧、跳帧和重录中产生同一画面。

## Requirements

### Requirement: 共享动效原语以进度为唯一时间输入

系统 SHALL 提供以下共享原语，供作品 `scenes/` 导入：数字滚动、数据曲线与柱状生长、列表滚屏、主体状态插值、签名粒子。

每个原语 MUST 只接受 `progress`（0–1）作为时间输入，MUST NOT 读取挂钟时间、帧号、上一帧状态或外部计时器。相同 `progress` 与相同参数 MUST 产生相同画面。

原语 MUST NOT 内置视觉主题；颜色、字体、线宽、粒子参数 MUST 由作品传入。缓动曲线 MUST 由作品显式传入，MUST NOT 使用缺省恒等或任何内置曲线。`linear` MUST 仅用于匀速跟踪、进度或旋转等有说明的用途；空间运动 MUST NOT 缺省使用线性。原语 MUST NOT 被用于关闭信息推进、母题可信度或版式重复问题，也不提供绕过对应复核的默认表现。

#### Scenario: 同一进度重复求值
- **WHEN** 同一原语以相同参数和 `progress` 求值两次
- **THEN** 两次输出一致，不受调用时刻或调用顺序影响

#### Scenario: 未传入缓动
- **WHEN** 作品调用空间原语但没有传入 `easing`
- **THEN** 调用在类型检查或运行时明确失败，不静默回落到线性

#### Scenario: 场景没有传入主题
- **WHEN** 作品只传入默认参数和显式缓动
- **THEN** 原语输出中性几何，不引入预设配色、字体或后期效果

### Requirement: 原语必须支持确定性录制

原语 MUST 在 60 fps 与任意采样帧率下按 `progress` 求值，MUST NOT 依赖逐帧累积状态。包含随机性的原语 MUST 由显式种子决定；未提供种子时 MUST 使用固定默认种子。

原语 MUST NOT 要求播放视频、试听或读取外部资源；其输出 MUST 限于场景画布内的绘制。

#### Scenario: 跳帧采样
- **WHEN** 录制从 0.2 直接跳到 0.8 而不经过中间帧
- **THEN** 该次采样与逐帧播放到同一进度时的输出一致

#### Scenario: 粒子重录
- **WHEN** 同一作品以相同参数重新录制
- **THEN** 粒子位置、数量与形态一致，不因录制次数变化

### Requirement: 原语变更必须使引用作品缓存失效

原语属于共享渲染资产。修改原语实现或默认参数 MUST 使引用它的作品片段缓存失效，并要求重新准备与复查受影响场景；MUST NOT 静默复用旧片段，也不得以"原语未变而场景未变"为由保留旧缓存。

#### Scenario: 修改原语后复用旧片段
- **WHEN** 原语实现变化而作品场景源码未变
- **THEN** 引用该原语的片段判定过期，重新录制后重新完成完整预演

### Requirement: 共享命名曲线库

系统 SHALL 在 `web/src/code-scene/motion.ts` 提供一组只依赖 `progress` 的命名缓动曲线，并从 `m2v/code-scene` 导出。曲线 MUST 为纯函数，输入 0–1、输出可插值数值；MUST NOT 读取时间、随机源或外部状态。

曲线库 SHALL 至少覆盖：线性、缓入、缓出、缓入缓出、指数缓出、回弹落定和五阶缓入缓出。命名 SHALL 表达方向与强度，不表达具体品牌或主题。相机与原语 SHALL 共用同一套命名，不得各自维护重复曲线。

#### Scenario: 曲线端点
- **WHEN** 任一命名曲线以 0 或 1 求值
- **THEN** 输出分别为 0 和 1；回弹曲线在结束前可以超出 0–1，但最终收敛到 1

#### Scenario: 相机和原语共用曲线
- **WHEN** 镜头与原语都使用缓出曲线
- **THEN** 二者引用同一个命名与实现，不出现两套近似但不一致的曲线

### Requirement: 轨迹、爆散与字幕原语

系统 SHALL 在 `web/src/code-scene/` 提供以下纯数值原语，并从 `m2v/code-scene` 导出：

- `samplePath`：按弧长把单子路径 SVG path 采样为等距点；多子路径 MUST 明确失败，不把不连续段当作一条轨迹；
- `sampleTrail`：沿点列按 `progress` 与尾迹长度采样位置、切线、年龄与透明度；
- `burstField`：按显式种子、原点、方向、速度、阻力、重力、寿命与 `progress` 计算粒子位置、尺寸与透明度；
- `expandingRings`：每个环独立出生、半径与透明度，按 `progress` 与错峰求值；
- `dissolvePair`：返回互补的旧层与新层不透明度；
- `staggerReveal`：返回每个字符的 0–1 进度，步长压缩在窗口内；
- 字幕原语：激活窗口查询、两行切分、窗口包络与关键词切分。

所有原语 MUST 只接受显式 `progress`/0–1 进度、显式种子与显式缓动，MUST NOT 读取挂钟、帧号、上一帧状态、DOM、外部资源或计时器。相同参数与进度 MUST 产生相同输出。端点 MUST 透明或零值，不留下上一帧残影。原语 MUST NOT 内置颜色、字体、线宽、题材或事件时刻。

路径采样与锥形笔触 MAY 复用 MIT 许可的 `svg-path-properties` 与 `perfect-freehand`；引入第三方纯函数 MUST 在 `m2v/code-scene` 内封装，风格组件与作品 MUST NOT 直接导入。新增动效或可视化组件前 MUST 先检索并评估外部成熟方案，只有在无法满足逐帧确定性、许可、包体或风格边界时才允许自研，并在设计记录中写明结论。

#### Scenario: 同一进度重复求值

- **WHEN** 任一新增原语以相同参数与 `progress` 求值两次
- **THEN** 两次输出一致，不受调用时刻、调用顺序或已播放帧数影响

#### Scenario: 跳帧与端点

- **WHEN** 录制从 0.2 直接跳到 0.8，或求值 `progress` 为 0 与 1
- **THEN** 跳帧结果与逐帧求值一致，粒子、环与尾迹在端点为透明或零值

#### Scenario: 多子路径

- **WHEN** 把含多个 `M` 子路径的图标传给 `samplePath`
- **THEN** 调用明确失败并提示单子路径限制，不返回跨子路径的连续点列

#### Scenario: 未检索直接手写

- **WHEN** 新增的动效或可视化组件没有外部方案检索记录，或选型理由未写入设计记录
- **THEN** 审查判定不符合协作约定，须补检索与记录后再实施

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
