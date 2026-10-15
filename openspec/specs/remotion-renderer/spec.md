# remotion-renderer Specification

## Purpose

把画面执行与成片渲染交给 React + Remotion，同时保持本项目唯一不可让渡的性质：
**画面是帧号的纯函数**。本能力规定版本 3 渲染契约、确定性验收口径、
以及 Python 入口与 Node 渲染器之间的职责边界。

Remotion 的官方规则与本项目既有渲染契约是同一条要求（所有动画必须由帧号驱动，
不得使用 CSS 动画），因此换渲染器不构成对确定性的放宽。

## Requirements

### Requirement: 画面由 React composition 渲染

系统 SHALL 以共享 React composition 作为唯一画面执行者，SHALL 由 Remotion 负责逐帧渲染与编码。
composition SHALL 能按分镜选择共享场景树解释器或经过校验的作品级代码场景，
但作品 SHALL NOT 自行注册 Remotion 根、composition、契约页或时间轴。

所有可达画面组件 SHALL 通过帧号钩子或共享场景参数取得当前帧，SHALL NOT 依赖挂钟时间、
系统随机数、CSS `animation` / `transition` / `@keyframes`，也 SHALL NOT 依赖组件库自带的
计时器或布局测量循环。渲染路径 SHALL 在开渲前对共享源码、当前作品可达源码和 CSS 做
静态检查，命中禁用写法时 SHALL 报出文件与位置，SHALL NOT 静默继续。

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
路径归属推导、分镜与作品源码校验、配音与字幕准备、体检与溯源 SHALL 继续由 Python 侧编排；
当前作品代码场景的静态清单生成、前端打包、逐帧渲染与编码 SHALL 交给 Node 侧工具链。

渲染入口 SHALL NOT 要求用户预先进入前端工程目录，也 SHALL NOT 依赖调用时的工作目录。
作品源码位于仓库外内容根时，系统 SHALL 通过显式内容根解析并只纳入当前作品允许的文件。

启用配音媒体清单时，系统 SHALL 把清单派生的分镜时长（每幕实际 `durationInFrames`）
写回源分镜快照形成有效分镜，并 SHALL 把有效分镜作为 composition 的 props 提供给
契约页与 Remotion 渲染；SHALL NOT 让画面按声明时长运行而音轨按派生时长合成。
代码场景清单与作品归属的解析 SHALL 继续使用原始分镜路径。

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

#### Scenario: 有声渲染的 props 时间轴

- **WHEN** 带 `--media` 渲染、预览或评审
- **THEN** composition 的 props 使用媒体清单派生的延长时长，总帧数与派生时间轴一致；
  体检抽帧与契约页使用同一条时间轴

#### Scenario: 无声路径不受影响

- **WHEN** 不带 `--media` 渲染、预览或评审
- **THEN** props 与页面 URL 仍指向原始分镜，行为与产物不变

### Requirement: 合成性能可观测

系统 SHALL 输出本次合成的打包、元数据读取、逐帧渲染编码、音轨合成、验收与总耗时，并标明缓存命中状态、实际并发、帧数及分辨率。未执行阶段 SHALL 标记为跳过，不得伪造实测值。

#### Scenario: 有声合成完成
- **WHEN** 用户完成一次有声成片合成
- **THEN** 性能报告列出各阶段秒数与总耗时，可用于同作品前后对照

#### Scenario: 无声合成
- **WHEN** 用户未提供媒体清单
- **THEN** 音轨合成阶段标记跳过，其余执行阶段仍有实际耗时

### Requirement: 安全复用构建产物

系统 SHALL 复用输入完全匹配且完整性验证通过的本地构建缓存。缓存键 SHALL 覆盖共享可达源码、当前作品模块及导入、生成的场景与样式清单、字体、公共静态资产、打包配置及依赖版本。输入变化、缓存损坏或缺少完整完成标记时 SHALL 重建。缓存命中 SHALL NOT 跳过分镜、安全、确定性、媒体时效及制作门禁检查。

#### Scenario: 重复合成同一作品
- **WHEN** 同一作品构建输入未变且缓存完整
- **THEN** 不重复打包，日志明确显示缓存命中，成片溯源仍反映当前输入

#### Scenario: 切换作品或修改资产
- **WHEN** 作品场景清单、代码、字体、公共资源或依赖改变
- **THEN** 系统重新构建，不交付上一作品或上一版本画面

#### Scenario: 缓存残缺
- **WHEN** 缓存被删除、修改或上次构建中断
- **THEN** 系统重建，构建失败时不发布残缺缓存

### Requirement: 显式受控渲染并发

渲染入口 SHALL 提供正整数 `--concurrency`，省略时 SHALL 使用 1。非法取值 SHALL 在打包前报错。提高并发 SHALL 保持帧范围、有效时间轴、字体就绪、画质和编码参数及验收标准一致；失败 SHALL 明确报告，不留下可被误认为成功的正式成片。

#### Scenario: 默认与显式并发
- **WHEN** 用户省略并发参数或指定有效正整数
- **THEN** 分别以单并发或指定并发渲染，报告实际并发值

#### Scenario: 非法并发
- **WHEN** 并发为零、负数、小数或非数字
- **THEN** 入口报出参数错误，尚未开始打包与渲染

### Requirement: 复用会话仍在渲染前校验元数据

系统 SHALL 在元数据交叉校验通过后才开始逐帧渲染。浏览器会话复用 SHALL NOT 放宽帧数、帧率和尺寸一致性检查；成功、失败或中止时 SHALL 关闭本次会话资源。

#### Scenario: 元数据不一致
- **WHEN** composition 元数据与有效分镜不一致
- **THEN** 渲染前终止并报告两边值，不生成正式成片

### Requirement: 构建锁持有者存活判定跨平台安全

系统 SHALL 以不影响目标进程、当前进程及同控制台其它进程的方式判定构建锁持有者是否仍然存活。存活探测 SHALL NOT 通过向进程或控制台进程组发送控制事件来实现，在 Windows 上 SHALL NOT 触发 Ctrl+C 或 Ctrl+Break 事件。探测本身 SHALL NOT 终止当前进程、锁持有者或同控制台的任何进程。

#### Scenario: Windows 上探测仍存活的持有者

- **WHEN** 在 Windows 上探测一个仍在运行的锁持有者
- **THEN** 判定结果为存活，且当前进程与同控制台的其它进程都不受影响

#### Scenario: 持有者已退出时提前回收

- **WHEN** 锁文件记录的持有者进程已经退出，而锁文件年龄尚未达到过期阈值
- **THEN** 判定为已退出并回收该锁，不必等待满过期时长

#### Scenario: 权限不足或查询失败

- **WHEN** 探测因权限不足或系统调用失败而无法得出确定结论
- **THEN** 系统视为持有者仍然存活，保留锁文件并继续等待，不得据此回收锁

### Requirement: 同一控制台的并发构建互不中断

系统 SHALL 保证在同一控制台并发启动的多个构建之间，存活探测不会中断任何一方，也不会把仍存活的锁持有者误判为已退出。只有确认持有者已退出或锁文件超过过期阈值时，系统才 SHALL 回收锁。

#### Scenario: 并发构建共享控制台

- **WHEN** 两个构建在同一控制台先后启动，先启动者已持有生成锁
- **THEN** 后启动者保持等待且不打断先启动者，不得回收先启动者仍持有的锁

#### Scenario: 锁保持有效直至正常释放

- **WHEN** 持有者仍在运行且未超时
- **THEN** 锁文件保持存在，等待方在超时后报出明确的等待超时错误，而不是抢到锁

### Requirement: 渲染契约
系统 SHALL 提供一个可被浏览器自动化驱动的契约页，把共享 composition 挂载为可寻址的帧序列，并在 `window.__M2V__` 上暴露 `version`、`fps`、`width`、`height`、`durationInFrames`、`ready()` 与 `seekToFrame(frame)`。契约页 SHALL 只服务当前仍受支持的 composition 契约。

`version` SHALL 与所选 composition 的契约版本一致；`article-narrative` 的 v5 讲解契约 SHALL 为 `5`。`ready()` SHALL 在字体、本地资源就绪且第 0 帧已绘制后 resolve。`seekToFrame(frame)` SHALL 把画面切换到第 frame 帧、暂停播放，并在画面更新完成后 resolve；`frame` 从 `0` 开始，最大值为 `durationInFrames - 1`。

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
