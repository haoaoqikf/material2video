# 方案确定

首要问题：观众要理解什么，靠哪个对象、变化和机制理解？

本阶段形成一份全片原则与一张逐场表，复杂未决风险才增加附件，模板见[设计记录](visual-creative-direction.md#12-designmd-模板)。

| 决定 | 写在哪里 | 判据 |
|---|---|---|
| 受众、命题、事实与约束 | 全片原则 | 主题具体、来源与口径可查 |
| 视觉、运动与声音分工 | 全片原则 | 共享规则能指导实际表达；方法读 [Frontend Design](../../frontend-design/SKILL.md) 与[运动设计](../../motion-design/SKILL.md)及各自适配 |
| 对象、变化、时序与认识 | 逐场表 | 每段有用途，执行帧与曲线引用分镜/代码事件 |
| 风险与证据 | 逐场表引用唯一合同 | 验收条件、窗口和显示尺寸可观察 |

## 必做

1. 确认受众、画幅、主题、事实边界与来源；用户方案足够时作为初始基线采用，目标优先，效果不成立时可调整方案，否则按未决问题选案。
2. 先给每个概念找到可见对象与变化，再写文案：形象不成立就改句，不硬配图。核心对象与一个明确问题已足够时，可先做局部构图或动态草样；原型须标明要回答的问题、素材精度和结论边界。判据见[看图诊断与形象判据](explainer-design.md#看图诊断与形象判据)。
3. 在既有逐场表记录主体、变化与不变量、目标关系、完整窗口和可能误读；优先考虑对象连续追踪、相机与尺度、过程与结果联动、回场，按需选用，不凑齐四种。方法见[四种讲解机制](explainer-design.md#四种讲解机制的执行方法)。
4. 复杂未决风险按[导演设计](visual-creative-direction.md#导演设计观众按什么顺序看到)组织；普通镜头不额外填完整导演卡。逐场表引用分镜或代码事件中的起止帧与命名曲线，不重复维护运动表，`linear` 只用于匀速跟踪、进度或旋转并写明用途。
5. 在 `DESIGN.md` 声明 v2 制作合同及适用风险，映射场景/镜头与检查窗；轮次、人数与完成条件只读[审核策略](checkpoint-gates.md#审核计划与风险触发)。
6. 选定最难关系、最小完整试制段落与观众应能复述的认识；按未决问题选择静态目标图、时序试验或实际动态原型，执行见[完整段落试制](production-workflow.md#完整段落试制与逐段扩展)。

逐场目标确定后、动态实现前，必须完成[整场细节编排](scene-detail-design.md)：考虑主体、文字、图标/配角、光影点缀、镜头剪辑和声音，选择写入同一 `DESIGN.md`；普通场景简写，复杂联动共用事件源。试制同时验证关系与声明的表现目标。

## 触发时展开

- 首次写分镜：读[分镜契约](storyboard-schema.md)与[逐场表](visual-creative-direction.md#逐场设计表)。
- 搜集或入片素材/声音：读[素材声音契约](article-media-and-sound.md)和[载体选择](visual-material-selection.md)。
- 学习参考：读[参考拆解](reference-video-analysis.md)；明确要求像参考时再读[风格契约](reference-style.md)。
- 首次实现场景/相机/字体：读[运行时契约](code-scene-runtime.md)；选择风格时读该包 GUIDE。
- 作品选择 `style.id`：读[风格接入契约](style-pack.md)，按指导把参数、组件与资产显式落到 `DESIGN.md`；选风格不会自动换肤。
- 开始有旁白制作：读[配音契约](voice-and-rhythm.md#配音音色与语速)，按全文和服务信息选音；无旁白跳过。

## 源文审查

先在作品内保存非空 `article.md`；采用稿存在时使用 `article.accepted.md`，也可由 `project.materials.article` 显式指定。

```powershell
uv run m2v general input-review --storyboard videos/general/<slug>/storyboard.json
```

命令生成 `outputs/input-review.json`，记录源文相对路径、SHA-256 和正文计数。阅读原文后填写 `status`、`claim`、`rationale`、`reviewer`、`problemSpans`；通过时 `status` 为 pass、依据非空且 `problemSpans` 为空。工具不会自动判定语义通过。源文或候选变化须重新生成；采用不等于审查通过。`input.kind` 为 `topic` 时跳过本审查。

## 完成与回退

事实边界和核心关系可观察，正式扩展前适用 G0–G3 证据须齐全；低成本原型可提前制作，G3 可复用当前有效 G4 过程证据，随后补齐适用独立时序观察。方案的目标或技术根本不成立时回到对应设计层；不以“以后精修”放行。记录与闭环见[制作流程](production-workflow.md#核心样片与全片粗片的回退决策)。
