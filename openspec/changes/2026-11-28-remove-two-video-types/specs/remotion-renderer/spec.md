## MODIFIED Requirements

### Requirement: 画面由 React composition 渲染

以下渲染实现归属于作品自己的默认工程模板，MUST 在没有主项目的环境运行。主项目 MUST 只委托作品入口，不注入其web工程、字体、源码或依赖；自定义工程可自行选择实现，接入制作工具时遵守同等输出与证据约束。

默认作品工程 SHALL 以本地 React composition 为唯一合成执行者，由 Remotion 逐帧渲染编码。三类作品 SHALL 使用 v9 全画布本地代码场景按需录制的无声片段；作品工程 MUST 自行拥有本地Remotion根、composition、契约页和时间轴；单个场景入口 MUST NOT 绕过该工程执行协议再注册另一套成片根。

本地 composition 可达画面 SHALL 由帧号或共享场景参数驱动，不依赖挂钟、系统随机数、CSS 动画或组件自带计时器。渲染前 SHALL 对本地合成源码和 CSS 静态检查，命中禁用写法时报出文件位置并拒绝。作品 scenes 代码 SHALL 仅运行于独立录制页，不进入 composition；其自由动画不承诺逐像素复现，正式导出只回放已验收片段。

#### Scenario: 使用帧号钩子

- **WHEN** 作品合成组件计算第 N 帧的显示状态
- **THEN** 结果来自帧号和运行时参数，与求值顺序和真实时间无关

#### Scenario: 组件库自带计时器

- **WHEN** 本地可达合成组件包含未经确定性适配的真实计时器或 CSS 动画
- **THEN** 静态检查拒绝并定位源文件

#### Scenario: 随机访问一帧

- **WHEN** 同一已准备作品的同一帧被直接求值两次
- **THEN** 回放同一片段，满足既有画面确定性阈值

#### Scenario: 作品试图声明独立 composition

- **WHEN** 单个场景入口试图另行注册绕过工程时间轴的Remotion根或composition
- **THEN** 拒绝该场景入口的绕行注册；作品工程自身的本地composition与契约页注册正常允许

### Requirement: 渲染契约

以下渲染实现归属于作品自己的默认工程模板，MUST 在没有主项目的环境运行。主项目 MUST 只委托作品入口，不注入其web工程、字体、源码或依赖；自定义工程可自行选择实现，接入制作工具时遵守同等输出与证据约束。

系统 SHALL 提供一个可被浏览器自动化驱动的契约页，把本地 composition 挂载为可寻址的帧序列，并在 `window.__M2V__` 上暴露 `version`、`fps`、`width`、`height`、`durationInFrames`、`ready()` 与 `seekToFrame(frame)`。契约页 SHALL 只服务当前仍受支持的 composition 契约。

`version` SHALL 与所选 composition 的契约版本一致；三类共用的 SceneFilm composition 契约 SHALL 为 `6`，与分镜版本相互独立。`ready()` SHALL 在字体、本地资源就绪且第 0 帧已绘制后 resolve。`seekToFrame(frame)` SHALL 把画面切换到第 frame 帧、暂停播放，并在画面更新完成后 resolve；`frame` 从 `0` 开始，最大值为 `durationInFrames - 1`。

默认模板的本地契约页 SHALL 复用Remotion Player；作品拥有该本地实现，自定义工程只需兑现已声明协议语义，不要求加载主项目契约页。`seekToFrame` 返回后，所有场景组件观察到的当前帧 SHALL 等于 `frame`。

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

### Requirement: 可选进程级分段渲染

渲染入口 SHALL 提供可选正整数 `--jobs`，默认 2。`--jobs: 1` SHALL 使用单会话渲染路径。`--jobs > 1` 时，系统 SHALL 先读取并交叉校验 composition 元数据，再按帧区间启动多个独立渲染进程；每段 SHALL 独立解码核对帧数、尺寸与帧率，拼接后 SHALL 复核总帧数，最后统一混入音轨。

`--jobs` SHALL 与 Remotion 页签级 `--concurrency` 区分；分段内部并发 SHALL 固定为 1。`--jobs` SHALL NOT 进入候选交付绑定：改变 jobs 仍可复用同一内容候选。任一段失败 SHALL 清理进程并明确失败，MUST NOT 留下可被误认为成功的成片。该能力 SHALL 对三类作品开放。

#### Scenario: 分段渲染

- **WHEN** 三类作品以 `--jobs 4` 渲染全片
- **THEN** 四个帧区间独立渲染、逐段验收后无损拼接，成片帧数、尺寸、帧率与单进程一致

#### Scenario: 默认双进程

- **WHEN** 未声明 `--jobs`
- **THEN** 使用 2 路分段渲染，行为与产物和显式 `--jobs 2` 一致

#### Scenario: 显式单进程

- **WHEN** 声明 `--jobs 1`
- **THEN** 走单会话渲染，行为与产物不变

#### Scenario: 元数据不一致

- **WHEN** composition 报出的 fps、尺寸或总帧数与准备记录不一致
- **THEN** 在分段渲染开始前失败，不生成任何片段

#### Scenario: 某段失败

- **WHEN** 任一分段渲染或解码验收失败
- **THEN** 终止其余进程并报错，不拼接、不发布候选
