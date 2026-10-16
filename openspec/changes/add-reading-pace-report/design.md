## Context

字幕 cue 由准备阶段从真实词时间戳派生（`engine/subtitles.py`），每条只有
`startFrame`/`endFrame`/`text` 三个字段，时长即帧差除以 30。因此阅读速度可以直接从
准备记录现有字段量算，不需要新的时间戳来源。

难点是**放在哪里**：`prepared.json` 的 `preparedFingerprint` 覆盖整个字典，任何新增字段
都会让既有预演失效；`input-review.json` 有严格的全字段相等校验，不适合塞额外数据。

## Goals / Non-Goals

**Goals**：量出每条字幕的字/秒；超限可见；准备、预演与导出都不受影响。

**Non-Goals**：不做阻断门禁；不改字幕切分与时长；不改分镜字段；不落外置字幕文件。

## Decisions

**落成独立旁车 `outputs/reading-pace.json`。** 照 `layout-check.json` 的模式：自带
`schemaVersion` 与 `preparedFingerprint` 标注它对应哪次准备，但**不进** `inputs`、
不进 prepared 字典——因此不改 `preparedFingerprint`，既有预演继续有效。
渲染后清理不删它（清理只动视频、`.srt`、图片与三种已知旁车）。

**字数复用 `count_characters`。** 该项目已有既定的字数口径（排除 Unicode 标点与空白），
另写一个 `len()` 会让「字数」在项目里有两个意思。

**提示在 CLI，不在准备阶段。** `prepare` 只负责写报告；`cli.py` 的 `prepare` 分支读报告并
往 stderr 打一行 `[warning]`，与旧产物清理失败的报告方式一致。这样报告本身可被
其他入口复用，而「提示什么」留在 CLI。

**模块放在 `types/general/` 而不是 `engine/`。** 它要用 `types/general/article_text.py`
的 `count_characters`，而共享底座不导入类型私有逻辑。

**不进 `implementation_digest`。** 报告不影响准备产物与预演契约；把它纳入摘要会让
「改报告口径」也让已验收的预演失效，代价与收益不成比例。这一取舍写在模块文档串里。

## Risks / Trade-offs

- **阈值取自电视字幕场景**（Netflix 指南面向影视），竖屏短视频的实际阅读条件不同，
  9 字/秒偏保守。因此只报告不阻断——先看清现状有多少条超限，再决定要不要收紧。
- **不阻断意味着可能长期没人看**：缓解办法是 `prepare` 每次都打印一行提示，
  且报告随准备一起刷新。
- 标点不计入字数：`count_characters` 的口径对中文口播是合理的（标点不占阅读时间），
  但它与「屏幕上的字符数」不是一回事，文档里已写明。
