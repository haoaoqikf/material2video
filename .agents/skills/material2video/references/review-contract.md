# 技术 QA 与独立视觉评审

正式设计样品的来源和交付检查见[网页原生样品](design-samples.md)：内部渲染与探索观察可以失败，样品交付必须独立通过；通用图片 pass 不代替原生采集。不得设置试制总时长/重试次数上限或以失败稿结束。静态目标仍须最小可编码局部视频，只证明实际静态范围，不强加动画或授权未验证过程。

只保留技术 QA、试制独立评审 trial 与当前完整候选独立终审 final。全片预演、粗片查看、局部复查是内部制作活动，不建立顺序门禁或声明式数量、布局、状态断言。

## 审核策略

每个制作周期至少有一次有代表性的独立试制观察和一次新代理终审。试制须覆盖所有影响当前方向的重要未知；不同片段可分批投喂，不以一个样片授权未覆盖机制。静态作品按实际静态窗口验证，不额外添加动画。

默认一名综合终审；具体观察能力/范围风险要求分工时，review start --split-final --basis <具体依据> 设置结构与视觉文案两名隔离终审。实质争议使用新代理复核；同一问题两轮修复无改善时匿名比较实质不同方案，合并到适用评审活动。

事实、来源、许可和用户硬约束由助手核验并在作品材料保留。技术和材料校验继续执行，评审不阻断候选导出；缺少有效评审不得报告制作完成。降级自审必须披露，不关闭独立项。

有用户指定或助手已采用并承诺的视觉目标时，助手负责将实际参考媒体和中性可观察采用特征带入既有同轮对照。盲看判断作品自身的吸引力、形象、构图及表达；对照判断目标效果的兑现和具体差距。理解、可读性和技术无错不能替代实际美术表现。缺少目标或覆盖不足时保持该目标未验证；明确目标失败不能改称偏好。研究方法见[具体标杆与深入拆解](reference-video-analysis.md)，不另加研究审批或风格审核轮次。

试制选案在现有 observations 中分别说明候选的吸引力、普通之处、与整体目标的主要差距，以及值得打磨或可作后续标准的依据；可以全部淘汰，不强制选赢家，不用总分或投票替代观察。主代理负责取舍、下一试验与整体品质，不能以独立 pass 免责或直接宣布阶段完成；实质分歧按原目标复核，不能反复换审挑通过。

正式 items 只放本次待验证范围，每项均受原失败闭环约束；备选/历史媒体可放 references，在 conditions 中中性注明用途，与整体品质标杆区分，随后同轮对照，不声称备选已独立盲看。方向争议确需全部候选匿名盲看时，可按[隔离执行](subagent-review.md)保留探索观察，再正式验证选定范围；不设例行新门禁，不把探索观察冒充导入通过。已经导入的失败不能通过淘汰、改放 references 或重开周期消除。

成功导出后的普通清理保留当前周期隔离包绑定的源媒体与目标媒体，包括位于 `previews/` 的文件；包内净化副本不能替代源文件摘要绑定。未导入或内容已过期的包仍保护其明确引用，引用记录损坏时停止清理并报告，不影响已生成候选。引用解析与清理共用作品写锁，无引用的旧媒体继续按原规则清理。

## 命令与周期

```powershell
uv run m2v review start --project <作品>
uv run m2v review pack --project <作品> --file <请求.json>
uv run m2v review import --project <作品> --file <报告.json>
uv run m2v review timeline --project <作品>
uv run m2v review retarget --project <作品> --file <用户目标变更.json>
uv run m2v qa --project <作品> --video <当前候选>
uv run m2v status --project <作品> --history --json
uv run m2v issues update --project <作品> --file <问题.json>
```

start 显式建立 version=2 新周期，归档旧问题正文并保留旧报告；不迁移旧通过。旧机器合同和旧请求/报告明确不兼容。DESIGN.md 是人读制作依据，不参与机器合同解析。

## 媒体与报告格式

请求 version=2 必填 round、fps、items、sources、sceneIds、displaySizes。sources 相对作品根，items.path 和 references 相对 outputs；均拒绝绝对路径、越界及符号链接。sceneIds 可为空，不要求全片分镜或 prepare；代码试制应登记实际场景依赖或完整来源文件。工具无法验证未登记的来源，助手必须如实声明。

```json
{"version":2,"round":"trial","fps":30,"items":[{"id":"window-1","path":"trial.mp4","window":[0,90],"dynamic":true}],"sources":["scenes/core.tsx"],"sceneIds":[],"displaySizes":[1920,393]}
```

每个 item 指定中性 id、媒体 path、源媒体局部半开帧窗 window、dynamic。动态须完整可解码过程；工具裁出实际窗口并提取有序原生与手机帧。sampleStep 可选，试制默认逐帧、终审默认半秒，并保留首尾；根据关键动作加密，稀疏序列不足时补证。静态图片派生多尺寸，声音按实际覆盖记录。

conditions 列出中性原条件，不填写设计理由、标准答案、推荐、制作成本或完整设计。references 列出实际参考媒体路径，conditions 对应说明整体品质、专项表现、信息表达或备选/历史比较用途，不把整体目标缩成特征清单。提供非空 references 时必须同时提供非空 conditions，缺失则在创建包前拒绝；旧请求须补条件后重建，不改写历史。条件可以只核对事实，无目标媒体不代表验证了风格。文件相对 outputs，可为画面或完整片段；目标按对象、窗口和显示条件描述，不写“应当高级”等抽象评价。

`dynamic`标识编码视频媒体，不自动承诺运动。静止编码仅验证静态表现与一致性，不据此宣称动态或全片基线；动态目标的代表性仍须实际完整运动过程，未提供的运动、停留时间、声音与正文保持未验证。

二者在盲包外绑定，盲看不展示。盲看导入后以相同请求增加 reviewType=consistency、blindId=<原报告ID> 建立同轮对照，包内生成 conditions.json 并附净化后的实际目标媒体（若有），提示核对兑现及具体差距。对照与盲看来源、窗口、评审者及职责须一致。机器只核对已声明的输入与记录，无法发现未登记参考或自动判断研究深度、审美及阶段完成；助手不能省略应提供的目标。

目标媒体及采用条件在盲看请求中预先登记，隔离只是不向盲看者展示。盲看后才新增或修改目标会改变绑定，须重建该范围的盲看与对照；不能给原本无参考的旧盲报告直接追加目标来补出风格通过。

终审请求须为单个当前完整候选、[0,全片帧数]、实际 fps，且当前候选和 qa.json 的视频摘要、准备指纹有效；仅使用文件名或旧 QA 不足。

报告必填 version、round、reviewType、packPath、packSha256、reviewerId、isolation、focus、verdict、observations、coverage、invocation；对照另含 blindId。packPath 是相对 outputs 的 manifest.json；invocation 为真实调用记录的 path/sha256。focus 为 comprehensive 或已声明的 structure/visual-copy；isolation 为 independent-subagent/self-review/external-review。

coverage 每项为 id、window、status、observations、limitations、assessment；assessment 含 understanding、presentation、representativeness，每项为 status 与 observations。状态 pass/fail/insufficient；代表性和表现须具体观察。工具只验证记录完整性，不自动评判审美。

## 用户明确变更目标

已经绑定独立失败的目标不得由助手自行改写以规避问题。用户明确允许换基准或改变采用目标时，继续当前周期，先按新目标建立完整盲包，再用 `review retarget --file` 登记用户原话、要替代目标的失败报告ID及该新包的manifest摘要：

```json
{
  "version": 1,
  "source": "user",
  "instruction": "用户明确允许更换视觉基准的原指令",
  "reportIds": ["原独立失败报告ID"],
  "packPath": "review-pack/新包ID/manifest.json",
  "packSha256": "0000000000000000000000000000000000000000000000000000000000000000"
}
```

`packSha256`填写实际摘要。一次登记只选择同轮同职责的开放独立必改失败；新包须为当前有效盲包且带实际参考和中性条件。登记阶段（包括final）严格保持来源、场景、观察项身份、窗口覆盖和显示尺寸，只替换参考与中性条件。登记后的全片复查仍遵守当前完整候选规则，允许剪短或重排，不把登记当作改写旧问题范围。

登记写入摘要绑定的历史收据，旧scope、失败结论和周期不改变，也不自动关闭问题。新独立盲看必须在登记后实际开始，导入及同轮对照也须晚于登记；新目标双通过后才按正常issues update关闭所列问题。未列问题仍按原目标；多次用户换目标采用该问题最新的有效登记。损坏记录使相关关闭失效；登记不能用来借用旧通过或重开周期。工具校验声明与证据，无法认证自然语言用户身份，操作者必须先依据真实对话核实授权，不得伪造用户原话。

## 问题状态与记录

唯一问题块 m2v-issues-v2 包含 version=2、cycleId、items。每项 id、cycleId、status（open/closed）、required、round（trial/final/internal）、scope、reportId（内部问题为 null）、versionRefs、cause、observations；可选 closureReportId、evidence。cause 为 implementation/design/mixed/undetermined，未定位不能关闭。

独立失败自动登记必改。关闭须绑定晚于原失败、当前、同范围同类独立通过及适用同轮对照，保留原中性条件、目标媒体、职责、显示尺寸与历史（用户明确变更目标须按上节登记替代，原记录仍保留）；局部复查覆盖原窗口，全片问题由当前完整候选终审复查，剪短或重排无需保留旧全片时长；自审或跨周期报告不得关闭。内部问题关闭须有效实际复查证据。status 只读展示证据，不推断创作阶段；基线保护活动引用，损坏或未知引用拒绝清理。
