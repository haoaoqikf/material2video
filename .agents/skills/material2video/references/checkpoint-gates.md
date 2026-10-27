# 检查点门、审核策略与基线保留

本契约适用于新启动 general 作品和后续重新启动的重制；存量在制作品沿用启动时合同，已交付作品不补造历史证据。v1 合同明确拒绝，不提供兼容执行、自动迁移或继承通过。金融和住宅使用专用契约。

门是助手声明制作完成的条件，不是用户审批或 CLI 导出硬门禁。G0–G6 是证据索引，不等于七次人工审核；独立审核轮次和人数由唯一审核策略从合同派生。

## 门、四阶段与审核轮

<!-- generated:production-gates:start -->
| 门 | 阶段 | 范围 | 检查方式 | 证据 |
|---|---|---|---|---|
| G0 | 方案确定 | 全片 | 外部报告登记 | 当前输入、事实与许可审查及不适用项 |
| G1 | 方案确定 | 全片 | 自动检查 | v2 合同、审核计划与设计声明一致性 |
| G2 | 方案确定 | 全片 | 自动检查 | 适用风险的独立目标关键帧及观察 |
| G3 | 方案确定 | 全片 | 自动检查 | 分镜映射自动检查；适用风险的 animatic 观察 |
| G4 | 粗片验证 | 检查点 | 自动检查 | 每场默认检查点断言、量测、状态边界；计划选中的核心窗须独立观察 |
| G5 | 粗片验证 | 全片 | 外部报告登记 | 一份全片粗片综合报告，覆盖全部场景、结构、衔接、节奏与视觉风险 |
| G6 | 最终验收 | 全片 | 外部报告登记 | 当前候选技术 QA、完整全片证据与计划要求的终审 |
<!-- generated:production-gates:end -->

审核轮的观察职责如下；是否适用及人数见下方生成策略：

| 轮 | 时点 | 执行者 | 必须覆盖 |
|---|---|---|---|
| 核心样片 | 扩展高投入实现前 | 独立代理 | 计划中每项未验证的核心风险；动态须完整事件窗 |
| 全片粗片 | 精修前 | 独立代理 | 全部场景、跨场衔接、结构、节奏、文案理解与视觉风险 |
| 最终成片 | 当前候选技术 QA 后 | 未参与前期评审的新代理 | 当前文件全片、理解、结构、节奏、视觉、文案与必要文字的手机可读性（示意／实拍边界标注除外） |

核心轮触发条件与人数见下方[审核计划与风险触发](#审核计划与风险触发)的生成策略。不同风险可以同轮分批投喂，但报告须逐项覆盖，不能用一个代表事件授权所有未验证风险。粗片和最终两轮不可互相替代。最终默认一人，不表示所有轮共用同一人。

门与轮不是一一对应：核心轮报告可以绑定 G2/G3/G4 的多个检查事件；普通镜头 G4 检查通过即可关闭，不再等待 G5 批量回绑；G5 有权发现并重开任意场景问题。

## 唯一设计合同 v2

在 DESIGN.md 内保留且仅保留一个 `m2v-checkpoints` 围栏 JSON 块。合同 `version` 必须为 2，与 v8 storyboard 版本独立，不进入 storyboard 或渲染缓存指纹。

顶层字段：`version`、`cycleId`、`fps`、`width`、`height`、`reviewPlan`、`scenes`，可选 `constraints`、`retrospective`。`cycleId` 标识当前制作周期；旧周期事件不得授权新周期。`structureRisk`、`acceptanceChecks` 和 v1 其余字段一律拒绝。

每场包含 `id`、`durationFrames`、`shots`、`checkpoints`。镜头包含全片唯一 `id`、`tier`、`window`，可选 `core` 与 `timeStructure`。检查点含全片唯一 `id`、`shotId`、`frame`、`window`、`expected`、`textPlan`、`claims`、`forbidden`，可选 `measurement`、`sampleStep`、`minEventFrames`、`manualEvidence`、`statePlan`。ID 使用字母数字、下划线和连字符，最长 96 位。

每场至少一个默认检查点；内部镜头按真实状态变化和风险补充，不要求每个内部镜头各有一套。普通镜头可以只声明用途与必要断言。`expected` 可以是空列表，但不能因此跳过实际内容核查。

`timeStructure` 只在依赖揭示时机的风险窗必填，含 establish、pause、change、reveal、result、hold；不适用段可省略或写 `window: null` 与原因。不再因 A 级标签强制六段。

全部帧窗是场景局部左闭右开区间，采样 frame 必须处于镜头与检查点帧窗内。

`expected` 是 role/count 断言列表，可选 state/color/visible/tolerance；`textPlan` 是 role/text/window 列表；`claims` 含 id/value/unit/basis，可选 role，同 ID 不可声明不同值；`forbidden` 是禁止出现的可见文字列表。`statePlan` 是 `{window, expected}` 列表，窗口落在所属镜头内且同角色不重叠。采样在步长和指定帧之外，自动加入 textPlan、statePlan 与 timeStructure 全部边界的前一帧、边界帧和后一帧，并去重、裁到检查窗。边界覆盖不证明全部连续运动正确，密度和完整窗口评审仍适用。

## 审核计划与风险触发

`reviewPlan` 必需 `basis` 和 `risks`。`basis` 写明适用性依据；`risks` 允许为空，但空列表意味着作品没有未决的核心表达、结构时序或动态风险，不能用来掩盖已知问题。每项风险含唯一 `id`、`kind`、`scope.checkpointIds`、`reason`、`requiredEvidence`，不得手填人数。

<!-- generated:review-risks:start -->
| kind | 门 | 额外要求 | 不触发的情况 |
|---|---|---|---|
| `static-expression` | G2 | 独立目标关键帧与盲看，覆盖该风险所需建立/结果/揭示状态 | 只是 A 级标签、普通标题或已验证布局 |
| `structure-timing` | G3 | animatic 观察，可与核心样片同轮 | 仅因片中有动画或 A 级镜头 |
| `core-event` | G4 | 完整动态窗口；静帧不能替代 | 无实质动态风险的静态作品 |
| `split-final` | G6 | 两名新且互相隔离的终审代理，分别负责结构与视觉文案 | 时长、镜头等级或主观追求更高级本身 |
| `substantive-dispute` | G4 | 新代理先盲看，再核对中性原条件，单独保留争议结论 | 纯审美偏好差异 |
| `repeated-failure` | G4 | 至少两个实质不同的匿名候选，包含删短、重排或替换机制 | 第一次重要返工 |
<!-- generated:review-risks:end -->

`split-final` 的专业风险依据须具体指向当前观察能力或覆盖限制，不允许笼统写“高风险”。用户明确的硬性审核要求可增加要求，不可被默认策略覆盖。删除风险或修改目标不能直接关闭关联的未解决问题。

<!-- generated:review-rounds:start -->
核心审核风险：`static-expression`、`structure-timing`、`core-event`、`substantive-dispute`、`repeated-failure`。镜头等级不决定审核人数。

| 审核计划 | 核心轮 | 粗片 | 终审 | 独立调用合计 |
|---|---|---|---|---|
| 无核心风险，常规终审 | 0 | 1 | 1 | 2 |
| 无核心风险，split-final | 0 | 1 | 2 | 3 |
| 有核心风险，常规终审 | 1 | 1 | 1 | 3 |
| 有核心风险，split-final | 1 | 1 | 2 | 4 |
<!-- generated:review-rounds:end -->

## 观测与来源

DOM 使用 data-m2v-role/data-m2v-state；可选 `window.__M2V_REVIEW_STATE__` 提供 role/count 状态对象列表，只用于开发读取，不进入画面。Canvas/WebGL 没有可靠可见状态观测时提供逐项人工证据，否则保持未验证，不能把内部模型数等同实际可见对象数。

`measurement` 可声明 bodyRoles、thresholdSource、minFont393、allowedOverlaps、maxTextCharacters、subtitleTop。原生字号乘 393/原生宽度得手机等效字号；阈值与文字预算必须有来源。父子包含与 allowedOverlaps 中有意重叠不误判，其他可见元素相交报告复核。裁切检查画布和裁剪祖先；DOM 不证明全部像素遮挡。未标记元素不在自动覆盖范围，需人工补证。

采集输出原生尺寸、852 宽及 393 宽等比例图，竖屏保持 1080×1920 原生画幅。sampleStep 不得大于待判断的 minEventFrames；完整窗口包括状态边界，连续运动无法确认时补片段或逐帧证据。B/C 没有设计图时只验合同，不宣称完成设计图对照。

独立目标图清单在 outputs/production/design-frames.json。仅 `static-expression` 风险涉及的检查点需要建立/结果/揭示图，852 与 393 宽由工具从原图派生。来源标签不能单独证明独立制作；PNG 实际尺寸和源记录摘要均须有效。

## 命令与事件

```powershell
uv run m2v gates check --project <作品> --gate G1
uv run m2v gates check --project <作品> --gate G2
uv run m2v gates check --project <作品> --gate G3
uv run m2v gates check --project <作品> --gate G4 --checkpoint <ID>
uv run m2v gates register --project <作品> --file <检查报告.json>
uv run m2v gates pack --project <作品> --file <打包请求.json>
uv run m2v gates timeline --project <作品>
uv run m2v review import --project <作品> --file <独立报告.json>
uv run m2v issues update --project <作品> --file <问题.json>
uv run m2v status --project <作品> --history --json
uv run m2v gates rebuild --project <作品>
uv run m2v gates repair --project <作品>
uv run m2v baseline create --project <作品> --reason <重制原因> --files video.mp4
uv run m2v baseline prune --project <作品>
```

check 生成报告并登记；G0/G5/G6 用 register 登记外部事实/审查报告，不自动给审美通过。报告字段 gate、sceneId、checkpointId、status、checks、evidence、upstream；场景外范围 ID 为 null，checks 每项 name/status/detail，evidence 每项 path/sha256（相对输出根），upstream 由当前制作依赖摘要绑定。可选 retrospective、coverage、reviewRequired、notApplicableReason。status 为 pass/fail/unverified/not-applicable；只有 G2 在没有 `static-expression` 风险时才允许整个门不适用。

history.jsonl 位于 outputs/production，事件包含唯一 ID、作品/周期、类型、时间、门/场景/检查点、证据及上游摘要。事件追加在作品写锁内串行进行，重复导入幂等；gates.json 是显式可重建快照。status 永远只读，检查当前文件，不能盲信快照。历史损坏显示诊断并禁止推断通过，repair 先保留损坏原件再恢复可验证前缀。

通过需当前文件存在且摘要匹配、上游有效、计划要求的独立评审齐全、无本范围未关闭必改。降级自审只显示旗标，不关闭独立项。自身结果优先级为过期、阻断、待评审、进行中、未开始；合法不适用单列。门的 `evidenceStatus` 保留自身检查与评审结果，`prerequisites` 列出未满足的前置门，`ready` 表示自身通过／不适用且前置齐全；自身通过但前置未完成时汇总 `status=等待前置`，不得冒充过期。G4 明细同样列出自身结果和前置条件，并保留 `checkStatus` 单列自动检查。普通镜头检查通过即关闭，不再显示待批量回绑。

唯一问题表仍为 outputs/visual-notes.md，机器块为 m2v-issues JSON 列表。每项 id、status=open/closed、required、gate、sceneId、checkpointId、caughtAt、catchableAt、evidence、versionRefs；可选 uncatchableReason。关闭须有当前复查证据，迟到缺陷须有早期门回归或不可拦截原因。正文记录现象与处理历史，状态只引用 ID；解析失败不得推断无引用。

## 隔离包与每轮覆盖

打包请求字段 gate、scene_id、checkpoint_ids、files、kind、display_sizes；可选 review_type、timecodes、blind_id。kind 为 design-keyframe/animatic/scene-window/rough-timeline/final-video。普通包只复制中性媒体，不接收任意源码或 HTML；文件改为中性名。盲包排除设计、分镜、源码、旧结论和匿名映射；consistency 包只用于同轮设计对照。

独立报告含 gate、round（core/rough/final）、roundId、sceneId、checkpointIds、packPath、packSha256、reviewerId、isolation、reviewType、verdict、observations、checkIds、focus、coverage、invocation。`isolation=independent-subagent` 才计独立；一致性对照不计人数，也不替代盲审。manifest、报告、调用记录与来源文件均以 SHA-256 绑定。

每轮报告提供一份 `coverage` 覆盖表：每项 checkpointId、window、status、observations、evidence、issues。窗口必须等于检查点完整检查窗，evidence 必须来自投喂的评审包。rough 与 final 盲审必须覆盖全片检查点；final 的 consistency 对照覆盖适用目标图检查点。核心轮动态风险项必须附过程片段，端点静帧不足。所有来源证据摘要绑定事件，变化后相关报告失效。

同一份报告可通过 `checkIds` 绑定多个门的检查事件，逐项校验后幂等登记；任一绑定无效则整份拒绝，不留部分成功事件。final 轮必须使用未参与该作品前期评审的 reviewerId，并绑定当前候选视频摘要。`split-final` 时两名评审者互不读取报告、各自独立导入。

### 设计对照与 blind 顺序

终审者先只读取当前成片盲包，写出不可覆写的 blind 观察；之后才能创建 `review_type=consistency` 包，查看适用目标图与中性条件。两阶段可由同一代理完成，对照包必须引用同一轮 blind 报告的 `blind_id`，且创建时间晚于盲审落盘。`readReportIds` 在盲审时为空，对照时只允许同一轮的 blind 报告。先对照再补盲审、或对照结论替代盲审的，均拒绝。

无独立目标图的镜头只验用途与实际表现，不追补目标图，也不要求五维三方空表。

## 依赖范围与证据失效

场景证据按实际依赖绑定：导入源码、所用素材 ID、字体、全局配置与准备输入。同一文件摘要在一次查询内只读取一次。动态导入、无法解析的本地引用或动态素材 ID 保守扩大范围并在状态中披露原因，不伪称精确。合同范围、源码、素材、字体或准备输入变化使对应细项过期；未被场景使用的文件变化不误伤无关场景。最终视频摘要变化必须重做当前技术 QA 与全片综合终审，但不自动重开未变的选案、目标图和场景量测。

局部布局或字幕改动复查本窗与相邻衔接；核心关系、叙事顺序、总时长或全局样式变化复查相关核心风险与全片结构。

## G5 粗片播放器

G5 timeline 复用正式 ArticleExplainer composition 和准备音轨，将必要媒体及播放器依赖复制进隔离包。用本地 HTTP 服务打开包内 index.html，不读取作品目录，不额外编码全片。缺失缓存仅补录缺区间；DOM 量测仍可能运行浏览器，不伪称只解码缓存。不能播放时补分场片段、跨场窗口及完整顺序，证据不足不放行。

每候选不先编码完整草稿；真实缺陷修复允许新候选。生成计数区分请求、真实生成尝试和成功，验收重试/复制不计编码。

## 基线保留与清理

默认完整版本目标是当前、直接前一个重置版、首版共 3 个（重合时更少）；额外保护引用通常使其为 4 个，多引用可超过 4 个并报告数量与原因。引用保护优先，解除后下次清理回到目标。局部修复不新增重置，但覆盖前仍保留比较候选（create --candidate），也纳入媒体统计。

活动比较登记 outputs/production/comparisons.json，列表每项 status=active/closed 与 versionRefs；未知/损坏引用阻止清理。基线位于 outputs/baselines/<id>，保留级别只有 full/record-only。manifest、摘要、准备记录、问题表快照、评审报告台账和关键帧记录长期保留；仅视频、音频和媒体序列可删除。

prune 在作品写锁内先验证记录与引用，再原子登记降级和待删清单，最后幂等删除本基线目录内媒体，全部完成才写 prunedAt。普通交付清理保留制作门、评审包和基线目录；不能越权删除共享素材或缓存。

人工补证 manualEvidence 为输出根内 path/sha256 列表；JSON 报告包含 checkpointId、当前 upstream、verifiedBy、observations、checks。只补同名未验证项，不覆盖已观察的缺陷。B/C 没有设计图时 animatic 显示明确占位，仅供时序观察，不推断最终美术通过。
