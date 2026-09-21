## MODIFIED Requirements

### Requirement: 画面由 React composition 渲染
系统 SHALL 以共享 React composition 作为唯一画面执行者，SHALL 由 Remotion 负责逐帧渲染与编码。composition SHALL 能按分镜选择共享场景树解释器或经过校验的作品级代码场景，但作品 SHALL NOT 自行注册 Remotion 根、composition、契约页或时间轴。

所有可达画面组件 SHALL 通过帧号钩子或共享场景参数取得当前帧，SHALL NOT 依赖挂钟时间、系统随机数、CSS `animation` / `transition` / `@keyframes`，也 SHALL NOT 依赖组件库自带的计时器或布局测量循环。渲染路径 SHALL 在开渲前对共享源码、当前作品可达源码和 CSS 做静态检查，命中禁用写法时 SHALL 报出文件与位置，SHALL NOT 静默继续。

#### Scenario: 使用帧号钩子
- **WHEN** 共享组件或作品代码场景需要计算某个元素在第 N 帧的位置、透明度或数值
- **THEN** 它由帧号与运行时能力算出，结果与求值顺序、真实时间无关

#### Scenario: 组件库自带计时器
- **WHEN** 可达组件树中出现由真实时钟或 CSS 动画驱动的实现，且未经确定性适配
- **THEN** 静态检查报错并指出该组件，渲染不开始

#### Scenario: 随机访问一帧
- **WHEN** 渲染器或验收入口直接跳到任意帧求值两次
- **THEN** 两次得到的画面在确定性阈值内一致

#### Scenario: 作品试图声明独立 composition
- **WHEN** 作品源码调用根注册或声明独立 Remotion composition
- **THEN** 静态检查失败，作品必须由共享 composition 承载

### Requirement: 版本 2 渲染契约
系统 SHALL 提供一个可被浏览器自动化驱动的契约页，把共享 composition 挂载为可寻址的帧序列，并在 `window.__A2V__` 上暴露 `version`、`fps`、`width`、`height`、`durationInFrames`、`ready()` 与 `seekToFrame(frame)`。

`version` SHALL 为 `2`。`ready()` SHALL 在字体、当前作品代码 bundle、首批本地资源就绪且第 0 帧已绘制后 resolve。`seekToFrame(frame)` SHALL 把画面切换到第 frame 帧、暂停播放，并在场景树或代码场景的画面更新完成后 resolve；`frame` 从 `0` 开始，最大值为 `durationInFrames - 1`。

契约 SHALL 由 Remotion 的 Player 实现，SHALL NOT 由每个作品自行实现。`seekToFrame` 返回后，所有场景组件观察到的当前帧 SHALL 等于 `frame`。

#### Scenario: 契约可用
- **WHEN** 浏览器打开契约页并调用 `ready()` 与 `seekToFrame(f)`
- **THEN** 两者按上述语义 resolve，且场景树和代码场景观察到的帧号均等于 `f`

#### Scenario: 声明与分镜不一致
- **WHEN** 契约页报告的 `fps`、`width`、`height` 或 `durationInFrames` 与分镜不一致
- **THEN** 渲染入口报错终止并列出两边的值

#### Scenario: 作品代码或本地资源未就绪
- **WHEN** 代码场景 bundle、字体或首批本地资源加载失败
- **THEN** `ready()` 失败并给出原因，不截取未完成画面

#### Scenario: 版本不匹配
- **WHEN** 页面暴露的 `__A2V__` 版本不是 `2`
- **THEN** 渲染入口报错终止并说明当前支持的契约版本

### Requirement: Python 入口与 Node 渲染器分工
系统的命令行入口 SHALL 继续由现有脚本提供，并 SHALL 保持现有参数与默认输出位置。路径归属推导、分镜与作品源码校验、配音与字幕准备、体检与溯源 SHALL 继续由 Python 侧编排；当前作品代码场景的静态清单生成、前端打包、逐帧渲染与编码 SHALL 交给 Node 侧工具链。

渲染入口 SHALL NOT 要求用户预先进入前端工程目录，也 SHALL NOT 依赖调用时的工作目录。作品源码位于仓库外内容根时，系统 SHALL 通过显式内容根解析并只纳入当前作品允许的文件。

#### Scenario: 命令不变
- **WHEN** 用户沿用既有的校验、预览、渲染、体检命令处理声明式或代码场景
- **THEN** 参数含义与产物位置不变，渲染由共享 Node 侧工具链完成

#### Scenario: 缺少前端依赖
- **WHEN** 前端工程依赖未安装而用户直接渲染
- **THEN** 命令报错并说明需要先安装前端依赖，SHALL NOT 产出一个空成片

#### Scenario: 渲染期离线
- **WHEN** 依赖已安装，字体、作品源码和资产均为本地文件，渲染时无网络
- **THEN** 声明式场景与代码场景均正常完成渲染

#### Scenario: 外部内容根中的代码场景
- **WHEN** 分镜和代码场景位于显式内容根中的规范作品目录
- **THEN** 系统从该内容根解析模块和素材，输出仍按该作品归属推导
