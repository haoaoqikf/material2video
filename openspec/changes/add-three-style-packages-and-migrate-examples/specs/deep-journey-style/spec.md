## Purpose

把《太阳系之旅》的深空连续旅程外观转成仓库内可安装、可验证的风格包，使通用作品能复用同一套近黑深空、自然天体色、暖白/淡金信息层、3D 舞台、连续相机与导航版式，而不是每次手工复刻；同时保留原作品的天体数据、路径、旁白与节奏作为该风格的规范示例。

## ADDED Requirements

### Requirement: 深空旅程风格包可用

仓库 SHALL 提供 `styles/deep-journey/`，清单 SHALL 声明 `types: ["general"]` 与 `frames: [{"width":1920,"height":1080}]`，并提供非空 `GUIDE.md` 与 `tokens.json`。包 SHALL NOT 声明 `requires.narration = "none"`；有旁白与无旁白作品均可选择。作品通过 `project.json` 的 `style.id: "deep-journey"` 选择后，`m2v validate` 与 `m2v prepare` SHALL 记录其 id、version 与内容指纹；包内容变化 SHALL 使旧准备失效。包 SHALL NOT 登记 `assets`，SHALL 使用宿主已注册字体与程序化材质。

#### Scenario: 选择风格并准备

- **WHEN** 一个有旁白的 general 横屏作品声明 `style.id: "deep-journey"` 并执行 `prepare`
- **THEN** 准备产物记录风格身份与指纹，`m2v status` 显示所选风格与准备有效性

#### Scenario: 不兼容选择

- **WHEN** 非 general 作品、竖屏作品或未知风格 id 选择该包
- **THEN** 校验明确失败并指出类型或画幅不匹配，不回退到无风格

### Requirement: 深空色板与 HUD 版式

`tokens.json` SHALL 提供近黑深空底、自然天体色、暖白正文、淡金导航与必要边界脚注色，并说明各颜色只承担一个语义；SHALL 提供章节进度轨、状态行、信息面板、字幕 scrim 与脚注的位置和字号阶。字幕安全区 SHALL 只由场景上下文 `subtitleSafeArea` 提供，tokens SHALL NOT 复制一份几何。风格包 SHALL NOT 硬编码天体名、距离、AU、NASA 文本或旁白。

#### Scenario: 场景读取参数

- **WHEN** 场景导入 `m2v/style` 的 `tokens`
- **THEN** 可用 tokens 取得深空色、HUD 分区与字号，且对象只读

#### Scenario: 未登记语义色

- **WHEN** 场景请求未登记的语义色或分区名
- **THEN** 组件明确抛错，不静默回退

### Requirement: 可复用 3D 组件与录制约束

风格包 SHALL 提供星场、轨道环、大气/光照辅助、行星材质包装、章节轨、状态行、信息面板、字幕 scrim 与边界脚注等组件。3D 组件 SHALL 通过 `m2v/code-scene` 导入 `THREE`、`Canvas`、`useFrame`、`useThree`，SHALL NOT 直接裸导入 `three`、`@react-three/fiber` 或 `@react-three/drei`。组件 SHALL 使用受控帧号或受控 R3F 时钟，SHALL NOT 使用挂钟、`Math.random`、CSS 动画或组件计时器。组件 SHALL NOT 自动修改作品画面，必须由作品显式导入，并且只接收天体、位置、镜头、进度与文字等 props。

#### Scenario: 组件构建与导入边界

- **WHEN** 在包内构建全部 3D 组件
- **THEN** 构建通过，组件 import 只来自 `react`、`m2v/` 或包内相对路径

#### Scenario: 确定性绘制

- **WHEN** 同一作品帧被两次独立录制
- **THEN** 同一帧画面一致，不因运行时刻或随机数变化

#### Scenario: pure-time 与逐帧回调冲突

- **WHEN** 使用 `useFrame` 的组件被声明 `capture.mode: "pure-time"` 的作品导入
- **THEN** 静态源码闸门明确失败并指出原因，不静默降级或改用挂钟

### Requirement: 风格示例作品（视频专属，不属于包）

仓库 SHALL 在 `styles/examples/deep-journey/solar-system-journey/` 提供规范示例，声明 `style.id: "deep-journey"`。该作品 SHALL 保持单幕一镜到底、15 段旁白、31 个首尾相接的镜头、60 fps、路径与换站空间过渡、独立行星视觉分离与分段节奏；旁白、字幕、配乐与音效沿用原作品契约。示例 SHALL 通过 v8 校验与 `prepare`，生成媒体 SHALL NOT 入库。天体数据、纹理、路径、分镜、旁白与声音属于作品，SHALL NOT 进入风格包。示例使用逐帧 3D 回调时 SHALL NOT 声明 `capture.mode: "pure-time"`。

#### Scenario: 示例可校验

- **WHEN** 对 `styles/examples/deep-journey/solar-system-journey/` 运行 `m2v validate` 与 `prepare`
- **THEN** 校验通过，单幕、60 fps、15 段旁白与 31 个镜头保持，路径首尾相接

#### Scenario: 示例不被当作风格包

- **WHEN** 运行 `m2v styles` 或 `m2v styles --json`
- **THEN** `styles/examples/deep-journey/solar-system-journey` 不出现在风格清单中，也不能按风格 id 加载

### Requirement: 示例换站必须有空间过渡（视频专属）

`deep-journey` 示例作品的每个站点镜头 MUST 从远处抵达特写，再在旁白结束后拉远；旁白开始时相机 MUST 已抵达特写。站点之间的过场 MUST 升到黄道面上方，从上一站远出点穿过两星之间的空间再下降到下一站远入点，MUST NOT 只靠短位移加朝向混合完成换站。站点镜头首末点到目标天体的距离与镜头内最近距离之比 MUST 不小于 1.35；独立过场的最大高度 MUST 高于 1.5 个世界单位且超过自身弧长的 10%。原始站点与过场路径 MUST 首尾相接；实际相机 MUST 使用跨边界的连续位置求值和覆盖过场的视线承接，MUST 检查镜头内部的速度峰值、加减速、转向及主体屏幕尺度，MUST NOT 仅用端点或边界速度比证明自然运动。依赖特定视角的 hero MUST 保留其验证过的轨道形状，不为了统一公式牺牲构图。该要求约束示例作品，不属于风格包。

#### Scenario: 太阳到水星

- **WHEN** 太阳站结束进入水星站
- **THEN** 相机先拉远太阳并升到水星轨道上方，水星从远处持续变大；旁白开始时已在特写，随后再拉远离开

#### Scenario: 地球到月球

- **WHEN** 地球 hero 结束进入月球站
- **THEN** 相机从地球上方经过近垂直的空间弧接近月球远入点，再下降到月球特写；两个天体都不被穿模

#### Scenario: 土星 hero

- **WHEN** 播放土星 hero
- **THEN** 相机按跨环平面的连续轨道呈现光环，进出方向按当前旅程设计，环在旁白期间可辨；轨道与构图须由当前版本风险材料复核，不能直接沿用旧版结论

#### Scenario: 只做朝向混合的换站

- **WHEN** 站点镜头首末点仍贴着天体、过场只做短位移与朝向混合
- **THEN** 相机测试按接近/拉远比与过场抬升判定失败，并要求重做路径

#### Scenario: 镜头内部急冲与短促转向

- **WHEN** 原始路径相接但中段位移集中或短促转向破坏连续旅程
- **THEN** 实际相机调整速度分配与覆盖过场的视线承接，并用完整运动过程证据复查，技术检查不自动关闭该问题

### Requirement: 示例独立行星必须具有清楚的视觉分离（视频专属）

`deep-journey` 示例制作 MUST 全量复核独立行星之间的过场，重点检查木星到土星；MUST 通过布局、相机路径与构图让独立行星呈现明确的空间分离，MUST NOT 出现两颗独立行星以挤靠的近景尺度造成伴星关系的错觉。行星与所属卫星的邻近关系 MUST 保留；大小、距离非同比例的示意声明 MUST 保留，无碰撞 MUST NOT 单独作为空间关系通过依据。该要求约束示例作品，不属于风格包。

#### Scenario: 木星到土星看似紧挨

- **WHEN** 相机路径安全但木星与土星在换站画面中看起来近景挤靠
- **THEN** 助手登记必改项，联合调整布局与运镜，在当前版本复查空间分离后才能关闭

#### Scenario: 行星与卫星邻近

- **WHEN** 复查地球与月球等母星和卫星关系
- **THEN** 保留合理的邻近表达，不把独立行星分离规则机械应用于卫星

### Requirement: 示例换站必须按段核定简洁连续的节奏（视频专属）

`deep-journey` 示例制作 MUST 分别核定各段离场、跨站、接近及必要观察预算，MUST 取消统一九秒段间预算并压缩重复拉远和无信息等待。MUST 保持单幕一镜到底、15 站、现有旁白及地球、土星、奥尔特云三个重点镜头，MUST NOT 以全片统一加速替代局部修订。总片长 MUST 在既有时长边界内由新版动态粗预演与全片高密度时间标注帧序列、路径/屏幕投影量测共同核定；连续旅行、主体可辨与必要观察 MUST 同时满足。不要求播放视频或连续收听声音。该要求约束示例作品，不属于风格包。

#### Scenario: 过场平滑但等待过长

- **WHEN** 过场没有突变但持续移动不再提供必要信息或旅行感
- **THEN** 助手压缩该段预算并重新生成全片时间标注帧序列，结合位移、主体尺度与停留时长量测复查，同时回归过快掠过风险

#### Scenario: 调整布局与时长

- **WHEN** 独立行星布局和换站预算改变
- **THEN** 助手同步路径、分镜、准备窗口、配乐覆盖、字幕与音效时序及验证说明，并回归高速掠过、甩头、瞬移和重点镜头构图

