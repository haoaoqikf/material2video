# 技术 QA 与独立视觉评审

只保留技术 QA、试制独立评审 trial 与当前完整候选独立终审 final。全片预演、粗片查看、局部复查是内部制作活动，不建立顺序门禁或声明式数量、布局、状态断言。

## 审核策略

每个制作周期至少有一次有代表性的独立试制观察和一次新代理终审。试制须覆盖所有影响当前方向的重要未知；不同片段可分批投喂，不以一个样片授权未覆盖机制。静态作品按实际静态窗口验证，不额外添加动画。

默认一名综合终审；具体观察能力/范围风险要求分工时，review start --split-final --basis <具体依据> 设置结构与视觉文案两名隔离终审。实质争议使用新代理复核；同一问题两轮修复无改善时匿名比较实质不同方案，合并到适用评审活动。

事实、来源、许可和用户硬约束由助手核验并在作品材料保留。技术和材料校验继续执行，评审不阻断候选导出；缺少有效评审不得报告制作完成。降级自审必须披露，不关闭独立项。

成功导出后的普通清理保留当前周期隔离包绑定的源媒体与目标媒体，包括位于 `previews/` 的文件；包内净化副本不能替代源文件摘要绑定。未导入或内容已过期的包仍保护其明确引用，引用记录损坏时停止清理并报告，不影响已生成候选。引用解析与清理共用作品写锁，无引用的旧媒体继续按原规则清理。

## 命令与周期

```powershell
uv run m2v review start --project <作品>
uv run m2v review pack --project <作品> --file <请求.json>
uv run m2v review import --project <作品> --file <报告.json>
uv run m2v review timeline --project <作品>
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

可选 conditions 列出中性原条件，不填写设计理由、标准答案或完整设计。实际目标媒体由 references 列出路径；二者在盲包外绑定，盲看不展示。盲看导入后以相同请求增加 reviewType=consistency、blindId=<原报告ID> 建立同轮对照，包内生成 conditions.json 并附实际目标媒体（若有）。对照与盲看来源、窗口、评审者及职责须一致。

终审请求须为单个当前完整候选、[0,全片帧数]、实际 fps，且当前候选和 qa.json 的视频摘要、准备指纹有效；仅使用文件名或旧 QA 不足。

报告必填 version、round、reviewType、packPath、packSha256、reviewerId、isolation、focus、verdict、observations、coverage、invocation；对照另含 blindId。packPath 是相对 outputs 的 manifest.json；invocation 为真实调用记录的 path/sha256。focus 为 comprehensive 或已声明的 structure/visual-copy；isolation 为 independent-subagent/self-review/external-review。

coverage 每项为 id、window、status、observations、limitations、assessment；assessment 含 understanding、presentation、representativeness，每项为 status 与 observations。状态 pass/fail/insufficient；代表性和表现须具体观察。工具只验证记录完整性，不自动评判审美。

## 问题状态与记录

唯一问题块 m2v-issues-v2 包含 version=2、cycleId、items。每项 id、cycleId、status（open/closed）、required、round（trial/final/internal）、scope、reportId（内部问题为 null）、versionRefs、cause、observations；可选 closureReportId、evidence。cause 为 implementation/design/mixed/undetermined，未定位不能关闭。

独立失败自动登记必改。关闭须绑定晚于原失败、当前、同范围同类独立通过及适用同轮对照，保留原中性条件、目标媒体、职责、显示尺寸与历史；局部复查覆盖原窗口，全片问题由当前完整候选终审复查，剪短或重排无需保留旧全片时长；自审或跨周期报告不得关闭。内部问题关闭须有效实际复查证据。status 只读展示证据，不推断创作阶段；基线保护活动引用，损坏或未知引用拒绝清理。
