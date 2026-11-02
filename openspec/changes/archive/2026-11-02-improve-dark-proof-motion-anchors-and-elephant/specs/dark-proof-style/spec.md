## MODIFIED Requirements

### Requirement: 可复用组件

风格包 SHALL 提供舞台、巨型数字、可数点阵、论证图表、计数器、双语标题、屏幕字幕、手绘描线、光轨、爆散与扩散环，以及确定性工具。光轨 SHALL 由通用 `sampleTrail` 与锥形笔触生成头部光晕、尾迹与尾尘；爆散 SHALL 由通用 `burstField` 与 `expandingRings` 生成粒子、核心光晕与环；扩散环 SHALL 支持虚线与旋转 dash。屏幕字幕 SHALL 支持逐字展开、英文延迟、关键词高亮与 `rise/settle/wipe`、`drift/dissolve/mask` 进出场；计数器 SHALL 支持 2–3 层延迟残影；手绘线 SHALL 默认使用锥形笔触。

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

- **WHEN** 风格组件直接导入 `perfect-freehand`、`svg-path-properties` 或计时器库
- **THEN** 组件导入闸门失败，须改为从 `m2v/code-scene` 导入

### Requirement: 运动与转场语法

`GUIDE.md` SHALL 规定：入场与抵达使用 `easeOutCubic`，画面内移动与状态切换使用 `easeInOutSine`，不做过冲；数字变化可用滚动、重影或溶解表现，但同一时刻只允许一个主运动；全片 SHALL 至多使用一次硬切，并把它放在论点转折处。

除硬切外的转场 SHALL 优先使用同一对象的形变、位移与光的延续：前一对象的状态变化生成下一画面；整屏透明度交叉淡化只用于次要层，且旧层 SHALL 快速退出（8 帧内降到 0.15 以下）、新层 SHALL 稍后进入，整段 SHALL NOT 超过 16 帧；SHALL NOT 把两层全亮画面长时间叠放。SHALL NOT 使用无叙事理由的持续推拉摇移。所有变化 SHALL 由帧号或秒数驱动。

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

## ADDED Requirements

### Requirement: 光效有来源且受节制

光效 SHALL 只服务状态变化：对象移动的轨迹、线条/曲线生长、评价翻转、爆散揭示与结尾回扣。每条光轨 SHALL 有可见来源；硬切处 SHALL 只允许单环与局部低透明度闪光，SHALL NOT 放粒子或做全屏闪白。全爆散 SHALL 只用于论证转折、结果揭示与结尾回扣，每拍 SHALL 至多一个光效焦点。1000 点阵 SHALL NOT 使用滤镜；粒子数、环数、光轨宽度与采样数 SHALL 受 tokens 限制。

#### Scenario: 光效无来源

- **WHEN** 画面出现没有对象移动、线条生长或揭示事件对应的随机闪烁或环境光斑
- **THEN** 视觉复核判定为装饰光，须删除

#### Scenario: 硬切放粒子

- **WHEN** 600 帧硬切处出现粒子爆散或全屏闪烁
- **THEN** 视为违反唯一硬切的克制边界，须改为单环与局部光

### Requirement: 可辨识的大象与真实局部取样

《样本》的“盲人摸象”段落 SHALL 使用可辨识的侧视大象几何，至少包含头、卷鼻、耳、眼、四腿与象牙，MUST NOT 使用无头鼻的团块。几何 MAY 取自 Lucide Lab `elephant`（ISC）并在作品内补象牙；来源、版本与许可 SHALL 登记在 `SOURCES.md`。

三个取样窗 SHALL 是同一大象几何的真实局部放大，窗心 SHALL 指向被放大的部位，并可用细引线标示；MUST NOT 用通用线纹、圆环或独立画的纹理冒充局部。窗内与整体 SHALL 共用同一组路径与生长进度。

#### Scenario: 可辨识性

- **WHEN** 观察 37–40 秒的代表帧
- **THEN** 能指出头、卷鼻、耳、眼、四腿与象牙，不把轮廓看成无头团块

#### Scenario: 通用纹理冒充局部

- **WHEN** 取样窗内出现与大象几何不对应的通用线纹或图案
- **THEN** 验收失败，须改为同一几何的局部放大
