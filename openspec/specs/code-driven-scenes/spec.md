# code-driven-scenes Specification

## Purpose

允许作品在固定依赖与确定性边界内使用自由 React/TypeScript 场景表达独特构图、图表、关系图和 SVG，同时保持分镜单一真源、离线渲染、可审查与可重复验收。

## Requirements

### Requirement: 代码场景使用固定能力白名单

代码场景 SHALL 只允许使用 React、React DOM、Remotion、Tailwind、ECharts、Dagre、Lucide、原生 HTML/JSX、原生 SVG、CSS、TypeScript 表达式以及项目公开的内部模块。作品 SHALL NOT 声明、安装、动态下载或导入其他 npm 包；允许包的版本 SHALL 由共享前端工程统一锁定。

#### Scenario: 使用允许的视觉能力

- **WHEN** 代码场景使用 Remotion 帧 API、Tailwind 类、ECharts、Dagre、Lucide 或内联 SVG
- **THEN** 依赖检查通过，并使用共享工程锁定的实现参与打包

#### Scenario: 导入非白名单包

- **WHEN** 作品模块直接或间接导入白名单之外的裸模块
- **THEN** 构建前校验失败，报告导入者、包名和导入位置，且不会尝试安装该包

### Requirement: 自由表达式不得突破执行边界

代码场景 SHALL 可以使用普通 TypeScript 表达式、条件渲染、数组变换和组件组合，但 SHALL NOT 使用动态代码求值、动态模块加载、Node 内置能力、进程或文件系统访问、网络请求、外部脚本、外部样式、远程媒体或远程字体。系统 SHALL 在源码检查与渲染期网络阻断两层执行该边界。

#### Scenario: 使用本地表达式组合画面

- **WHEN** 场景以局部数据执行映射、过滤、数学计算和 JSX 条件渲染
- **THEN** 代码可正常构建并按当前帧求值

#### Scenario: 尝试执行动态或远程内容

- **WHEN** 可达源码包含 `eval`、动态函数构造、动态导入、网络 API 或外部 URL 资源
- **THEN** 校验或运行期隔离使流程失败，并给出可定位诊断，不交付成片

### Requirement: 代码场景保持帧确定性

代码场景的可见状态 SHALL 是分镜、已锁定本地资产和当前帧号的确定性函数。代码与样式 SHALL NOT 使用挂钟、系统随机数、计时器、浏览器动画循环、CSS `animation`、CSS `transition` 或第三方库内置时间轴推进画面。需要伪随机效果时 SHALL 使用项目提供的稳定种子随机能力。

#### Scenario: 同帧重复求值

- **WHEN** 同一代码场景以相同输入和帧号重复绘制
- **THEN** 两次画面达到现有确定性相似度门槛

#### Scenario: 使用非确定性入口

- **WHEN** 可达源码或 CSS 使用真实时间、`Math.random`、计时器、动画循环或 CSS 时间动画
- **THEN** 静态检查失败并报告文件与位置，预览和渲染均不开始

### Requirement: 白名单视觉库采用确定性适配

ECharts SHALL 禁用内置动画并由帧号生成当前数据或状态；Dagre SHALL 仅以稳定排序的输入和固定配置计算布局，且 SHALL NOT 随帧重排；Lucide SHALL 作为静态 SVG 组件使用；原生 SVG 的动态属性 SHALL 由帧号计算。相同输入下，各适配结果 SHALL 可重复。

#### Scenario: 帧驱动图表

- **WHEN** ECharts 图表需要柱长、数值或路径随时间变化
- **THEN** 当前图表状态由帧进度计算，ECharts 自身动画保持关闭

#### Scenario: 稳定关系图布局

- **WHEN** Dagre 对同一组已稳定排序的节点、边和配置执行布局
- **THEN** 重复得到相同节点坐标与连线路由，动画只作用于其可见状态

### Requirement: 作品源码进入构建与溯源闭环

系统 SHALL 在构建前生成只包含当前作品代码场景的静态场景清单，并 SHALL 使作品 TSX、CSS、SVG 与本地媒体参与模块解析、Tailwind 内容扫描和成片源码指纹。预览、评审与导出 SHALL 使用同一清单和同一 bundle。

#### Scenario: Tailwind 类来自作品源码

- **WHEN** 作品代码使用可静态发现的 Tailwind 完整类名
- **THEN** 预览和导出均包含对应样式且画面一致

#### Scenario: 作品源码修改后检查旧成片

- **WHEN** 已渲染成片之后修改代码场景、CSS、SVG 或其本地资产
- **THEN** 溯源检查把旧成片判为落后并指出变化的输入

### Requirement: 作品可以在幕上声明代码场景
作品 SHALL 在 `general-plan.json` 的幕上以 `renderer: { kind: "code", module: "<scenes/ 下的模块标识>" }` 声明代码场景；模块标识 SHALL 解析到当前作品 `scenes/` 目录内的真实模块，该模块 SHALL 默认导出 `M2VCodeScene` 组件。共享层 SHALL 注入该幕的 `data`、幕内帧与幕内进度、`fps`、画布尺寸、主题与按幕标识播种的稳定随机源；模块 SHALL NOT 自行决定幕顺序、总时长或字幕边界。

#### Scenario: 幕级模块进入全片时间轴
- **WHEN** 作品的某一幕声明 `renderer.kind` 为 `code`
- **THEN** 该幕的预览、预演与导出使用同一模块，并落在该幕在全片中的帧区间内

#### Scenario: 模块缺失或没有规定导出
- **WHEN** 幕引用的模块无法解析、逃出 `scenes/` 或没有默认导出规定的场景组件
- **THEN** 校验在启动浏览器或渲染前失败，并指出该幕的 `renderer.module` 与目标源码位置

#### Scenario: 同一幕同时声明 renderer 与内联内容
- **WHEN** 一幕既声明 `renderer` 又声明该幕类型自带的内联图文内容
- **THEN** 校验拒绝该幕，要求二选一

### Requirement: 代码场景接收幕级上下文槽位
共享层 SHALL 向代码场景注入幕标识、幕数据、幕内帧与幕内进度、`fps`、画布尺寸、主题与稳定随机源，并 SHALL 保留类型化的 `beats`、`motion` 与 `objectStates` 槽位。通用视频当前不提供语义节拍、镜头运动与跨幕对象状态，这些槽位 SHALL 以文档化的空值传入（`beats.current` 为 `null`、`beats.plan` 为空、`motion.camera.kind` 为 `"none"`、`motion.continuity` 为 `null`、`objectStates` 为空对象）；代码模块 SHALL NOT 假设这些槽位被填充。

#### Scenario: 同一帧重复求值得到同一上下文
- **WHEN** 以任意顺序、任意次数求同一幕的同一帧号
- **THEN** 代码场景收到相同的幕数据、幕内帧、幕内进度与随机序列

#### Scenario: 代码场景读取空镜头槽位
- **WHEN** 代码场景读取 `motion.camera`
- **THEN** 读到文档化的空镜头（`kind` 为 `"none"`），并据此走无镜头分支而不是抛错
