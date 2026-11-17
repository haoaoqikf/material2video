## Why

当前整片复核要求实际播放、从头观看和试听，这不是助手可以可靠完成并如实登记的检查。改用真实候选的抽帧和信号证据，让结论与实际核验能力一致。

## What Changes

- 取消研究、制作、评审和交付中的视频播放观看与实际试听要求。保留参考静帧、抽帧、按时间排列的帧、完整解码及信号量测；不把这些证据写成实时观感或听感。
- 保留正式关键帧、适用关键样片的独立评审、当前技术 QA、整片证据复核和必改闭环。按实际证据覆盖及适用风险判断，不因没播放或没试听而阻断。
- **BREAKING**：以 `review confirm-evidence` 和状态的 `wholeFilmReview` 代替旧看听登记与状态字段；旧账本原样保留，旧看听收据不作为新证据确认。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `video-production-workflow`：研究、试制与短片检查采用帧和信号证据。
- `reference-style-transfer`：参考分析按已有图像、帧和来源证据拆解。
- `independent-subagent-review`：主制作代理与独立评审都按证据核查。
- `media-bound-production-review`：整片复核改为候选证据复核。
- `production-status-ledger`：登记、投影并校验整片证据复核。
- `single-pass-delivery`：整片复核使用当前正式候选的抽帧及适用信号。
- `scene-design-documents`：动态字幕复查基于有序帧、时间轴和信号。
- `compound-interest-explainer-video`、`solar-system-journey-video`：示例采用同一证据政策。

## Impact

影响制作 Skill、README、示例和模板提示、制作账本及 CLI 测试。保留预览、播放器、自动解码和媒体采集能力，以及既有独立评审格式、职责与通过条件。无新依赖。
