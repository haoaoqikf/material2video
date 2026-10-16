## MODIFIED Requirements

### Requirement: 画面由 React composition 渲染

系统 SHALL 以共享 React composition 作为唯一画面执行者，SHALL 由 Remotion 负责逐帧渲染与编码。
composition SHALL 按视频类型绘制共享画面，通用类型 SHALL 使用 v7 六模板与本地 React 代码场景在准备阶段录制的无声片段，
但作品 SHALL NOT 自行注册 Remotion 根、composition、契约页或时间轴。

所有可达画面组件 SHALL 通过帧号钩子或共享场景参数取得当前帧，SHALL NOT 依赖挂钟时间、
系统随机数、CSS `animation` / `transition` / `@keyframes`，也 SHALL NOT 依赖组件库自带的
计时器或布局测量循环。渲染路径 SHALL 在开渲前对共享源码和 CSS 做
静态检查，命中禁用写法时 SHALL 报出文件与位置，SHALL NOT 静默继续。
作品 `scenes/` 下的代码场景入口 SHALL NOT 进入 composition：它只在准备阶段的独立录制页运行，
其自由动画不承诺逐像素复现，正式导出只回放已验收片段。

#### Scenario: 使用帧号钩子

- **WHEN** 共享组件需要计算某个元素在第 N 帧的位置、透明度或数值
- **THEN** 它由帧号与运行时能力算出，结果与求值顺序、真实时间无关

#### Scenario: 组件库自带计时器

- **WHEN** 可达组件树中出现由真实时钟或 CSS 动画驱动的实现，且未经确定性适配
- **THEN** 静态检查报错并指出该组件，渲染不开始

#### Scenario: 随机访问一帧

- **WHEN** 渲染器或验收入口直接跳到任意帧求值两次
- **THEN** 两次得到的画面在确定性阈值内一致

#### Scenario: 作品试图声明独立 composition

- **WHEN** 作品声明独立根注册或 Remotion composition（分镜 `code` 幕声明的本地入口除外）
- **THEN** 材料校验失败，作品必须由共享 composition 承载

### Requirement: 渲染契约
系统 SHALL 提供一个可被浏览器自动化驱动的契约页，把共享 composition 挂载为可寻址的帧序列，并在 `window.__M2V__` 上暴露 `version`、`fps`、`width`、`height`、`durationInFrames`、`ready()` 与 `seekToFrame(frame)`。契约页 SHALL 只服务当前仍受支持的 composition 契约。

`version` SHALL 与所选 composition 的契约版本一致；`general` 的讲解 composition 契约 SHALL 为 `6`，与分镜版本相互独立。`ready()` SHALL 在字体、本地资源就绪且第 0 帧已绘制后 resolve。`seekToFrame(frame)` SHALL 把画面切换到第 frame 帧、暂停播放，并在画面更新完成后 resolve；`frame` 从 `0` 开始，最大值为 `durationInFrames - 1`。

契约 SHALL 由 Remotion 的 Player 实现，SHALL NOT 由每个作品自行实现。`seekToFrame` 返回后，所有场景组件观察到的当前帧 SHALL 等于 `frame`。

契约页 SHALL 另外暴露当前帧的只读诊断读数，供验收流程在量测失败时判断画面停在何处；该读数 SHALL NOT 参与 `seekToFrame` 的语义。

#### Scenario: 契约可用
- **WHEN** 浏览器打开契约页并调用 `ready()` 与 `seekToFrame(f)`
- **THEN** 两者按上述语义 resolve，且画面观察到的帧号等于 `f`

#### Scenario: 声明与准备记录不一致
- **WHEN** 契约页报告的 `fps`、`width`、`height` 或 `durationInFrames` 与准备记录不一致
- **THEN** 渲染入口报错终止并列出两边的值

#### Scenario: 本地资源未就绪
- **WHEN** 字体或首批本地资源加载失败
- **THEN** `ready()` 失败并给出原因，不截取未完成画面

#### Scenario: 版本不匹配
- **WHEN** 页面暴露的 `__M2V__` 版本与所选 composition 的契约版本不一致
- **THEN** 渲染入口报错终止并说明当前支持的契约版本
