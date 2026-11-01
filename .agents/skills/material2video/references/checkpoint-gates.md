# 检查点门、审核策略与基线保留

本契约适用于新启动 general 作品和后续重新启动的重制；存量在制作品沿用启动时合同，已交付作品不补造历史证据。v1 合同明确拒绝，不提供兼容执行、自动迁移或继承通过。金融使用专用契约。

门是助手声明制作完成的条件，不是用户审批或 CLI 导出硬门禁。G0–G6 是证据索引，不等于七次人工审核；独立审核轮次和人数由唯一审核策略从合同派生。

[Frontend Design](../../frontend-design/SKILL.md)与[运动设计](../../motion-design/SKILL.md)只提供设计、观察词汇和判断方法，不新增门、风险类型、审核轮次、人数、评分或 CLI 判据。其上游的“反默认清单”和危险等级在本项目按设计默认处理，实际缺陷仍按本契约的性质分级与证据要求关闭。

## 门、三阶段与审核轮

<!-- generated:production-gates:start -->
| 门 | 阶段 | 范围 | 检查方式 | 证据 |
|---|---|---|---|---|
| G0 | 方案确定 | 全片 | 外部报告登记 | 当前输入、事实与许可审查及不适用项 |
| G1 | 方案确定 | 全片 | 自动检查 | v2 合同、审核计划与设计声明一致性 |
| G2 | 方案确定 | 全片 | 自动检查 | 适用风险的独立目标关键帧及观察 |
| G3 | 方案确定 | 全片 | 自动检查 | 分镜映射自动检查；适用风险的 animatic 观察 |
| G4 | 制作与迭代 | 检查点 | 自动检查 | 每场默认检查点断言、量测、状态边界；计划选中的核心窗须独立观察 |
| G5 | 制作与迭代 | 全片 | 制作助手内部检查登记 | 制作助手的全片内部粗片检查，覆盖结构、衔接、节奏与已知风险 |
| G6 | 最终验收 | 全片 | 外部报告登记 | 当前候选技术 QA、完整全片证据与计划要求的终审 |
<!-- generated:production-gates:end -->

审核轮的观察职责如下；是否适用及人数见下方生成策略：

| 轮 | 时点 | 执行者 | 必须覆盖 |
|---|---|---|---|
| 核心样片 | 扩展高投入实现前 | 独立代理 | 计划中每项未验证的核心风险；动态须完整事件窗 |
| 全片粗片 | 阶段问题收敛前 | 制作助手内部检查 | 全片结构、信息推进、衔接、节奏及已知问题 |
| 最终成片 | 当前候选技术 QA 后 | 未参与前期评审的新代理 | 当前文件全片、理解、结构、节奏、视觉、文案与必要文字的手机可读性（示意／实拍边界标注除外） |

核心轮触发条件与人数见下方[审核计划与风险触发](#审核计划与风险触发)的生成策略。不同风险可以同轮分批投喂，但报告须逐项覆盖，不能用一个代表事件授权所有未验证风险。G5 内部检查不派独立代理；G6 独立终审覆盖当前全片。最终默认一人，不表示所有轮共用同一人。

门与轮不是一一对应：核心轮报告可以绑定 G2/G3/G4 的多个检查事件；普通镜头 G4 检查通过即可关闭，不再等待 G5 批量回绑；G5 或 G6 发现实际缺陷时均可重开任意场景问题。

适用核心样片评审在相关实现扩展前，G5 内部全片粗片检查在阶段问题收敛前，均按[推进与回退决策](production-workflow.md#核心样片与全片粗片的回退决策)检查设计及技术路线是否成立，明确通过、局部修复、补证或退回重设计。根本失败直接回退，不等两轮无改善。四种决策保存在制作记录正文，不新增合同／报告字段或状态枚举；独立报告继续如实使用既有 fail／insufficient 等结果，检查报告沿用 fail／unverified，相关必改项保持 open。回退或更改目标不能清除原失败；重新放行继续满足本契约的证据有效性、独立复查、依赖失效及问题关闭要求，不新增 CLI 导出硬门禁。

## 唯一设计合同 v2

在 DESIGN.md 内保留且仅保留一个 `m2v-checkpoints` 围栏 JSON 块。合同 `version` 必须为 2，与 v8 storyboard 版本独立，不进入 storyboard 或渲染缓存指纹。

顶层字段：`version`、`cycleId`、`fps`、`width`、`height`、`reviewPlan`、`scenes`，可选 `constraints`、`retrospective`。`cycleId` 标识当前制作周期；旧周期事件不得授权新周期。`structureRisk`、`acceptanceChecks` 和 v1 其余字段一律拒绝。

每场包含 `id`、`durationFrames`、`shots`、`checkpoints`。镜头包含全片唯一 `id`、`tier`、`window`，可选 `core` 与 `timeStructure`。检查点含全片唯一 `id`、`shotId`、`frame`、`window`、`expected`、`textPlan`、`claims`、`forbidden`，可选 `measurement`、`sampleStep`、`minEventFrames`、`manualEvidence`、`statePlan`。ID 使用字母数字、下划线和连字符，最长 96 位。

每场至少一个默认检查点；内部镜头按真实状态变化和风险补充，不要求每个内部镜头各有一套。普通镜头可以只声明用途与必要断言。`expected` 可以是空列表，但不能因此跳过实际内容核查。

`timeStructure` 只在依赖揭示时机的风险窗必填，含 establish、pause、change、reveal、result、hold；不适用段可省略或写 `window: null` 与原因。不再因 A 级标签强制六段。

全部帧窗是场景局部左闭右开区间，采样 frame 必须处于镜头与检查点帧窗内。

`expected` 是 role/count 断言列表，可选 state/color/visible/tolerance；`textPlan` 是 role/text/window 列表；`claims` 含 id/value/unit/basis，可选 role，同 ID 不可声明不同值；`forbidden` 是禁止出现的可见文字列表。`statePlan` 是 `{window, expected}` 列表，窗口落在所属镜头内且同角色不重叠。采样在步长和指定帧之外，自动加入 textPlan、statePlan 与 timeStructure 全部边界的前一帧、边界帧和后一帧，并去重、裁到检查窗。边界覆盖不证明全部连续运动正确，密度和完整窗口评审仍适用。

画面文字的实现要与 `textPlan` 按帧对齐：窗口起点帧应已可见，排他终点帧应不可见；用不透明度渐变时，首末帧保留自动量测能识别的最小可见度。`allowedOverlaps` 只声明设计上有意相交的角色对；薄片、底座、手等结构性接触需在每个相关检查点逐一列出，显式声明正确画面中的必要重叠，而不是让量测把正确画面判成缺陷。

`measurement.subtitleRoles` 用于无旁白作品自绘的屏幕字幕：对命中角色检查包围盒完全落在字幕安全区内、单行且不横向溢出。它不替代 `subtitleTop` 对正文越界的检查，也不改变共享字幕层的量测；未声明该规则的检查点仍需帧序列与人工证据。

## 审核计划与风险触发

`reviewPlan` 必需 `basis` 和 `risks`。`basis` 写明适用性依据；`risks` 允许为空，但空列表意味着作品没有未决的核心表达、结构时序或动态风险，不能用来掩盖已知问题。每项风险含唯一 `id`、`kind`、`scope.checkpointIds`、`reason`、`requiredEvidence`，不得手填人数。

<!-- generated:review-risks:start -->
| kind | 门 | 额外要求 | 不触发的情况 |
|---|---|---|---|
| `static-expression` | G2 | 独立目标关键帧与盲看；实际 G4 核心窗须同轮目标对照 | 只是 A 级标签、普通标题或已验证布局 |
| `structure-timing` | G3 | animatic 观察；关键运动窗口须有加密帧或过程片段，可与核心样片同轮 | 仅因片中有动画或 A 级镜头 |
| `core-event` | G4 | 完整动态窗口；静帧不能替代 | 无实质动态风险的静态作品 |
| `split-final` | G6 | 两名新且互相隔离的终审代理，分别负责结构与视觉文案 | 时长、镜头等级或主观追求更高级本身 |
| `substantive-dispute` | G4 | 新代理先盲看，再核对中性原条件，单独保留争议结论 | 纯审美偏好差异 |
| `repeated-failure` | G4 | 至少两个实质不同的匿名候选，包含删短、重排或替换机制 | 第一次重要返工 |
<!-- generated:review-risks:end -->

`split-final` 的专业风险依据须具体指向当前观察能力或覆盖限制，不允许笼统写“高风险”。用户明确的硬性审核要求可增加要求，不可被默认策略覆盖。删除风险或修改目标不能直接关闭关联的未解决问题。

用户明确要求借鉴参考风格时，把尚未验证的关键采用项登记到适用的 `static-expression`／`structure-timing`／`core-event` 风险；`reason` 与 `requiredEvidence` 引用原[风格契约](reference-style.md)，不复制一套指标。预先区分关键采用项与允许偏离项；核心差距不能事后改名为有意偏离来放行，纯偏好差异不自动否决。机器不通过关键词猜测风险，计划完整性仍须人工核查。

`static-expression` 检查点除 G2 目标图观察外，实际 G4 片段也须核心盲审及同轮设计对照。G4 中有目标图的核心窗、G6 中全部适用目标图范围均须对照；G2 自身通过不等于实际实现兑现。配对须同一独立评审者、同轮、同一检查事件及当前有效证据，且覆盖相关检查点。不增加固定轮次或人数。

<!-- generated:review-rounds:start -->
核心审核风险：`static-expression`、`structure-timing`、`core-event`、`substantive-dispute`、`repeated-failure`。镜头等级不决定审核人数。

| 审核计划 | 核心轮 | 粗片 | 终审 | 独立调用合计 |
|---|---|---|---|---|
| 无核心风险，常规终审 | 0 | 0 | 1 | 1 |
| 无核心风险，split-final | 0 | 0 | 2 | 2 |
| 有核心风险，常规终审 | 1 | 0 | 1 | 2 |
| 有核心风险，split-final | 1 | 0 | 2 | 3 |
<!-- generated:review-rounds:end -->

## 讲解机制与关键采用项的关闭

承诺用画面建立对象身份、尺度、过程结果或回场关系时，未验证的关键项按既有风险类型登记，
不新增 kind、字段、轮次、人数或 CLI 硬门禁。目标在原逐场表声明；观察按
[视觉复核](visual-review-rubric.md#讲解关系的观察)、隔离执行按
[独立评审](subagent-review.md#讲解机制的隔离观察)。参考关键采用项同样适用。

独立对照确认关键关系仍主要依赖字幕、对象无法认回或过程未带来声明结果时，沿现有唯一问题表
登记必改，暂停依赖该失败机制的扩展。局部尺度、亮度或观察时长问题局部修复；机制或结构失败退回
重设计；采样、上下文不足补证且保持未验证。具体推进决策沿用[回退路径](production-workflow.md#核心样片与全片粗片的回退决策)。

技术 QA、目标图一致、外观相似、相同对象 ID 或共用状态均不能覆盖表达失败；作者解释及事后改成
“有意偏离”不能关闭原问题。复查须绑定当前候选，按原问题、完整窗口、显示条件与观察类型由独立
评审关闭。合法改目标保留失败历史，重做受影响验证；改变用户明确要求时仍须用户决定。
合理延迟揭示、文字用途、偏好与证据不足按视觉复核区分，不机械否决。
本规则用于后续制作与修订，不追溯重写存量作品的合同、报告或完成状态。

## 观测与来源

DOM 使用 data-m2v-role/data-m2v-state；可选 `window.__M2V_REVIEW_STATE__` 提供 role/count 状态对象列表，只用于开发读取，不进入画面。Canvas/WebGL 没有可靠可见状态观测时提供逐项人工证据，否则保持未验证，不能把内部模型数等同实际可见对象数。

`measurement` 可声明 bodyRoles、thresholdSource、minFont393、allowedOverlaps、maxTextCharacters、subtitleTop。原生字号乘 393/原生宽度得手机等效字号；阈值与文字预算必须有来源。父子包含与 allowedOverlaps 中有意重叠不误判，其他可见元素相交报告复核。裁切检查画布和裁剪祖先；DOM 不证明全部像素遮挡。未标记元素不在自动覆盖范围，需人工补证。

采集输出原生尺寸、852 宽及 393 宽等比例图，竖屏保持 1080×1920 原生画幅。sampleStep 不得大于待判断的 minEventFrames；完整窗口包括状态边界，连续运动无法确认时补片段或逐帧证据。G4 采集还会把检查窗内的事件帧、实际采样帧、漏采帧与真实最小间隔写入 `measurements.json` 的 `eventCoverage`；它只作诊断，不改变 `checks` 或门结果，作者据此调整 `sampleStep` 或补事件边界帧。B/C 没有设计图时只验合同，不宣称完成设计图对照。

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

计划选中的核心盲审覆盖项还须包含 `assessment`，分列 `understanding`（理解）、`presentation`（表现）、`representativeness`（证据代表性），每项含 `status=pass/fail/insufficient` 与非空 `observations`。覆盖结果取三项中最保守的结果：有 fail 则 fail，其次 insufficient，否则 pass。理解通过不能覆盖表现失败。G2 代表独立目标画面、G3 代表时序证据；G4 用于正式视觉放行时必须采用实际资产、光线、字体、文字合成与完整关键动作，不能以占位样片授权扩展。字段只用于评审，当前不渲染。旧核心报告缺少这些凭据时仅作历史，不补造或推断通过。

动态核心检查点（`core-event` 风险范围）引用的过程片段必须实际探测：至少一段可解码、有视频流与正时长的视频，其视频时长不短于该检查点窗口时长，容差一帧；多个短片段不得相加。报告导入与状态查询共用该检查，坏证据使完成为 false 但不改写历史、不阻止候选生成；判据与执行细节见[独立评审](subagent-review.md#评审包)。

```json
{
  "understanding": {"status": "pass", "observations": "完整窗口中能认回同一主体和新公开的关系"},
  "presentation": {"status": "fail", "observations": "揭示对象太暗，注意力仍停在旧主体"},
  "representativeness": {"status": "pass", "observations": "实际资产、字体、灯光与文字合成已用于该完整窗口"}
}
```

上例为 `assessment` 内容，对应覆盖项必须为 fail；它是评审观察示例，不是所有作品的统一视觉要求。

### 设计对照与 blind 顺序

终审者先只读取当前成片盲包，写出不可覆写的 blind 观察；之后才能创建 `review_type=consistency` 包，查看适用目标图与中性条件。两阶段可由同一代理完成，对照包必须引用同一轮 blind 报告的 `blind_id`，且创建时间晚于盲审落盘。`readReportIds` 在盲审时为空，对照时只允许同一轮的 blind 报告。先对照再补盲审、或对照结论替代盲审的，均拒绝。

无独立目标图的镜头只验用途与实际表现，不追补目标图，也不要求五维三方空表。

### 推进范围与独立缺陷关闭

`production.expansion` 逐检查点给出 `allowed` 和 `reasons`：全局 G0–G3 准备证据须有效，当前检查点的 G4 自身检查、适用独立观察与同轮对照须通过，相关必改项须关闭。另一检查点未完成不改变本检查点已有证据；无关准备工作可以继续。范围之外的实现不得借用该通过结果。`production.complete` 只在全部门 ready 且无诊断错误时为 true。技术 `stage/candidate` 保持原语义，`summary` 明示候选生成与制作完成的区别；状态不代表自动审美判定，不阻断取证渲染。

自动登记的 `REVIEW-` 问题保留原失败范围和必改性质，不可通过降级或改范围关闭。关闭须在 `evidence` 直接引用已导入的同范围、同类观察（blind/consistency）、当前有效独立通过复查报告；制作解释、过期报告、量测或降级自审均不能代替。目标变更使旧证据失效，仍需保留原问题并重新复查；普通确定性量测问题沿用原证据闭环。执行见[独立评审](subagent-review.md#评审判断与否决边界)。

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
