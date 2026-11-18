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

start 显式建立 version=4 新周期，归档旧问题正文并保留旧报告。旧通过不能授权新版，未解决历史必改承接到当前周期。历史整片问题需要当前整片复核及针对原缺陷的实际修复证据。历史关键帧或样片的独立必改仍须同范围独立复查。旧机器合同和旧请求/报告明确不兼容。DESIGN.md 是人读制作依据，不参与机器合同解析。

## 媒体与报告格式

请求 version=4 必填 round、purpose、fps、items、sources、sceneIds、displaySizes。sources 相对作品根，items.path 和 references 相对 outputs；均拒绝绝对路径、越界及符号链接。sceneIds 可为空，不要求全片分镜或 prepare；代码试制应登记实际场景依赖或完整来源文件。工具无法验证未登记的来源，助手必须如实声明。

```json
{"version":4,"round":"trial","purpose":"keyframe","fps":30,"items":[{"id":"window-1","path":"trial.png","window":[0,1],"dynamic":false}],"sources":["scenes/core.tsx"],"sceneIds":[],"displaySizes":[1920,393]}
```

每个 item 指定中性 id、媒体 path、源媒体局部半开帧窗 window、dynamic。动态须完整可解码过程；工具裁出实际窗口并提取有序原生与手机帧，评审据此与帧差/场景切分、主体区域量测和音频信号量测核对。sampleStep 可选，默认逐帧，并保留首尾；根据关键动作加密，稀疏序列不足时补证。静态图片派生多尺寸，声音按实际覆盖记录。

conditions 列出中性原条件，不填写设计理由、标准答案、推荐、制作成本或完整设计。references 列出实际参考媒体路径，conditions 对应说明整体品质、专项表现、信息表达或备选/历史比较用途，不把整体目标缩成特征清单。提供非空 references 时必须同时提供非空 conditions，缺失则在创建包前拒绝；旧请求须补条件后重建，不改写历史。条件可以只核对事实，无目标媒体不代表验证了风格。文件相对 outputs，可为画面或完整片段；目标按对象、窗口和显示条件描述，不写“应当高级”等抽象评价。

`dynamic`标识编码视频媒体，不自动承诺运动。静止编码仅验证静态表现与一致性，不据此宣称动态或全片基线；动态目标的代表性仍须完整过程的有序帧、帧差/场景切分与信号量测，未提供的运动、停留时间、声音与正文保持未验证。

purpose 为 keyframe 或 process，round 为 trial。原生试制样品仅有关键帧评审。正式取证见下节。reviewType 为 blind/consistency/process，process 为直接过程对照，必须有实际 references 与 conditions，不填 blindId。正式过程例外 blind/consistency 须登记非空 blindReason。

每份报告顶层和 coverage 项均须 adoption=adopt/reject，只有 pass 对应 adopt，fail/insufficient 对应 reject；整体 verdict 必须与覆盖项最严重状态一致。

目标和条件在盲包外绑定，盲看不展示。盲看导入后以相同请求增加 reviewType=consistency、blindId=<原报告ID> 建立同轮对照，包内生成 conditions.json 并附净化后的实际目标媒体（若有），提示核对兑现及具体差距。对照与盲看来源、窗口、评审者及职责须一致。机器只核对已声明的输入与记录，无法发现未登记参考或自动判断研究深度、审美及阶段完成；助手不能省略应提供的目标。

目标媒体及采用条件在盲看请求中预先登记，隔离只是不向盲看者展示。盲看后才新增或修改目标会改变绑定，须重建该范围的盲看与对照；不能给原本无参考的旧盲报告直接追加目标来补出风格通过。

报告必填 version、round、reviewType、packPath、packSha256、reviewerId、isolation、focus、verdict、adoption、observations、coverage、invocation；consistency 对照另含 blindId，blind/process 不得含 blindId。packPath 是相对 outputs 的 manifest.json；invocation 为真实调用记录的 path/sha256。focus 为 comprehensive；isolation 为 independent-subagent/self-review/external-review。

调用记录的 `inputPaths` 同样以 `outputs/` 为基准，例如 `review-pack/<包ID>/evidence-0000-1920.png`（使用实际清单文件名）。`reviewerId` 使用真实身份的标签，只含英文字母、数字、下划线或连字符，最长 96 字符；例如将代理路径 `/root/reviewer` 记作 `root-reviewer`，同轮保持一致。修正路径或标签格式时保留原稿和修正原因，不改观察结论或调用时间。

coverage 每项为 id、window、status、adoption、observations、limitations、assessment；assessment 含 understanding、presentation、representativeness，每项为 status 与 observations。状态 pass/fail/insufficient；代表性和表现须具体观察。工具只验证记录完整性，不自动评判审美。

## 正式窗口与整片复核

优先使用当前合成预演或完整候选，保留其视频和原始同名溯源旁车。按设计问题登记绝对成片半开帧窗。登记中的目标原样加入对应过程包的 conditions。复查多个窗口时可分别送审。

```powershell
uv run m2v review scope --project <作品> --file <必审窗口.json>
uv run m2v review pack --project <作品> --file <正式评审请求.json>
uv run m2v review confirm-evidence --project <作品> --file <整片复核.json>
```

必审窗口文件形如：

```json
{"windows":[{"id":"reveal","window":[210,330],"goal":"变化呈现完整因果及真实字幕阅读窗口"}]}
```

正式请求加 film=true。path 指向 outputs 内已有合成视频，window 仍是源视频的局部半开帧窗。关键帧填写恰好一帧、dynamic=false，隔离包实际只含图像；关键样片填 dynamic=true，包内保留窗口画面与适用的音轨。工具根据旁车显示 filmWindow 成片绝对帧窗，关键样片状态按同 ID、同绝对范围与对应目标匹配。窗口示例来自 startFrame=210 的预演视频：

```json
{"version":4,"round":"trial","purpose":"process","reviewType":"process","film":true,"fps":30,"items":[{"id":"reveal","path":"previews/video.mp4","window":[0,120],"dynamic":true}],"references":["refs/quality.mp4"],"conditions":["变化呈现完整因果及真实字幕阅读窗口"],"sources":[],"sceneIds":[],"displaySizes":[1920,393]}
```

固定路径的预演按摘要封存，完整候选复用已有持久路径。以 `video.mp4` 取证时校验其与候选的字节摘要及溯源映射，允许技术 QA 在交付旁车补写独立的 `qa` 注记。后续按实际窗口的场景依赖、合成字幕和适用母版音频重验。同批中的窗口按各自来源区分有效范围，正式独立失败只把实际失败的项登记为必改。原生试制与正式窗口可以在同一周期记录，完成状态只统计正式合成证据。有字幕时正式关键帧与适用关键样片均须覆盖实际字幕。

总代理完成当前候选的抽帧、时间轴、适用信号核查及技术 QA 后，提交 `candidateSha256`、整片 `observations` 和 `windows`。至少登记一个实际核查过的帧窗，帧号为成片绝对半开区间；每窗填写具体帧、信号或时序证据及结论，整片结论说明覆盖和限制。以下数值与摘要仅作结构示意：

```json
{"candidateSha256":"<当前候选SHA-256>","observations":"核对全片各场代表帧、跨场边界及字幕时序；声音结论限于信号量测","windows":[{"window":[88,96],"observations":"核对切镜两侧及中段有序帧，字幕未跨入下一场"}]}
```

确认写入现有账本，由 `status` 的 `wholeFilmReview` 显示。候选、准备身份或 QA 变化后，确认失效。旧 `confirm-playback` 不再接受，历史记录保留；仍有效的旧候选可复用媒体和 QA 补登记，不必重渲染。

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

`packSha256`填写实际摘要。一次登记只选择同轮同职责的开放独立必改失败；新包须为对应用途的当前有效盲包或直接过程对照包，且带实际参考和中性条件。登记阶段严格保持用途、帧率、审核方式、来源、场景、观察项身份、窗口覆盖和显示尺寸，只替换参考与中性条件。

登记写入摘要绑定的历史收据，旧scope、失败结论和周期不改变，也不自动关闭问题。新独立观察必须在登记后实际开始，导入及同轮对照也须晚于登记；新目标按对应用途独立通过后才按正常issues update关闭所列问题。未列问题仍按原目标；多次用户换目标采用该问题最新的有效登记。损坏记录使相关关闭失效；登记不能用来借用旧通过或重开周期。工具校验声明与证据，无法认证自然语言用户身份，操作者必须先依据真实对话核实授权，不得伪造用户原话。

## 完整媒体相同的 trial 视觉复用

`review reuse --file` 可将原同轮独立双通过显式绑定到当前有效盲包；不执行新观察、不复制或改写报告。请求为：

```json
{"version":1,"blindId":"原盲报告ID","comparisonId":"原对照报告ID","packPath":"review-pack/当前包ID/manifest.json","packSha256":"当前manifest实际摘要"}
```

只允许同周期 trial。完整源媒体文件（含容器和适用音轨）字节摘要、所有窗口、帧率、显示尺寸、职责、参考与条件必须相同；不同编码、容器或近似画面不视为等价。当前来源、采集和包必须有效；旧来源内容可以变化，但原封存请求、来源摘要记录、包、全部证据、报告、调用及账本身份仍须完整。收据不恢复旧技术绑定。新动画、目标或显示条件必须重新观察。

相同媒体存在未解决独立失败时拒绝挑选旧 pass；相关失败须经晚于失败的新代理实质争议复查合法关闭，或有效用户目标变更及新复查关闭。关闭失效则重新阻断。问题关闭仍按原报告导入和调用时间核验，收据时间不能让失败前的观察关闭后续 fail 或 retarget。收据绑定当前采集及原报告，损坏或过期时投影失效，历史保持不变。

## 问题状态与记录

唯一问题块 m2v-issues-v4 包含 version=4、cycleId、items。每项 id、cycleId、status（open/closed）、required、round（trial/internal）、scope、reportId（内部问题为 null）、versionRefs、cause、observations；可选 closureReportId、evidence。cause 为 implementation/design/mixed/undetermined，未定位不能关闭。

带闭环校验的问题加载在单次只读查询内复用已完整核验的报告、包与账本；已有外层只读查询时沿用它，独立读取返回后不把缓存带入后续写入。循环复用仍须拒绝，来源或证据变化在下一次独立查询重新核验，样品发布前的来源直读保留；缓存不替代关闭条件或新增失败检查。

独立失败自动登记必改。关闭须绑定晚于原失败、当前、同用途同范围的独立通过。关键帧另须同轮对照，正式过程按其适用评审复查。保留原中性条件、目标媒体、职责、显示尺寸与历史。用户明确变更目标时按上节登记替代。历史原生试制过程报告保留在原记录中，从当前适用问题投影排除。自审或跨周期报告不得关闭独立失败。内部问题关闭须有效实际复查证据。status 只读展示证据，基线保护活动引用，损坏或未知引用拒绝清理。

同一试制请求包含多个原生片段时，可用新采集的视频复查。每段须与登记的原生采集一一对应并覆盖完整帧窗，前后保持观察项身份、场景入口、参数、画幅和帧率一致。独立报告仍绑定实际采集凭据与媒体摘要。

评审请求引用原生采集凭据时，普通成片清理保留该凭据绑定的所有采集产物，包括没有单列为观察项的静帧。

## 自动任务与同轮对照

包生成后，production/<周期>/review-tasks/<包ID>/ 自动生成 task.md、report-template.json、invocation-template.json。模板位于隔离包外，不参与封存证据，不填真实身份、时间或观察。默认 insufficient/reject；使用者复制填写，不修改原包。

```powershell
uv run m2v review compare --project <作品> --blind-id <当前盲报告ID>
uv run m2v sample review --project <作品> --id <采集ID> --purpose keyframe --targets <目标.json>
```

compare 从有效当前盲报告的封存请求派生。sample review 从当前采集自动生成关键帧来源、窗口和显示尺寸，targets 只含 references 和 conditions。正式过程确需盲审时在请求中登记 blindReason。真实观察和调用由独立评审者完成。

同轮对照严格保持帧率、显示尺寸和 sampleStep，独立复制已核验盲包的净化媒体并逐文件直读核对封存摘要，不重复编码或取帧。不得使用硬链接共享可写文件。正式独立评审须登记实际视觉参考及中性条件，只有音频不能充当视觉品质标杆。

调用记录仅含 id、reviewerId、freshContext、startedAt、completedAt、inputPaths、readReportIds。时间有时区，实际开始不得早于包创建；失败复查另遵守时序。inputPaths 只列实际读取的包内登记文件或 manifest.json；盲审及直接过程对照的 readReportIds=[]，consistency 只列自身同轮 blindId。freshContext 表示代理最初创建时隔离，同一代理继续该轮对照时仍为 true。报告的 invocation 绑定真实记录的相对 outputs 路径与实际摘要，空白模板不是真实执行。用途、视觉目标标记和报告 ID 由工具绑定／导入后派生，不手填到提交报告。

## 隔离包格式

<!-- generated:review-manifest:start -->
```json
{
  "version": 4,
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
