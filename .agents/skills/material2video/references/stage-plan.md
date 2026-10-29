# 方案确定

首要问题：观众要理解什么，靠哪个对象、变化和机制理解？

## 必做

1. 确认受众、画幅、主题、事实边界与来源；用户方案足够时直接采用，否则按未决问题选案。
2. 先给每个概念找到可见对象与变化，再写文案：形象不成立就改句，不硬配图。核心对象与一个明确问题已经足够时，可先做局部构图或动态草样；原型须标明要回答的问题、素材精度和结论边界。正式扩展全片前完成足以执行的形象与逐场设计。方法见[讲解设计](explainer-design.md#先找形象再写文案)，判据见[看图诊断与形象判据](explainer-design.md#看图诊断与形象判据)。
3. 讲解片在现有逐场表记录主体、变化与不变量、目标关系、完整窗口和可能误读。优先考虑对象连续追踪、相机与尺度、过程与结果联动、回场；按需采用，不凑齐四种。方法见[讲解机制](explainer-design.md#四种讲解机制的执行方法)。
4. 先确定贯穿对象、可见事件和观众的信息顺序，再选素材与实现方式；在既有逐场表协调动作、读数、字幕和适用声音的事件时刻，方法见[贯穿对象与完整动作](explainer-design.md#贯穿对象事件和完整动作)。关键镜头按[导演设计](visual-creative-direction.md#导演设计观众按什么顺序看到)组织；普通镜头不额外填完整导演卡。
5. 在 DESIGN.md 声明现有 v2 制作合同及适用风险，映射场景/镜头与检查窗。轮次、人数及完成条件只读[审核策略](checkpoint-gates.md#审核计划与风险触发)。
6. 在原逐场表选定最难关系、最小完整试制段落及观众应能复述的认识；优先兼顾开场，覆盖不足另补，不固定 30 秒。执行见[完整段落试制](production-workflow.md#完整段落试制与逐段扩展)。按未决问题选择静态目标图、时序试验或实际动态原型；能复用同一场景逐步完善时沿用该场景，静态目标通过不替代实际核心片段。
7. 声明 `static-expression` 风险时，按风险制作所需目标关键帧并在扩展相关高投入实现前盲审；风险允许时可将实际场景逐步完善为核心样片并复用。新上下文只收评审包与中性条件，先描述后判定，适用的目标对照在同轮完成。执行与隔离要求见[独立评审](subagent-review.md)。

## 输入类型与源文处理

源文输入须有非空 article；优先使用已采用的 `article.accepted.md`，也可由 `project.materials.article` 指定。进入分镜前按本页讲解输入审查核验事实、核心主张和材料边界；候选稿须经用户明确采用并重新审查，不能把候选生成等同采用或审查通过。只按主题制作时使用 `input.kind: "topic"`，跳过源文审查，但每幕声明检索关键词。具体字段与版本以[分镜契约](storyboard-schema.md)为准。

## 触发时展开

- 首次写分镜：读[分镜契约](storyboard-schema.md)与[逐场表](visual-creative-direction.md#逐场设计表)。
- 搜集或入片素材/声音：读[素材声音契约](article-media-and-sound.md)和[载体选择](visual-material-selection.md)。
- 学习参考：读[参考拆解](reference-video-analysis.md)；明确要求像参考时再读[风格契约](reference-style.md)。
- 首次实现场景/相机/字体：读[运行时契约](code-scene-runtime.md)；选择风格时读该包 GUIDE。
- 作品选择 `style.id`：读[风格接入契约](style-pack.md)，按指导把参数、组件与资产显式落到 DESIGN.md；选风格不会自动换肤。
- 开始有旁白制作：读[配音契约](voice-and-rhythm.md#配音音色与语速)，按全文和服务信息选音；无旁白跳过。

## 完成与回退

事实边界和核心关系可观察，适用 G0–G3 证据齐全后进入制作与迭代。方案的目标或技术根本不成立时回到对应设计层；不以“以后精修”放行。记录与闭环见[制作流程](production-workflow.md#核心样片与全片粗片的回退决策)。


## 源文审查命令与记录


先在作品内保存非空 article.md。采用稿存在时使用 article.accepted.md；也可由 project.materials.article 显式指定源文。

```powershell
uv run m2v general input-review --storyboard videos/general/<slug>/storyboard.json
```

命令生成 outputs/input-review.json，记录源文相对路径、SHA-256 和正文计数（排除一级标题、标点和空白）。计数只用于记录，不要求 130～170 字。阅读原文后填写 status、claim、rationale、reviewer、problemSpans；通过时 status 为 pass、依据非空且 problemSpans 为空。工具不会自动判定语义通过。

不合格材料可运行 `m2v general candidate --article <article.md> --text-file <候选文本>`；原文保持不变，候选必须非空并绑定原文摘要。用户明确采用后执行 `m2v general adopt-candidate --article <article.md>`，再重新审查。源文或候选变化须重新生成；采用不等于审查通过。

当前审查是通用作品的源文语义审查，不要求单世界隐喻或连续性。分镜 `input.kind` 为 `topic` 时没有源文，跳过本审查；旧 production.json 与 singleScene 评审不能用于当前制作。
