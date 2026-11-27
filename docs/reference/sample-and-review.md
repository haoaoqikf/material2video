# 网页原生设计样品与媒体评审

本文件从 README 下沉，权威内容仍以 [`.agents/skills/material2video/references/`](../../.agents/skills/material2video/references/) 为准。具体见[网页原生样品](../../.agents/skills/material2video/references/design-samples.md)、[审核策略](../../.agents/skills/material2video/references/review-contract.md)、[评审工具协议](../../.agents/skills/material2video/references/review-protocol.md)。

## 网页原生设计样品

`m2v sample capture` 委托作品本地构建与采集，不需要完整分镜或配音。原生样品 v2 默认 static，只采集可复现网页和关键帧，不编码视频；motion 另生成完整过程。源码、实际依赖、字体、登记媒体、参数及产物均绑定，变化后重新采集。

试制及正式关键帧均独立盲审并做同轮目标对照。试制验证已成立的艺术方向，正式验证所选风格的成片完成度。对照按已登记的画面职责使用实际参考。研究试制的完整动态样片由总代理用有序帧、完整解码及适用信号核验。正式关键片段按审核策略做独立过程对照，核心时间机制需要时可登记正式过程盲审。总代理实际查看、初筛、核对报告并负责最终选案。[审核政策](../../.agents/skills/material2video/references/review-contract.md)

```powershell
uv run m2v sample capture --project <作品> --entry scenes/core.tsx --kind static --duration-seconds 3 --frame 30
uv run m2v sample serve --project <作品> --id <采集ID>
uv run m2v sample review --project <作品> --id <采集ID> --purpose keyframe --targets <目标.json>
uv run m2v review import --project <作品> --file <真实盲报告.json>
uv run m2v review compare --project <作品> --blind-id <盲报告ID>
uv run m2v review import --project <作品> --file <真实对照报告.json>
uv run m2v sample deliver --project <作品> --id <采集ID> --blind-id <盲报告ID> --comparison-id <对照报告ID> --basis <具体选案依据>
```

sample review 为同源关键帧自动派生来源、窗口、显示尺寸和只读隔离包，compare 根据封存目标生成同轮对照。静态和动态样品使用同一套关键帧报告参数交付。交付直接复制已有媒体。Windows 发布后恢复继承权限。

关键帧在正常尺寸核对阶段艺术效果，在手机等小屏核对核心形象、关键关系和必要信息。抽象细节只在小屏减弱时可随通过记录，见[不同观看尺寸的职责](../../.agents/skills/material2video/references/visual-review-rubric.md#不同观看尺寸的职责)。

同轮对照回传可直接观察的复查问题。主代理用原尺寸的前后实绘回答同一个问题，凭实际效果决定是否复送，见[返工交接](../../.agents/skills/material2video/references/production-workflow.md#返工交接)。

固定保留 RESEARCH.md、DESIGN.md 和每个正式场景文档。制作片段按[逐场循环](../../.agents/skills/material2video/references/scene-design.md#渐进设计与开发循环)从粗排逐步细化到精修和衔接复查。成熟外部组件、模型、材质、Shader 和开源方案优先采用与改造，只自研必要缺口。试制关键帧按[阶段标准](../../.agents/skills/material2video/references/visual-review-rubric.md#试制关键帧的通过标准)判断。同一个问题连续两次修改无明显改善时，按[暂停送审规则](../../.agents/skills/material2video/references/production-workflow.md#试制暂停送审与重新选案)先内部重选。AI 图只作内部构思或参考。

采集使用完整 Chromium 的无头模式；`uv run playwright install chromium` 会安装所需浏览器，仅安装 headless shell 不足以在 Windows 加载 WebGPU 的 DXC。代码场景可通过 `waitForFrame(PromiseLike)` 登记异步绘制，初始就绪和每帧/子帧在工作及合成完成后才放行；拒绝或超时仍失败，纯时间仍须实际验证。静态代码场景可在作品内采用路径追踪、OIDN 去噪等可选能力；共享层不登记这类依赖，采用时由作品把实际依赖、补丁、权重来源与许可写进自己的工程和锁文件，固定种子、样本与分块，在 GPU 与本地权重就绪后采集，并逐场核验确定性，不据此宣称动态已验证；模型权重由作品登记来源、许可和恢复摘要，不入库。

## 制作阶段与设计材料

- [三阶段制作](../../.agents/skills/material2video/SKILL.md)：研究与创意试制 → 正式设计 → 制作与验收。先比较同一关键场景的不同设计，按判断需要补足精度，再集中打磨；分别判断候选优劣与能否作为后续标准，允许全部淘汰。整体品质成立且在拟用链路重现后展开全片，具体选案与收敛见[研究与试制](../../.agents/skills/material2video/references/stage-research.md)。样片适用范围及整片复核见[审核策略](../../.agents/skills/material2video/references/review-contract.md)。
- [全片与场景设计](../../.agents/skills/material2video/references/scene-design.md)：总设计先组织叙事、共用视听规则和场景索引。逐场以既有 scene.id 回答四问，按需用对象、节拍、单体变化和光影模板展开，并区分预期和实绘结果。指南附复杂和简明的实作示例。分镜和代码维护执行参数，脚本支持全片或局部对应检查。
- [案例调研](../../.agents/skills/material2video/references/reference-video-analysis.md)统一在全片开展，形成可验证的镜头方案。[组件调研](../../.agents/skills/material2video/references/visual-components.md#成熟组件调研)分全片和场景两层，先查内部实现，按缺口查外部。全片案例、核心效果与共用选型归 RESEARCH.md，局部组件选型和验证归[场景文档](../../.agents/skills/material2video/references/scene-design.md#分工与对应)。

## 媒体评审

`m2v review start|pack|compare|import|timeline|retarget|reuse|scope|confirm-evidence|export` 统一周期、隔离包、报告和证据复用。评审 v4 声明 keyframe 或 process 用途；报告顶层及每项明确 adoption=adopt/reject，仅 pass 可以采用。旧评审通过不授权新版本，历史与未解决必改保留。

新评审包的原生尺寸展示图复用包内净化 PNG。其他尺寸按比例派生。报告导入后按摘要保存评审媒体。需要复核时，用 `review export` 恢复已校验的独立目录。

status 只读展示正式关键帧、适用的关键样片窗口、当前技术 QA、整片证据复核（`wholeFilmReview`）和待解决问题。超过 30 秒的作品须登记并通过全部必审样片窗口。技术候选可以提前生成。研究、试制和验收均无需播放观看或试听；整片复核基于当前候选的抽帧、时间轴和适用音频信号登记。

目标参考与中性条件绑定，盲看后不能暗换；真实用户改变已失败目标时使用 retarget 保留原指令及旧失败，再完成对应独立复查。完整字节及观察条件相同的 trial 双评可显式 reuse，当前技术来源仍核验。具体格式、调用与失效处理按需读[工具协议](../../.agents/skills/material2video/references/review-protocol.md)，隔离执行见[独立子代理](../../.agents/skills/material2video/references/subagent-review.md)。

导出后清理会保护当前周期评审包仍绑定的预览源媒体和目标媒体；源文件仍参与证据摘要校验，无引用的旧预览继续清理。无法确认引用时报告并跳过清理。

作品修订直接更新当前工程，旧版本基线保留数量为 0。当前成片在新版通过原有交付验证后替换。独立评审原件、失败和复查历史继续保留。
