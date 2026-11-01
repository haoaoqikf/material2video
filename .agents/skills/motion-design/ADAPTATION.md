# 项目适配：帧驱动视频运动

上游是一份 UI / 交互动效知识。本文件把它接到 material2video 的帧驱动视频语境；上游的导演原则、编排和时长直觉仍然有效，但实现方式、时间单位和交互场景必须转译。

## 什么时候读

| 场景 | 读取内容 |
|---|---|
| 方案确定：确定运动人格与整体节奏 | `director/core-philosophy.md`、`director/motion-personality.md`、`director/emotion-mapping.md` |
| 逐场设计：入场、退场、转场、镜头行为 | `patterns/entrance-exit.md`、`director/choreography.md`、`director/narrative-structure.md` |
| 多元素编排、数据揭示 | `patterns/multi-element.md`、`director/choreography.md` |
| 时长、缓动、错峰查表 | `reference/timing-easing-tables.md` |
| 动态复核 | `reference/quality-checklist.md`、`reference/troubleshooting.md` |
| 状态反馈、加载、成功/错误 | 只取可迁移的情绪与节奏原则；具体 UI 状态不适用 |

## 毫秒到帧

上游时长表是 UI 起点，不是视频阈值。制作时先按作品实际帧率换算，再按镜头、对象尺度和叙事节拍调整：

| 视频节拍 | 秒 | 30 fps | 60 fps | 典型用途 |
|---|---|---|---|---|
| 微反馈 | 0.1–0.2 | 3–6 | 6–12 | 小标签、按钮式强调、极小位移 |
| 标准动作 | 0.3–0.6 | 9–18 | 18–36 | 对象入场、状态变化、图形生长 |
| 镜头动作 / 揭示 | 0.6–1.2 | 18–36 | 36–72 | 推拉、转向、尺度揭示 |
| 观察停留 | 1.6–4.0 | 48–120 | 96–240 | 结果观察、阅读、情绪消化 |
| 持续环境运动 | 4.0+ | 120+ | 240+ | 背景、粒子、氛围；只在承担表达时使用 |

这些数字是设计起点，不是所有作品通用的门禁。镜头越长、尺度变化越大、信息越复杂，需要的帧数越多；不能用统一秒数裁断所有运动。

## 缓动

共享命名曲线位于 `web/src/code-scene/motion.ts`，相机与原语共用同一套：

| 用途 | 曲线 |
|---|---|
| 入场、抵达、减速落定 | `easeOutCubic` / `easeOutQuint` / `easeOutExpo` |
| 离场、加速离开 | `easeInCubic` / `easeInQuint` / `easeInExpo` |
| 画面内移动、转场 | `easeInOutCubic` / `easeInOutQuint` / `easeInOutExpo` / `easeInOutSine` |
| 回弹、落定 | `backOut` |
| 匀速跟踪、进度、旋转 | `linear`，必须显式并说明用途 |

空间运动 MUST NOT 缺省使用线性。入场用减速家族，离场用加速家族，画面内用两端平滑；匀速跟踪是明确例外。

## 三层运动与不硬套的规则

上游的 primary / secondary / ambient 三层是诊断：

- **不是每镜必备**。项目允许静止、克制和单层运动；环境层只在承担表达时使用。
- 不要把“缺少 ambient”判为失败，也不要用装饰运动填补信息推进问题。
- 1/3 规则、错峰预算和上游危险等级是设计默认与观察提示，**不是自动门禁**；实际判断仍按项目问题分类、完整窗口和表达目标。
- 错峰总预算按镜头节拍确定；上游的 500ms 不是视频通用上限。

## 情绪与人格

上游四种运动人格可作为方案起点，对应本仓库风格：

| 风格 | 人格 |
|---|---|
| `vibe-night` | Premium / Calm |
| `vibe-fable` | Playful |
| `doc-archive` | Corporate / Premium |
| `count-ledger` | Corporate |
| `deep-journey` | Premium / Elegant |

人格只约束缓动、时长和过冲倾向，不决定题材、构图或叙事。作品仍按实际表达调整；无风格作品由设计自行声明人格。

## 采集模式边界

这是上游“可用任意动画库”在本项目中的硬边界：

- `sequential`（默认）：允许在受控时钟下使用 Motion、GSAP、CSS 动画和 R3F `useFrame`；仍须通过确定性源码闸门与成片验收。
- `pure-time`：只接受由帧号、`elapsedSeconds`、`globalSeconds`、`props` 和事件帧推导的纯函数；拒绝 CSS 动效、`useFrame`、ECharts 动画和自走媒体播放。
- `render --jobs N` 并行渲染：与 `pure-time` 相同，只接受可任意 seek 的纯函数。

因此默认实现优先写成帧函数；只有在确实需要且不进入 pure-time / 并行渲染时，才使用动画库。

## 不适用内容

- hover、press、tap、drag、表单校验、页面切换、滚动触发等 UI 交互场景；
- `prefers-reduced-motion`、布局抖动、transform 性能、触摸目标 40px 等 Web 工程规则；
- 把“加载 spinner”“成功粒子”“错误抖动”等组件配方直接搬进视频；
- 用毫秒表直接替代按帧率换算和镜头节拍判断；
- 把上游危险等级当作 CLI 或评审硬门禁。

## 与项目契约的关系

- 运动 skill 是设计与观察方法，不新增命令、评分、阈值、审核轮次或人数。
- 项目既有的分镜字段、帧驱动契约、采集模式、字幕安全区、手机尺寸和审核策略仍然优先。
- 评审者可以加载本 skill，但仍须先盲看落盘、再对照中性条件。
