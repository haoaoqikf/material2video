# code-driven-scenes Specification

## Purpose

允许作品在固定依赖与确定性边界内使用自由 React/TypeScript 场景表达独特构图、图表、关系图和 SVG，同时保持分镜单一真源、离线渲染、可审查与可重复验收。

## Requirements

### Requirement: 作品可以声明代码场景
作品 SHALL 在 world.renderer 声明一个通过稳定模块标识引用的全片代码模块。共享层 SHALL 注入分镜内容、全局帧与进度、阶段上下文、fps、画布、主题和全局状态；模块 SHALL NOT 自行决定阶段顺序或时长。

#### Scenario: 单一全片模块
- **WHEN** 作品选择 code renderer
- **THEN** 预览、评审和导出全片使用同一模块与时间轴

#### Scenario: 模块缺失
- **WHEN** 模块无法解析或没有规定导出
- **THEN** 启动浏览器前失败并定位 world.renderer.module

#### Scenario: 一支作品混用两种场景
- **WHEN** 分镜试图在不同阶段混用 tree 和 code
- **THEN** 校验拒绝阶段 renderer，要求选择一个全片 renderer

#### Scenario: 代码模块不存在

- **WHEN** 分镜引用的作品级代码模块无法解析或没有导出规定的场景组件
- **THEN** 校验在启动浏览器或渲染前失败，并指出场景字段与目标模块

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

### Requirement: 代码场景继续接受统一体检

每个代码场景 SHALL 暴露稳定场景标识、节点标识、语义角色和容器归属标记，使共享契约探针能够读取文本、定位节点、检查安全区与溢出并扫描帧驱动动效。缺少最低探针信息的代码场景 SHALL NOT 通过严格评审。

#### Scenario: 代码场景通过统一评审

- **WHEN** 代码场景按契约标记标题、正文、图表和容器
- **THEN** 现有内容探针、C/K/M 系列闸门在同一契约页上量测该场景

#### Scenario: 场景没有可观察标记

- **WHEN** 代码场景渲染了内容但未提供规定的场景与节点标识
- **THEN** 严格评审失败并指出对应场景，成片不得标记为验收通过

### Requirement: 作品源码进入构建与溯源闭环

系统 SHALL 在构建前生成只包含当前作品代码场景的静态场景清单，并 SHALL 使作品 TSX、CSS、SVG 与本地媒体参与模块解析、Tailwind 内容扫描和成片源码指纹。预览、评审与导出 SHALL 使用同一清单和同一 bundle。

#### Scenario: Tailwind 类来自作品源码

- **WHEN** 作品代码使用可静态发现的 Tailwind 完整类名
- **THEN** 预览和导出均包含对应样式且画面一致

#### Scenario: 作品源码修改后检查旧成片

- **WHEN** 已渲染成片之后修改代码场景、CSS、SVG 或其本地资产
- **THEN** 溯源检查把旧成片判为落后并指出变化的输入

### Requirement: 代码场景接收统一导演运行时上下文
共享层 SHALL 注入全局 beats、阶段语义状态、全片镜头与对象状态，不提供幕级跨场景转场上下文。代码模块 SHALL 可通过共同上下文编排复杂动作；系统不自动猜测内部节点或生成对象动画。

#### Scenario: 随机访问上下文
- **WHEN** 直接访问后一阶段帧
- **THEN** 得到与 tree 相同的全局 beat、阶段、镜头和已累计状态

#### Scenario: 代码场景跟随镜头段
- **WHEN** 当前阶段进入绑定 beat 的推进镜头段
- **THEN** 代码场景收到与场景树相同的镜头进度和焦点信息，并在随机寻帧时得到相同上下文

### Requirement: 代码场景显式加入节点级连续性
全片代码模块 SHALL 为持续对象暴露稳定节点 id、几何、语义角色和容器标记，以便验证状态与镜头连续性。缺少被引用节点的探针 SHALL 使严格评审失败，不得降级为独立场景转场或猜测 DOM。

#### Scenario: 探针完整
- **WHEN** 全片模块暴露持续对象探针
- **THEN** 评审可跟踪阶段边界对象身份、状态与几何

#### Scenario: 探针不足
- **WHEN** 镜头或评审目标缺少规定探针
- **THEN** 明确报错并阻断正式输出，无场景级转场回退

#### Scenario: 探针不完整
- **WHEN** 全片代码对象缺少被镜头或连续性评审引用的稳定几何或外观
- **THEN** 严格评审失败并说明对象和缺失探针，不降级为场景转场
