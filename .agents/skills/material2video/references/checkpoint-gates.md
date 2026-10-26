# 检查点门、制作状态与基线保留

本契约适用于新启动 general 作品和后续重新启动的重制；存量在制作品本轮沿用启动时流程，已交付作品不补造历史证据。金融和住宅使用专用契约。门是助手声明制作完成的条件，不是用户审批或 CLI 导出硬门禁。

## 门与四阶段

| 门 | 阶段 | 证据 |
|---|---|---|
| G0 | 方案确定 | 当前输入、事实与许可审查及不适用项 |
| G1 | 方案确定 | DESIGN.md 合同解析、设计声明一致性 |
| G2 | 方案确定 | A 级/核心段落独立目标关键帧、来源核验与独立盲审 |
| G3 | 方案确定 | 实际分镜映射与时间线；A 级或结构风险另需 animatic 独立评审 |
| G4 | 粗片验证 | 逐场检查点、布局/状态观测、完整事件窗口与所需独立评审 |
| G5 | 粗片验证 | 跨场结构、声画承接、节奏、首次导演及 B/C 批量独立评审 |
| G6 | 最终验收 | 当前成片技术 QA、完整帧证据、两名隔离终审及交付来源检查 |

精制修订按问题影响更新上述证据。镜头 A/B/C 与独立评审 A/B 是不同等级，B/C 不免除独立性要求。G4 检查与评审分列：A 级二者通过才扩展，B/C 检查通过即可在 G5 批量评审并回绑。粗片验证完成须 G4/G5 都关闭；带问题迭代不等于阶段完成。全片评审聚焦跨场问题，仍可重开任何场景问题；迟到缺陷记录 caughtAt/catchableAt 并回填早期检查。

### 视觉事件与设计兑现的阶段归属

对本次更新后新启动的 general 作品及明确启动的重制，G4 执行[视觉事件检查](production-workflow.md#视觉事件检查)，G5 复核其跨场后的有效性；精制修订执行[设计兑现检查](production-workflow.md#设计兑现检查)，按影响更新 G4/G5 证据，G6 核验当前成片闭环并保留重开权。仍使用现有 checks/evidence、独立报告与唯一问题表，不增加门、合同字段或自动审美判定；在制作品不追溯切换。判断演练见[太阳系示例](../../../../examples/solar-system-journey/WORKFLOW_CHECK_EXERCISE.md)。

## 唯一设计合同

在 DESIGN.md 内保留且仅保留一个 `m2v-checkpoints` 围栏 JSON 块。格式版本 1，与 v8 storyboard 版本独立，不新增 storyboard 或运行时字段。完整实例见仓库 [复利设计](../../../../examples/compound-interest/DESIGN.md)。

顶层字段：version、fps、width、height、structureRisk、scenes，可选 constraints、retrospective、acceptanceChecks。本次修复后新启动的作品及明确启动的重制须声明 `acceptanceChecks: true`；缺省的在制合同不追溯增加完成凭据要求，不升级合同版本或改变渲染缓存。每场包含 id、durationFrames、shots、checkpoints；镜头包含全片唯一 id、tier、window，可选 core 与 timeStructure。检查点含全片唯一 id、shotId、frame、window、expected、textPlan、claims、forbidden，可选 measurement、sampleStep、minEventFrames、manualEvidence、statePlan。ID 使用字母数字、下划线和连字符，最长96位。

全部帧窗是场景局部左闭右开区间，采样 frame 必须处于镜头与检查点帧窗内。G1 不依赖场景源码；G3 才核验 storyboard 实际场景、时长和画幅。每镜头至少一个默认检查点；A 级与核心段落还需建立/结果关键帧，有揭示时增加揭示图，不能用场景截图冒充。

A 级 timeStructure 含 establish、pause、change、reveal、result、hold，每段记录 window、audience、visible、attention、toleranceFrames、failure。不适用段 window 为 null，并记录 notApplicableReason 和 alternative；不为填表制造停顿。适用段连续覆盖镜头窗口。

expected 是 role/count 断言列表，可选 state/color/visible/tolerance，默认在检查点采样帧核对数量；时间窗内其他帧负责布局与动态取证。textPlan 是 role/text/window 列表，核对文字出现与离开；claims 含 id/value/unit/basis，可选 role，同 ID 不可声明不同值。forbidden 是禁止出现的可见文字列表；语义禁止项仍由人工独立评审。

`statePlan` 是 `{window, expected}` 列表，window 采用场景局部半开窗且必须落在所属镜头内，expected 与默认对象断言同构；同角色状态计划窗口不得重叠。在匹配采样帧，状态计划覆盖同角色的单帧默认值，用于验证中途数量、颜色或状态。采样在步长和指定帧之外，自动加入 textPlan、statePlan 与 timeStructure 全部边界的前一帧、边界帧和后一帧，并去重、裁到检查窗。边界覆盖不证明全部连续运动正确，密度和完整窗口评审仍适用。

## 观测与来源

DOM 使用 data-m2v-role/data-m2v-state；可选 window.__M2V_REVIEW_STATE__ 提供 role/count 状态对象列表，只用于开发读取，不进入画面。Canvas/WebGL 没有可靠可见状态观测时提供逐项人工证据，否则保持未验证，不能把内部模型数等同实际可见对象数。

measurement 可声明 bodyRoles、thresholdSource、minFont393、allowedOverlaps、maxTextCharacters、subtitleTop。原生字号乘393/原生宽度得手机等效字号；阈值与文字预算必须有来源。父子包含与 allowedOverlaps 中有意重叠不误判，其他可见元素相交报告复核。裁切检查画布和裁剪祖先；DOM 不证明全部像素遮挡。未标记元素不在自动覆盖范围，需人工补证。

采集输出原生尺寸、852宽及393宽等比例图，竖屏保持1080×1920原生画幅。sampleStep 不得大于待判断的 minEventFrames；完整窗口包括状态边界，连续运动无法确认时补片段或逐帧证据。B/C 没有设计图时只验合同，不宣称完成设计图对照。

独立图清单在 outputs/production/design-frames.json（示例输出根为 videos/examples/<slug>/outputs）。frames 每项记录 checkpointId、phase=establish/reveal/result、width、path、sha256、source=independent-design、tool、createdAt、sourceRecord={path,sha256}、verifiedBy、verificationBasis。PNG实际尺寸和源记录摘要均须有效；来源标签不能单独证明独立制作。仅记录格式，不自动识别所有截图冒充。

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

check 生成报告并登记；G0/G5/G6 用 register 登记外部事实/审查报告，不自动给审美通过。报告字段 gate、sceneId、checkpointId、status、checks、evidence、upstream；场景外范围 ID 为 null，checks 每项 name/status/detail，evidence 每项 path/sha256（相对输出根），upstream 由当前制作依赖摘要绑定。可选 retrospective、coverage、reviewRequired、notApplicableReason。status 为 pass/fail/unverified/not-applicable；G2 无适用段落才允许整个门不适用。

history.jsonl 位于 outputs/production，事件包含唯一 ID、作品/版本、类型、时间、门/场景/检查点、证据及上游摘要。事件追加在作品写锁内串行进行，重复导入幂等；gates.json 是显式可重建快照。status 永远只读，检查当前文件，不能盲信快照。历史损坏显示诊断并禁止推断通过，repair 先保留损坏原件再恢复可验证前缀。

既有技术状态字段与可选 review.json 语义保持不变，制作状态在 production 命名空间扩展。通过需当前文件存在且摘要匹配、上游有效、独立评审齐全、无本范围未关闭必改；降级自审只显示旗标，不关闭独立项。自身结果优先级为过期、阻断、待评审、进行中、未开始；合法不适用单列。门的 `evidenceStatus` 保留自身检查与评审结果，`prerequisites` 列出未满足的前置门，`ready` 表示自身通过／不适用且前置齐全；自身通过但前置未完成时汇总 `status=等待前置`，不得冒充过期。G4 明细同样列出自身结果和前置条件，并保留 `checkStatus` 单列自动检查。最早未关闭门是当前门，但 B/C 等待 G5 批量评审时下一步不能回到等待自身。

唯一问题表仍为 outputs/visual-notes.md，机器块为 m2v-issues JSON 列表。每项 id、status=open/closed、required、gate、sceneId、checkpointId、caughtAt、catchableAt、evidence、versionRefs；可选 uncatchableReason。关闭须有当前复查证据，迟到缺陷须有早期门回归或不可拦截原因。正文记录现象与处理历史，状态只引用 ID；解析失败不得推断无引用。

## 隔离包与粗片

打包请求字段 gate、scene_id、checkpoint_ids、files、kind、display_sizes；可选 review_type、timecodes。kind 为 design-keyframe/animatic/scene-window/rough-timeline/final-video。普通包只复制中性媒体，不接收任意源码或 HTML；文件改为中性名。盲包排除设计、分镜、源码、旧结论和匿名映射；设计对照图只用于 consistency 包。

独立报告含 gate、sceneId、checkpointIds、packPath、packSha256、reviewerId、isolation、reviewType、verdict、observations、checkIds；G6 另需 focus=structure/visual-copy，两个不同代理覆盖两类职责。isolation=independent-subagent 才计独立；consistency 不计审美通过，其他方式显著降级。manifest、报告、来源文件均以 SHA-256 绑定。批量报告逐检查点回绑；未覆盖项保持待评审。

### 表达检查的完成凭据

启用 acceptanceChecks 后，独立报告增加 `acceptance` 列表，每项包含 checkpointId、kind、window、status、observations、evidence；window 必须等于该检查点完整检查窗，status 为 pass/fail/insufficient，observations 为非空实际观察，evidence 为输出根内 path/sha256 列表。所有来源证据摘要均绑定事件，变化后相关报告失效。报告 verdict=pass 时所有凭据也须 pass。

- G4 的 A 级或 core 检查点必须有 `kind=visual-event` 的独立 blind 凭据；G5 批量报告可以回绑 G4。通用通过或降级自审不能代替该项。
- G6 必须覆盖上述全部核心检查点的 `kind=design-fulfillment` 凭据，使用单独 consistency 包；导入前，同一 checkId 必须已有当前有效独立 blind 观察。它不替代原有两名隔离终审，也不能先对照再补盲审。
- design-fulfillment 额外包含 dimensions 对象，键固定为 composition-scale、spatial-hierarchy、impact、attention、timing，每项包含 status 与 observations；design 对象含 direction、keyframes、animation，各为非空 path/sha256 列表，分别引用中性导演条件、独立目标关键帧和当前动画证据。
- 系统仅校验覆盖、记录和来源，不自动判断是否值得看或有冲击力。缺项列入 `missingAcceptance` 并保持待评审；独立失败阻断制作完成。未启用的存量在制合同不补项，技术导出行为不变。

可复制的 JSON 示例与规则演练见[太阳系检查演练](../../../../examples/solar-system-journey/WORKFLOW_CHECK_EXERCISE.md#结构化完成凭据示例)。

G5 timeline 复用正式 ArticleExplainer composition 和准备音轨，将必要媒体及播放器依赖复制进隔离包。用本地 HTTP 服务打开包内 index.html，不读取作品目录，不额外编码全片。缺失缓存仅补录缺区间；DOM量测仍可能运行浏览器，不伪称只解码缓存。不能播放时补分场片段、跨场窗口及完整顺序，证据不足不放行。

每候选不先编码完整草稿；真实缺陷修复允许新候选。生成计数区分请求、真实生成尝试和成功，验收重试/复制不计编码。

## 基线保留与清理

默认完整版本目标是当前、直接前一个重置版、首版共3个（重合时更少）；额外保护引用通常使其为4个，多引用可超过4个并报告数量与原因。引用保护优先，解除后下次清理回到目标。局部修复不新增重置，但覆盖前仍保留比较候选（create --candidate），也纳入媒体统计。

活动比较登记 outputs/production/comparisons.json，列表每项 status=active/closed 与 versionRefs；未知/损坏引用阻止清理。基线位于 outputs/baselines/<id>，保留级别只有 full/record-only。manifest、摘要、准备记录、问题表快照、评审报告台账和关键帧记录长期保留；仅视频、音频和媒体序列可删除。

prune 在作品写锁内先验证记录与引用，再原子登记降级和待删清单，最后幂等删除本基线目录内媒体，全部完成才写 prunedAt。普通交付清理保留制作门、评审包和基线目录；不能越权删除共享素材或缓存。

人工补证 manualEvidence 为输出根内 path/sha256 列表；JSON报告包含 checkpointId、当前 upstream、verifiedBy、observations、checks。只补同名未验证项，不覆盖已观察的缺陷。B/C 没有设计图时 animatic 显示明确占位，仅供时序观察，不推断最终美术通过。
