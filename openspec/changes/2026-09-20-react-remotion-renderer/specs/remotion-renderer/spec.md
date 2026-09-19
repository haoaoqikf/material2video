## Purpose

把画面执行与成片渲染交给 React + Remotion，同时保持本项目唯一不可让渡的性质：
**画面是帧号的纯函数**。本能力规定版本 2 渲染契约、确定性验收口径、
以及 Python 入口与 Node 渲染器之间的职责边界。

Remotion 的官方规则与本项目既有渲染契约是同一条要求（所有动画必须由帧号驱动，
不得使用 CSS 动画），因此换渲染器不构成对确定性的放宽。

## ADDED Requirements

### Requirement: 画面由 React composition 渲染

系统 SHALL 以 React composition 作为唯一画面执行者，SHALL 由 Remotion 负责逐帧渲染与编码。
画面组件 SHALL 通过帧号钩子取得当前帧，SHALL NOT 依赖挂钟时间、随机数、
CSS `animation` / `transition` / `@keyframes`，也 SHALL NOT 依赖组件库自带的计时器或
布局测量循环。

系统的渲染路径 SHALL 在开渲前对 composition 源码做静态检查，命中禁用写法时
SHALL 报出文件与位置，SHALL NOT 静默继续。

#### Scenario: 使用帧号钩子
- **WHEN** 组件需要计算某个元素在第 N 帧的位置、透明度或数值
- **THEN** 它由帧号钩子与运行时原语算出，结果与求值顺序、真实时间无关

#### Scenario: 组件库自带计时器
- **WHEN** 组件树中出现由真实时钟或 CSS 动画驱动的第三方组件，且未经适配层改造
- **THEN** 静态检查报错并指出该组件，渲染不开始

#### Scenario: 随机访问一帧
- **WHEN** 渲染器或验收入口直接跳到任意帧求值两次
- **THEN** 两次得到的画面在确定性阈值内一致

### Requirement: 版本 2 渲染契约

系统 SHALL 提供一个可被浏览器自动化驱动的契约页，把 composition 挂载为可寻址的帧序列，
并在 `window.__A2V__` 上暴露 `version`、`fps`、`width`、`height`、`durationInFrames`、
`ready()` 与 `seekToFrame(frame)`。

`version` SHALL 为 `2`。`ready()` SHALL 在字体加载完成、首批资源就绪且第 0 帧已绘制后 resolve。
`seekToFrame(frame)` SHALL 把画面切换到第 frame 帧、暂停播放，
并在画面更新完成后 resolve；`frame` 从 `0` 开始，最大值为 `durationInFrames - 1`。

契约 SHALL 由 Remotion 的 Player 实现，SHALL NOT 由每个作品自行实现。
`seekToFrame` 返回后，`useCurrentFrame()` 的取值 SHALL 已等于 `frame`。

#### Scenario: 契约可用
- **WHEN** 浏览器打开契约页并调用 `ready()` 与 `seekToFrame(f)`
- **THEN** 两者按上述语义 resolve，且页面上的帧号等于 `f`

#### Scenario: 声明与分镜不一致
- **WHEN** 契约页报告的 `fps`、`width`、`height` 或 `durationInFrames` 与分镜不一致
- **THEN** 渲染入口报错终止并列出两边的值

#### Scenario: 版本不匹配
- **WHEN** 页面暴露的 `__A2V__` 版本不是 `2`
- **THEN** 渲染入口报错终止并说明当前支持的契约版本

### Requirement: 确定性以画面等价为准

系统 SHALL 以**画面等价**而非逐字节相等作为帧确定性的判据：对同一帧重复渲染，
两次截图的结构相似度 SHALL ≥ 60 dB。

该阈值 SHALL 由渲染契约参考文档记录，并 SHALL 说明放宽逐字节相等的原因：
换用不同的无头浏览器发行版后，光栅化噪声仍会让极少数像素相差 1 个色阶，
而这类噪声在编码后不可见。

既有的观感闸门（K 系列）、动效闸门（M 系列）与字体缺字机检的**数值门槛**
SHALL NOT 因为本次口径调整而放宽。

#### Scenario: 同帧重复渲染
- **WHEN** 对同一帧连续截图两次并比对
- **THEN** 相似度不低于阈值；低于阈值时判定为画面逻辑问题并报出该帧

#### Scenario: 整块元素位置不同
- **WHEN** 某个元素在两帧之间的位置或透明度不同
- **THEN** 相似度远低于阈值并被判为确定性失败

### Requirement: 成片编码与交付参数不变

成片的编码参数 SHALL 与既有契约一致：画面 `yuv420p`（`tv` 范围、`bt709`）、
宽高为偶数、帧率与尺寸取自分镜；有声导出 SHALL 使用 AAC-LC、44.1kHz、立体声。

渲染成功后系统 SHALL 完整解码一遍成片并核对帧数与分辨率，
SHALL 读回码流参数并拒绝全范围像素格式的产物。
交付文件落盘后 SHALL 交回目标目录的继承权限。

#### Scenario: 全范围像素格式
- **WHEN** 产出的码流为全范围像素格式
- **THEN** 验收报错终止，SHALL NOT 交付「能解码但播放器打不开」的成片

#### Scenario: 帧数与分辨率
- **WHEN** 渲染成功
- **THEN** 解码复核得到的帧数与分辨率与分镜一致

### Requirement: Python 入口与 Node 渲染器分工

系统的命令行入口 SHALL 继续由现有脚本提供，并 SHALL 保持现有参数与默认输出位置。
路径归属推导、分镜校验、配音与字幕准备、体检与溯源 SHALL 继续由 Python 侧承担；
逐帧渲染与编码 SHALL 交给 Node 侧渲染器。

渲染入口 SHALL NOT 要求用户预先进入前端工程目录，也 SHALL NOT 依赖调用时的工作目录。

#### Scenario: 命令不变
- **WHEN** 用户沿用既有的校验、预览、渲染、体检命令
- **THEN** 参数含义与产物位置不变，渲染由 Node 侧完成

#### Scenario: 缺少前端依赖
- **WHEN** 前端工程依赖未安装而用户直接渲染
- **THEN** 命令报错并说明需要先安装前端依赖，SHALL NOT 产出一个空成片

#### Scenario: 渲染期离线
- **WHEN** 依赖已安装、字体与资产随仓库分发，渲染时无网络
- **THEN** 渲染正常完成
