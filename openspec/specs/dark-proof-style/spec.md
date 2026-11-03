# dark-proof-style Specification

## Purpose

把参考片《重复》中可迁移的论证型视觉语法做成仓库内可安装、可验证的风格包，并配一条《样本》规范示例，使通用作品能复用近黑舞台、金/红语义、巨型数字、可数点阵、论证图表与连续溶解，而不是每次手工复刻参考片。风格包只提供表现层，不改变视频类型、题材数学、制作门或验收条件。

## Requirements

### Requirement: 暗场论证风格包可用

仓库 SHALL 提供 `styles/dark-proof/`，清单 SHALL 声明 `types: ["general"]` 与 `frames: [{"width":1920,"height":1080}]`，并提供非空 `GUIDE.md` 与 `tokens.json`。作品通过 `project.json` 的 `style.id: "dark-proof"` 选择后，`m2v validate` 与 `m2v prepare` SHALL 记录其 id、version 与内容指纹；包内容变化 SHALL 使旧准备失效。清单 SHALL 允许无旁白与有旁白作品选择，SHALL NOT 把旁白设为 `none` 强制约束；本包 SHALL NOT 携带字体或外部素材资产。

#### Scenario: 选择风格并准备

- **WHEN** 一个 general 横屏作品声明 `style.id: "dark-proof"` 并执行 `prepare`
- **THEN** 准备产物记录风格身份与指纹，`m2v status` 显示所选风格与准备有效性

#### Scenario: 不兼容选择

- **WHEN** 非 general 作品、竖屏作品或未知风格 id 选择该包
- **THEN** 校验明确失败并指出类型或画幅不匹配，不回退到无风格

#### Scenario: 旁白可选

- **WHEN** 无旁白作品或有旁白作品选择 `dark-proof`
- **THEN** 两者都通过校验与准备；有旁白作品使用共享字幕层，无旁白作品在安全区内自绘屏幕字幕

### Requirement: 色板语义与字阶

`tokens.json` SHALL 提供近黑底、米白、金色、朱红、次要灰与线灰；具体取值、字阶与版式参数见 `styles/dark-proof/GUIDE.md` 与 `tokens.json`。颜色语义 SHALL 全片固定：金色只表达被强调的样本、累积结果或揭示；朱红只表达失败、噪声或被证伪的结论；米白表达已知、中性、仍在场内的事实；次要灰只承担刻度、次要标签与方法说明；近黑底承担背景与负形。画面 SHALL NOT 引入第四种强调色。

字阶 SHALL 分为三级主体文字；中文使用宿主 `M2V Sans`，英文使用宿主 `M2V Inter`，数字使用等宽数字。主体区、左右边距与字幕安全区的约束见 GUIDE；字幕安全区 SHALL 只由场景上下文 `subtitleSafeArea` 提供，tokens SHALL NOT 复制一份几何。

#### Scenario: 场景读取色板

- **WHEN** 场景导入 `m2v/style` 的 `tokens` 并按语义取色
- **THEN** 得到与语义表一致的颜色；把朱红用于成功、把金色用于失败，或引入第四种强调色时，视觉复核判定不符合本风格

#### Scenario: 字幕避让

- **WHEN** 示例或无旁白作品绘制屏幕字幕
- **THEN** 字幕完整落在 `subtitleSafeArea` 内，主体与结论不与字幕重叠

### Requirement: 可复用组件

风格包 SHALL 提供 GUIDE 列出的舞台、巨型数字、可数点阵、论证图表、计数器、双语标题、屏幕字幕、手绘描线、光轨、爆散、扩散环与整屏冲击，以及确定性工具；具体参数见 `styles/dark-proof/GUIDE.md`。整屏冲击 SHALL 由 `impact` 组件提供 `shatter/reveal/formula/finale` 四个 preset，把 tokens 映射为透明 Canvas 粒子层的参数；光轨 SHALL 由 `sampleTrail` 与锥形笔触生成；局部爆散 SHALL 由 `explosionField`/`burstField` 与扩散环生成。屏幕字幕 SHALL 支持逐字展开、英文延迟、关键词高亮与节拍脉冲；计数器 SHALL 支持 2–3 层延迟残影；手绘线 SHALL 默认使用锥形笔触。

组件 SHALL 使用受控帧号或秒数、固定种子与显式缓动，SHALL NOT 使用挂钟、`Math.random`、CSS 动画或组件计时器。组件 SHALL NOT 自动修改作品画面，必须由作品显式导入；组件 SHALL NOT 内置题材数学、文案、分镜、时长或音频时序。组件 SHALL NOT 直接导入第三方包，动效数学 SHALL 从 `m2v/code-scene` 导入。

#### Scenario: 确定性绘制

- **WHEN** 同一作品帧被两次独立录制
- **THEN** 同一帧画面一致，不因运行时刻或随机数变化

#### Scenario: 未显式导入

- **WHEN** 作品声明了风格但场景没有导入任何组件
- **THEN** 画面与未选择风格时相同，不发生自动换肤

#### Scenario: 组件不携带题材

- **WHEN** 检查组件可接受的 props 与包内源码
- **THEN** 组件只接收数量、状态、几何、缓动、强度、种子与文字等内容无关参数，不出现《样本》的数学、文案或事件时刻

#### Scenario: 组件绕过 SDK

- **WHEN** 风格组件直接导入 `perfect-freehand`、`three`、粒子引擎或计时器库
- **THEN** 组件导入闸门失败，须改为从 `m2v/code-scene` 导入

### Requirement: 运动与转场语法

`GUIDE.md` SHALL 规定：入场与抵达使用 `easeOutCubic`，画面内移动与状态切换使用 `easeInOutSine`，不做过冲；数字变化可用滚动、重影或溶解表现，但同一时刻只允许一个主运动；全片 SHALL 至多使用一次硬切，并把它放在论点转折处。

除硬切外的转场 SHALL 优先使用同一对象的形变、位移与光的延续；整屏透明度交叉淡化只用于次要层，旧层 SHALL 快速退出（8 帧内降到 0.15 以下）、新层 SHALL 稍后进入，整段 SHALL NOT 超过 16 帧。作品 MAY 使用全片缓慢单向推近，幅度 SHALL NOT 超过 8%，MUST NOT 往返、摇移或反复推拉；字幕与方法说明 SHALL NOT 参与缩放。所有变化 SHALL 由帧号或秒数驱动。

示例的 `DESIGN.md` SHALL 记录硬切的时间、前后镜头与论证作用；只有一次硬切的声明不能替代画面核对。

#### Scenario: 全片两次硬切

- **WHEN** 成片或设计记录中有两个及以上的硬切
- **THEN** 视觉复核判定不符合本风格，须合并其中一次或改为溶解

#### Scenario: 双重曝光

- **WHEN** 转场中旧层与新层同时高不透明，或旧层在 8 帧后仍高于 0.15
- **THEN** 视觉复核判定为重影，须改为锚点交接或缩短旧层退场

#### Scenario: 无理由运镜

- **WHEN** 画面在段落内持续推近或拉远，但没有改变尺度、数量或因果的理解
- **THEN** 视为装饰运镜，须删除或改写为对象状态变化

#### Scenario: 往返运镜

- **WHEN** 画面在段落内反复推近拉远，或推近幅度超过 8%
- **THEN** 视为无理由运镜，须删除或改为单向推近

### Requirement: 示例作品《样本》

仓库 SHALL 在 `styles/dark-proof/examples/sample/` 提供规范示例《样本》。示例 SHALL 为 general v8、1920×1080、30 fps、约 58 秒（1740 帧），SHALL 声明 `style.id: "dark-proof"`，SHALL 无旁白并在字幕安全区内绘制中英双语屏幕字幕。示例 SHALL 使用原创、确定性的环境床与稀疏事件音，生成媒体按配方恢复且不入库；SHALL NOT 使用参考片画面、音轨、字幕、文案、角色或分镜。

#### Scenario: 示例可校验

- **WHEN** 对 `styles/dark-proof/examples/sample` 运行 `m2v validate` 并恢复原创声音后运行 `m2v prepare`
- **THEN** 示例通过 v8 校验，画幅 1920×1080、30 fps、1740 帧，分镜无旁白，屏幕字幕在安全区内，场景入口存在

#### Scenario: 参考素材不进入成片

- **WHEN** 检查示例素材、场景源码与渲染输入
- **THEN** 不出现 `refs/` 路径、参考片帧、参考音轨或参考文案；参考片只作为并排基准与设计证据

#### Scenario: 有旁白作品误用为示例

- **WHEN** 示例分镜包含 `narrationSegments` 或依赖共享旁白字幕
- **THEN** 示例验收失败，须改为屏幕字幕或另建有声作品

### Requirement: 示例内容与数学口径

《样本》SHALL 围绕小样本幻觉展开，并至少覆盖以下可核对的关系：

- 3 条评价中每次翻转一条，均值摆动约 33 个百分点；
- 3/1000 = 0.3%，开场必须让观众看到“3 条”与“1000 个样本”的比例；
- 样本量从 3 增到 1000，样本均值的标准误约缩小 18 倍（`√(1000/3) ≈ 18.26`）；
- 误差减半需要样本量翻四倍（`√(4n)`）；
- 第一次的极端观测，第二次更可能靠近均值；这不是退步，而是均值回归；
- 局部样本为真、整体结论不成立，用“盲人摸象”作为文化锚点。

示例 SHALL 以小字方法说明写明“随机、独立、同分布”的数学假设，SHALL NOT 把示例数字说成对真实人群、产品或考试的统计结论，SHALL NOT 编造数据来源，SHALL NOT 提供医疗、投资或法律建议。方法说明属于必要注释，字号 SHALL 明显小于主体文字并置于次要位置。

#### Scenario: 数学关系可核对

- **WHEN** 对照分镜、场景源码与示例说明检查上述数字
- **THEN** 33 个百分点、0.3%、约 18 倍、四倍关系与均值回归均有画面或文案依据，计算与显示一致

#### Scenario: 把示例当现实结论

- **WHEN** 文案把 3 条评价的摆动写成某类人或某个产品的真实成功率，或省略数学假设
- **THEN** 示例验收失败，须改写为数学演示并补回小字方法说明

### Requirement: 参考风格证据

《样本》SHALL 按[参考风格契约](../../../.agents/skills/material2video/references/reference-style.md)产出 `outputs/style-reference.md`，记录借鉴分层、不借清单、八项指标（参考值、目标值、实际值、差值）、三张并排基准与 2 秒动效样片，并由独立子代理完成冷审。该记录是证据格式，SHALL NOT 被当作数值通过阈值；缺少任一材料视为还原度验收未完成。

#### Scenario: 材料齐全

- **WHEN** 示例产出 `style-reference.md`、并排基准图、2 秒样片与独立冷审记录
- **THEN** 还原度验收视为过程完备，无论冷审结论为何

#### Scenario: 只有形容词

- **WHEN** 风格记录只有“安静”“高级”“像参考片”等描述，没有八项数值与差值
- **THEN** 视为未完成，不得以注册成功或技术 QA 通过替代

### Requirement: 光效有来源且受节制

光效 SHALL 只服务状态变化：对象移动的轨迹、线条/曲线生长、评价翻转、爆散揭示与结尾回扣。每条局部光轨 SHALL 有可见来源；全片 MAY 使用 4 个整屏冲击，且 SHALL 绑定线溶解、全象揭示、公式收口与结尾回扣等具体对象；MUST NOT 用无来源的全屏装饰。硬切处 SHALL 只允许单环与局部低透明度闪光，SHALL NOT 放粒子或做全屏闪白。每拍 SHALL 至多一个整屏焦点，局部微光不计。1000 点阵 SHALL NOT 使用滤镜；粒子数、环数、光轨宽度与采样数 SHALL 受 tokens 限制。

整屏冲击期间 MAY 压暗点阵，使粒子成为唯一焦点；MAY 使用低速 ambient dust 作为连续微动，但 dust MUST 固定种子、缓慢漂移、低透明度，MUST NOT 随机闪烁。

#### Scenario: 光效无来源

- **WHEN** 画面出现没有对象移动、线条生长或揭示事件对应的随机闪烁或环境光斑
- **THEN** 视觉复核判定为装饰光，须删除

#### Scenario: 硬切放粒子

- **WHEN** 600 帧硬切处出现粒子爆散或全屏闪烁
- **THEN** 视为违反唯一硬切的克制边界，须改为单环与局部光

#### Scenario: 整屏冲击过密

- **WHEN** 同一拍出现两个及以上整屏冲击，或全片超过 5 个整屏冲击
- **THEN** 视觉复核判定为疲劳，须合并或删除

### Requirement: 可辨识的大象与真实局部取样

《样本》的“盲人摸象”段落 SHALL 使用可辨识的侧视大象几何，至少包含头、卷鼻、耳、眼、四腿与象牙，MUST NOT 使用无头鼻的团块。几何 MAY 取自 Lucide Lab `elephant`（ISC）并在作品内补象牙；来源、版本与许可 SHALL 登记在 `SOURCES.md`。

三个取样窗 SHALL 是同一大象几何的真实局部放大，窗心 SHALL 指向被放大的部位，并可用细引线标示；MUST NOT 用通用线纹、圆环或独立画的纹理冒充局部。窗内与整体 SHALL 共用同一组路径与生长进度。

#### Scenario: 可辨识性

- **WHEN** 观察 37–40 秒的代表帧
- **THEN** 能指出头、卷鼻、耳、眼、四腿与象牙，不把轮廓看成无头团块

#### Scenario: 通用纹理冒充局部

- **WHEN** 取样窗内出现与大象几何不对应的通用线纹或图案
- **THEN** 验收失败，须改为同一几何的局部放大

### Requirement: 微拍密度与 112 BPM 节奏

《样本》SHALL 保留 58 秒、1740 帧、八段论证、13 条屏幕字幕、10 个检查点与 600 帧唯一硬切；每段内部 SHALL 拆成 12–16 个微拍，任一主内容停留 SHALL NOT 超过约 1.5 秒。微拍 SHALL 至少改变一个可见状态（位置、数量、亮度、标记或文字强调），MUST NOT 只靠无信息运动填满。

示例 SHALL 使用 58 秒、约 112 BPM 的原创程序化配乐与密集事件音；声音 SHALL 由 `assets/synthesize.py` 确定性生成、按 `recipe.json` 校验摘要，MUST NOT 使用第三方采样或音乐服务。金点、点阵呼吸、计数器与关键词 MAY 按 112 BPM 做脉冲；视觉脉冲按帧取整，声音按采样时间精确对齐。

#### Scenario: 长停留

- **WHEN** 任一主内容停留超过约 1.5 秒
- **THEN** 须加入有语义的微事件，或压缩该段

#### Scenario: 微拍无可见变化

- **WHEN** 某个微拍只改变不可见参数，观众看不到任何状态变化
- **THEN** 视为未完成微拍，须补可见事件或删除

#### Scenario: 配乐来源

- **WHEN** 配乐来自第三方音乐服务或包含非原创采样
- **THEN** 示例验收失败，须改为确定性程序化生成
