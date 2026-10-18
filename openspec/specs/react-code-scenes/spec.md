# react-code-scenes Specification

## Purpose

让通用讲解在保留统一音轨、字幕与素材留证的前提下使用可信的本地 React 代码场景：作品在 `scenes/` 下提供 TSX 入口并自行控制整张画布，系统在准备阶段受限打包、按实际画幅逐帧采集为与镜头帧数一致的无声片段并绑定摘要缓存，完整预演与正式导出只回放同一片段，不在导出执行作品代码。

## Requirements

### Requirement: 本地代码场景
系统 MUST 接受 scenes 下 TSX 默认导出的 React 组件及 JSON 对象参数，提供 fps、时长、实际 width/height、字幕安全区、本幕旁白时间窗及录制进度；MUST NOT 提供 theme。场景 MUST 控制完整画布，作品绘制标题、内容及不透明背景，共享层仅合成片段与字幕。系统 MUST 拒绝路径越界、未批准依赖和远程模块，不安装作品依赖。场景 MUST 支持无旁白，声音由统一音轨处理。

#### Scenario: 有效入口
- **WHEN** 录制有效横屏或竖屏入口
- **THEN** SDK 与录制 viewport 均采用实际画幅，无固定标题及内容框

#### Scenario: 无效导入
- **WHEN** 代码越过作品边界或引用未批准包及远程模块
- **THEN** 构建失败并指出原因

### Requirement: 逐帧录制及复用
系统 MUST 等待字体、组件及显式资源就绪后录制；超时、外网请求或运行异常 MUST 失败且不保存有效准备。录制 MUST 按顺序在第 n/fps 秒完成动画更新和绘制后逐帧采集，截图与磁盘等待 MUST NOT 推进动画；系统 MUST 同步上下文、动画库、三维绘制、CSS 动画和本地视频。录制 MUST 标准化为实际画幅、精确帧数、60 fps 的无声视频，并恢复落盘目录继承权限。缓存 MUST 绑定源码、资源、参数、时间窗、依赖、实现、画幅、字幕安全区配置及素材导入映射和摘要。完整预演及正式导出 MUST 复用同一已验收片段，不在导出执行作品代码；自由动画不承诺逐像素复现。

#### Scenario: 输入变化
- **WHEN** 仅改变画幅、安全区配置或登记媒体内容
- **THEN** 旧缓存及准备失效，重新录制并要求完整预演

#### Scenario: 运行失败
- **WHEN** 代码异常、请求外网或未及时 ready
- **THEN** prepare 失败且不发布有效准备记录

#### Scenario: 正式导出
- **WHEN** 输入完全一致且片段完整，或当前准备和预演有效后正式导出
- **THEN** 复用相同片段，不重新录制，片段可按目录继承权限直接打开

#### Scenario: 片段可直接打开
- **WHEN** 录制片段从临时目录落盘
- **THEN** 恢复目标目录继承权限，用户可直接播放

#### Scenario: 采集变慢
- **WHEN** 截图或磁盘写入延迟
- **THEN** 下一帧仍对应下一固定时间点，不跳过运动状态或补重复帧

#### Scenario: 精确采集
- **WHEN** 顺序录制 N 帧并编码
- **THEN** 采集和解码均为 N 帧，缺帧或推进异常明确失败，不发布缓存；旧实时缓存不能复用

### Requirement: 已导入媒体解析
代码场景 MUST 能按素材 ID 获取本地地址、类型、实测宽高、视频时长、色彩空间、alpha 标记与登记许可；未知 ID MUST 明确失败。接口 MUST 仅暴露已登记且摘要有效的素材，MUST NOT 允许借直接文件地址绕过留证。媒体比例 MUST 不受画幅限制，裁切、布局和播放由作品代码控制。视频原声 MUST NOT 隐式进入母版。

#### Scenario: 图片及视频
- **WHEN** 代码解析已导入的横图或视频用于竖屏作品
- **THEN** 返回有效本地地址、实测元数据、色彩空间、alpha 与许可，不因素材比例拒绝；成片声音仅来自统一音轨

#### Scenario: 非法素材
- **WHEN** 素材未登记、ID 不存在、摘要不符或试图访问边界外文件
- **THEN** 准备或资源解析明确失败，不静默替换

#### Scenario: 电影级资产元数据
- **WHEN** cinematic 作品解析 hero 纹理
- **THEN** 返回色彩空间、alpha 与许可；作品可据色彩空间设置 sRGB/线性，并在片尾署名

### Requirement: 电影级镜头与后期接口

系统 MUST 在 `m2v/code-scene` 提供电影级共享接口：`PostFX`（Bloom、DOF、grain、vignette、chromatic aberration、LUT）、`CameraRig`（CatmullRom/Bezier 路径、缓动、FOV、滚转、曝光、焦点拉移、穿球与背景裁切检查）、`LookProvider`，以及星空、粒子带、大气、环、日面、日冕、日珥、奥尔特云与彗星组件。SHOULD 提供每镜头质量档（hero 2× SSAA + 2–4 子帧运动模糊；standard 1×、无后期）。

后期 MUST 只作用于代码场景 canvas，MUST NOT 覆盖或改变共享字幕 DOM 层。全部后期与粒子参数 MUST 由 `elapsedSeconds` 或帧号驱动，MUST NOT 使用挂钟、`Math.random`、CSS animation、组件计时器或未受控的异步状态；粒子噪声 MUST 使用「帧号 + shot id」的确定性种子。源码闸门 MUST 继续拒绝禁用写法。

系统 MUST 批准并随仓库分发 `postprocessing` 与 `@react-three/postprocessing`，并把依赖、shots、look、后期参数纳入代码片段缓存键。缺少依赖或版本不匹配时 MUST 在打包/准备前明确失败，MUST NOT 输出无后期或部分后期的画面。standard 作品不声明 shots/look 时 MUST 保持当前 SDK 行为与画质。

#### Scenario: 确定性后期
- **WHEN** 同一帧连续渲染两次并比对
- **THEN** 两次画面相似度 ≥ 60dB；若 Bloom、DOF、grain 或粒子因时间/随机源变化而不同，判定失败并定位到该帧

#### Scenario: 缺少后期依赖
- **WHEN** cinematic 作品引用了 PostFX 但前端依赖未安装或版本不匹配
- **THEN** 打包或准备前失败并指出依赖，不产出缺少后期的片段

#### Scenario: 标准作品不受影响
- **WHEN** standard 作品的场景未声明 shots/look 且未引用 PostFX
- **THEN** SDK 行为、录制片段、缓存键与现有画面保持不变

#### Scenario: 后期不覆盖字幕
- **WHEN** 代码场景使用 Bloom、DOF 或 LUT 渲染
- **THEN** 共享字幕层仍按原有几何与样式绘制，不被后期模糊、变色或裁切

#### Scenario: 镜头校验
- **WHEN** shots 的时间窗越界、重叠或与旁白段不匹配
- **THEN** 准备失败并指出具体 shot 与时间窗
