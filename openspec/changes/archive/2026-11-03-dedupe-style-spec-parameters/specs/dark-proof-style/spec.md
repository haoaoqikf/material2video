## MODIFIED Requirements

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
