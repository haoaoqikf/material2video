## Why

字幕时长完全跟随实际 TTS 语速，项目此前**没有任何阅读速度上限**——语速偏快时，
字幕在观众读完之前就切走了，而制作流程对此毫无提示。调研中确认 Netflix
《Chinese Simplified Timed Text Style Guide》给出成人节目 **≤9 字/秒** 的明确上限，
是目前可引用的最直接出处。

直接加阻断门禁会改变行为，且可能让现有作品无法通过；因此本轮只做**报告**。

## What Changes

- 准备阶段逐条量算字幕字数与字/秒，写入 `outputs/reading-pace.json`，
  绑定当前准备指纹。
- 超过 9 字/秒的条目单独列一份，`m2v prepare` 在 stderr 打印一行 `[warning]` 提示。
- **不阻断**：准备、完整预演与导出一律照常进行。
- 字数为标点与空白之外的字数，复用既有的 `count_characters`，不另立口径。
- 产物清单同步：补上该报告，并清掉清单里一个无人写入的过期条目
  （`subtitle-check-props.json`）。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `article-explainer`：新增字幕阅读速度的量算与报告要求，明确只报告不阻断。

## Impact

准备阶段、CLI 的 `prepare` 分支、新增 `m2v/types/general/reading_pace.py`、
制作参考文档的产物清单。报告不进准备产物与预演契约，因此不影响 `preparedFingerprint`、
不参与验收，也不会被渲染后清理删除。
