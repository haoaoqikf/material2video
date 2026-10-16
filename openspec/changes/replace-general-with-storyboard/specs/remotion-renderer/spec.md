
## MODIFIED Requirements

### Requirement: 画面由 React composition 渲染

系统 SHALL 以共享 React composition 作为唯一画面执行者，SHALL 由 Remotion 负责逐帧渲染与编码。
composition SHALL 按视频类型绘制共享画面，通用类型仅使用 v6 六模板，
但作品 SHALL NOT 自行注册 Remotion 根、composition、契约页或时间轴。

所有可达画面组件 SHALL 通过帧号钩子或共享场景参数取得当前帧，SHALL NOT 依赖挂钟时间、
系统随机数、CSS `animation` / `transition` / `@keyframes`，也 SHALL NOT 依赖组件库自带的
计时器或布局测量循环。渲染路径 SHALL 在开渲前对共享源码和 CSS 做
静态检查，命中禁用写法时 SHALL 报出文件与位置，SHALL NOT 静默继续。

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

- **WHEN** 作品声明代码场景、独立根注册或 Remotion composition
- **THEN** 材料校验失败，作品必须由共享 composition 承载

### Requirement: Python 入口与 Node 渲染器分工

系统的命令行入口 SHALL 继续由现有脚本提供，并 SHALL 保持现有参数与默认输出位置。
路径归属推导、分镜校验、配音与字幕准备、体检与溯源 SHALL 继续由 Python 侧编排；
前端打包、逐帧渲染与编码 SHALL 交给 Node 侧工具链。

渲染入口 SHALL NOT 要求用户预先进入前端工程目录，也 SHALL NOT 依赖调用时的工作目录。
作品材料位于仓库外内容根时，系统 SHALL 按作品目录解析本地素材。

启用配音媒体清单时，系统 SHALL 把清单派生的分镜时长（每幕实际 `durationInFrames`）
写回源分镜快照形成有效分镜，并 SHALL 把有效分镜作为 composition 的 props 提供给
契约页与 Remotion 渲染；SHALL NOT 让画面按声明时长运行而音轨按派生时长合成。
作品归属 SHALL 使用原始材料路径。

#### Scenario: 命令不变

- **WHEN** 用户沿用既有的校验、预览、渲染、体检命令处理当前类型的材料
- **THEN** 参数含义与产物位置不变，渲染由共享 Node 侧工具链完成

#### Scenario: 缺少前端依赖

- **WHEN** 前端工程依赖未安装而用户直接渲染
- **THEN** 命令报错并说明需要先安装前端依赖，SHALL NOT 产出一个空成片

#### Scenario: 渲染期离线

- **WHEN** 依赖已安装，字体、作品源码和资产均为本地文件，渲染时无网络
- **THEN** 共享 composition 正常完成渲染

#### Scenario: 外部内容根中的代码场景

- **WHEN** 分镜位于显式内容根中的规范作品目录
- **THEN** 系统从该内容根解析材料和素材，输出仍按该作品归属推导

#### Scenario: 有声渲染的 props 时间轴

- **WHEN** 带 `--media` 渲染、预览或评审
- **THEN** composition 的 props 使用媒体清单派生的延长时长，总帧数与派生时间轴一致；
  体检抽帧与契约页使用同一条时间轴

#### Scenario: 无声路径不受影响

- **WHEN** 不带 `--media` 渲染、预览或评审
- **THEN** props 与页面 URL 仍指向原始分镜，行为与产物不变

### Requirement: 渲染契约
系统 SHALL 提供一个可被浏览器自动化驱动的契约页，把共享 composition 挂载为可寻址的帧序列，并在 `window.__M2V__` 上暴露 `version`、`fps`、`width`、`height`、`durationInFrames`、`ready()` 与 `seekToFrame(frame)`。契约页 SHALL 只服务当前仍受支持的 composition 契约。

`version` SHALL 与所选 composition 的契约版本一致；`general` 的 v6 混合媒体契约 SHALL 为 `6`。`ready()` SHALL 在字体、本地资源就绪且第 0 帧已绘制后 resolve。`seekToFrame(frame)` SHALL 把画面切换到第 frame 帧、暂停播放，并在画面更新完成后 resolve；`frame` 从 `0` 开始，最大值为 `durationInFrames - 1`。

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

### Requirement: 安全复用构建产物

系统 SHALL 复用输入完全匹配且完整性验证通过的本地构建缓存。缓存键 SHALL 覆盖共享可达源码、字体、公共静态资产、打包配置及依赖版本。输入变化、缓存损坏或缺少完整完成标记时 SHALL 重建。缓存命中 SHALL NOT 跳过分镜、安全、确定性、媒体时效及制作门禁检查。

#### Scenario: 重复合成同一作品
- **WHEN** 同一作品构建输入未变且缓存完整
- **THEN** 不重复打包，日志明确显示缓存命中，成片溯源仍反映当前输入

#### Scenario: 切换作品或修改资产
- **WHEN** 当前材料路径、共享代码、字体、公共资源或依赖改变
- **THEN** 系统重新构建，不交付上一作品或上一版本画面

#### Scenario: 缓存残缺
- **WHEN** 缓存被删除、修改或上次构建中断
- **THEN** 系统重建，构建失败时不发布残缺缓存
