# 评审工具协议

审核职责与采用规则见[评审政策](review-contract.md)，隔离执行见[独立评审](subagent-review.md)。本页只维护命令、字段、摘要及失败关闭的技术约束。

## 命令与周期

```powershell
uv run m2v review start --project <作品>
uv run m2v review pack --project <作品> --file <请求.json>
uv run m2v review import --project <作品> --file <报告.json>
uv run m2v review timeline --project <作品>
uv run m2v review retarget --project <作品> --file <用户目标变更.json>
uv run m2v qa --project <作品> --video <当前候选>
uv run m2v status --project <作品> --history
uv run m2v issues update --project <作品> --file <问题.json>
```

start 显式建立 version=3 新周期，归档旧问题正文并保留旧报告；不迁移旧通过。旧机器合同和旧请求/报告明确不兼容。DESIGN.md 是人读制作依据，不参与机器合同解析。

## 媒体与报告格式

请求 version=3 必填 round、purpose、fps、items、sources、sceneIds、displaySizes。sources 相对作品根，items.path 和 references 相对 outputs；均拒绝绝对路径、越界及符号链接。sceneIds 可为空，不要求全片分镜或 prepare；代码试制应登记实际场景依赖或完整来源文件。工具无法验证未登记的来源，助手必须如实声明。

```json
{"version":3,"round":"trial","purpose":"keyframe","fps":30,"items":[{"id":"window-1","path":"trial.png","window":[0,1],"dynamic":false}],"sources":["scenes/core.tsx"],"sceneIds":[],"displaySizes":[1920,393]}
```

每个 item 指定中性 id、媒体 path、源媒体局部半开帧窗 window、dynamic。动态须完整可解码过程；工具裁出实际窗口并提取有序原生与手机帧，评审据此与帧差/场景切分、主体区域量测和音频信号量测核对。sampleStep 可选，试制默认逐帧、终审默认半秒，并保留首尾；根据关键动作加密，稀疏序列不足时补证。静态图片派生多尺寸，声音按实际覆盖记录。

conditions 列出中性原条件，不填写设计理由、标准答案、推荐、制作成本或完整设计。references 列出实际参考媒体路径，conditions 对应说明整体品质、专项表现、信息表达或备选/历史比较用途，不把整体目标缩成特征清单。提供非空 references 时必须同时提供非空 conditions，缺失则在创建包前拒绝；旧请求须补条件后重建，不改写历史。条件可以只核对事实，无目标媒体不代表验证了风格。文件相对 outputs，可为画面或完整片段；目标按对象、窗口和显示条件描述，不写“应当高级”等抽象评价。

`dynamic`标识编码视频媒体，不自动承诺运动。静止编码仅验证静态表现与一致性，不据此宣称动态或全片基线；动态目标的代表性仍须完整过程的有序帧、帧差/场景切分与信号量测，未提供的运动、停留时间、声音与正文保持未验证。

purpose 为 keyframe/process/final，round 分别为 trial/trial/final。keyframe 只接受图片；process 只接受视频。reviewType 为 blind/consistency/process，process 为直接过程对照，必须有实际 references 与 conditions，不填 blindId；过程例外 blind/consistency 须登记非空 blindReason。

每份报告顶层和 coverage 项均须 adoption=adopt/reject，只有 pass 对应 adopt，fail/insufficient 对应 reject；整体 verdict 必须与覆盖项最严重状态一致。

目标和条件在盲包外绑定，盲看不展示。盲看导入后以相同请求增加 reviewType=consistency、blindId=<原报告ID> 建立同轮对照，包内生成 conditions.json 并附净化后的实际目标媒体（若有），提示核对兑现及具体差距。对照与盲看来源、窗口、评审者及职责须一致。机器只核对已声明的输入与记录，无法发现未登记参考或自动判断研究深度、审美及阶段完成；助手不能省略应提供的目标。

目标媒体及采用条件在盲看请求中预先登记，隔离只是不向盲看者展示。盲看后才新增或修改目标会改变绑定，须重建该范围的盲看与对照；不能给原本无参考的旧盲报告直接追加目标来补出风格通过。

终审请求须为单个当前完整候选、[0,全片帧数]、实际 fps，且当前候选和 qa.json 的视频摘要、准备指纹有效；仅使用文件名或旧 QA 不足。

报告必填 version、round、reviewType、packPath、packSha256、reviewerId、isolation、focus、verdict、adoption、observations、coverage、invocation；consistency 对照另含 blindId，blind/process 不得含 blindId。packPath 是相对 outputs 的 manifest.json；invocation 为真实调用记录的 path/sha256。focus 为 comprehensive 或已声明的 structure/visual-copy；isolation 为 independent-subagent/self-review/external-review。

coverage 每项为 id、window、status、adoption、observations、limitations、assessment；assessment 含 understanding、presentation、representativeness，每项为 status 与 observations。状态 pass/fail/insufficient；代表性和表现须具体观察。工具只验证记录完整性，不自动评判审美。

## 用户明确变更目标

已经绑定独立失败的目标不得由助手自行改写以规避问题。用户明确允许换基准或改变采用目标时，继续当前周期，先按新目标建立完整盲包或直接过程对照包，再用 `review retarget --file` 登记用户原话、要替代目标的失败报告ID及该新包的manifest摘要：

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

`packSha256`填写实际摘要。一次登记只选择同轮同职责的开放独立必改失败；新包须为对应用途的当前有效盲包或直接过程对照包，且带实际参考和中性条件。登记阶段（包括final）严格保持用途、帧率、审核方式、来源、场景、观察项身份、窗口覆盖和显示尺寸，只替换参考与中性条件。登记后的全片复查仍遵守当前完整候选规则，允许剪短或重排，不把登记当作改写旧问题范围。

登记写入摘要绑定的历史收据，旧scope、失败结论和周期不改变，也不自动关闭问题。新独立观察必须在登记后实际开始，导入及同轮对照也须晚于登记；新目标按对应用途独立通过后才按正常issues update关闭所列问题。未列问题仍按原目标；多次用户换目标采用该问题最新的有效登记。损坏记录使相关关闭失效；登记不能用来借用旧通过或重开周期。工具校验声明与证据，无法认证自然语言用户身份，操作者必须先依据真实对话核实授权，不得伪造用户原话。

## 完整媒体相同的 trial 视觉复用

`review reuse --file` 可将原同轮独立双通过显式绑定到当前有效盲包；不执行新观察、不复制或改写报告。请求为：

```json
{"version":1,"blindId":"原盲报告ID","comparisonId":"原对照报告ID","packPath":"review-pack/当前包ID/manifest.json","packSha256":"当前manifest实际摘要"}
```

只允许同周期 trial。完整源媒体文件（含容器和适用音轨）字节摘要、所有窗口、帧率、显示尺寸、职责、参考与条件必须相同；不同编码、容器或近似画面不视为等价。当前来源、采集和包必须有效；旧来源内容可以变化，但原封存请求、来源摘要记录、包、全部证据、报告、调用及账本身份仍须完整。收据不恢复旧技术绑定。新动画、目标或显示条件必须重新观察，final 仍由合格新代理实际终审。

相同媒体存在未解决独立失败时拒绝挑选旧 pass；相关失败须经晚于失败的新代理实质争议复查合法关闭，或有效用户目标变更及新复查关闭。关闭失效则重新阻断。问题关闭仍按原报告导入和调用时间核验，收据时间不能让失败前的观察关闭后续 fail 或 retarget。收据绑定当前采集及原报告，损坏或过期时投影失效，历史保持不变。

## 问题状态与记录

唯一问题块 m2v-issues-v3 包含 version=3、cycleId、items。每项 id、cycleId、status（open/closed）、required、round（trial/final/internal）、scope、reportId（内部问题为 null）、versionRefs、cause、observations；可选 closureReportId、evidence。cause 为 implementation/design/mixed/undetermined，未定位不能关闭。

带闭环校验的问题加载在单次只读查询内复用已完整核验的报告、包与账本；已有外层只读查询时沿用它，独立读取返回后不把缓存带入后续写入。循环复用仍须拒绝，来源或证据变化在下一次独立查询重新核验，样品发布前的来源直读保留；缓存不替代关闭条件或新增失败检查。

独立失败自动登记必改。关闭须绑定晚于原失败、当前、同用途同范围同类独立通过及适用同轮对照，保留原中性条件、目标媒体、职责、显示尺寸与历史（用户明确变更目标须按上节登记替代，原记录仍保留）；关键帧采用盲审及同轮对照，直接过程失败由对应过程独立通过关闭；局部复查覆盖原窗口，全片问题由当前完整候选终审复查，剪短或重排无需保留旧全片时长；自审或跨周期报告不得关闭。内部问题关闭须有效实际复查证据。status 只读展示证据，不推断创作阶段；基线保护活动引用，损坏或未知引用拒绝清理。

同一试制请求包含多个原生片段时，可用新采集的视频复查。每段须与登记的原生采集一一对应并覆盖完整帧窗，前后保持观察项身份、场景入口、参数、画幅和帧率一致。独立报告仍绑定实际采集凭据与媒体摘要。

评审请求引用原生采集凭据时，普通成片清理保留该凭据绑定的所有采集产物，包括没有单列为观察项的静帧。

## 自动任务与同轮对照

包生成后，production/<周期>/review-tasks/<包ID>/ 自动生成 task.md、report-template.json、invocation-template.json。模板位于隔离包外，不参与封存证据，不填真实身份、时间或观察。默认 insufficient/reject；使用者复制填写，不修改原包。

```powershell
uv run m2v review compare --project <作品> --blind-id <当前盲报告ID>
uv run m2v sample review --project <作品> --id <采集ID> --purpose keyframe --targets <目标.json>
uv run m2v sample review --project <作品> --id <采集ID> --purpose process --targets <过程目标.json>
```

compare 只从有效当前盲报告的封存请求派生，不接受另填目标。sample review 从当前采集自动生成完整来源、窗口和显示尺寸；targets 只含 references 和 conditions。过程需要盲审时额外指定 --blind-reason <具体时间机制风险>。这些命令生成材料，不自动启动代理、填写调用或判断审美。

同轮对照严格保持帧率、显示尺寸和 sampleStep，独立复制已核验盲包的净化媒体并逐文件直读核对封存摘要，不重复编码或取帧。不得使用硬链接共享可写文件。终审必须登记实际视觉参考及中性条件，只有音频不能充当视觉品质标杆。

调用记录仅含 id、reviewerId、freshContext、startedAt、completedAt、inputPaths、readReportIds。时间有时区，实际开始不得早于包创建；终审及失败复查另遵守资格和时序。inputPaths 只列实际读取的包内登记文件或 manifest.json；盲审及直接过程对照的 readReportIds=[]，consistency 只列自身同轮 blindId。freshContext 表示代理最初创建时隔离，同一代理继续该轮对照时仍为 true。报告的 invocation 绑定真实记录的相对 outputs 路径与实际摘要，空白模板不是真实执行。用途、视觉目标标记和报告 ID 由工具绑定／导入后派生，不手填到提交报告。

## 隔离包格式

<!-- generated:review-manifest:start -->
```json
{
  "version": 3,
  "reviewId": "R01",
  "cycleId": "example-cycle",
  "createdAt": "2026-11-07T00:00:00+00:00",
  "round": "trial",
  "purpose": "keyframe",
  "fps": 30,
  "items": [
    {
      "id": "window-1",
      "path": "evidence-0000.png",
      "window": [
        0,
        1
      ],
      "dynamic": false,
      "sequence": []
    }
  ],
  "files": [
    {
      "path": "evidence-0000.png",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
    }
  ],
  "displaySizes": [
    1920,
    393
  ],
  "reviewType": "blind",
  "blindId": null,
  "requiresComparison": false
}
```
<!-- generated:review-manifest:end -->
