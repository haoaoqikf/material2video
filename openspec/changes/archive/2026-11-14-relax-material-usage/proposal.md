## Why

现行素材政策虽然写明「未发现明确禁止即可采用」，但执行层把平台服务条款当成禁止，并对人像、引用长度、署名和已检查依据设置了较多默认要求，导致社媒截图、引用他人媒体等常见素材在进入制作前就被排除。用户明确要求：素材与使用相关的一切从宽，只要没有明确禁止就能用。

## What Changes

- 采用判定只剩一条阻断：**权利人明确禁止当前用途**。平台服务条款、登录墙、付费墙与反爬限制不算禁止，只记风险。
- 新增来源类型 `social-screenshot`（社媒截图）与 `quoted-media`（引用图文、音视频），并增加可选字段 `platform`、`postUrl`、`postedAt`、`capturedAt`、`risk`、`riskNotes`、`quotedWork`。
- `usage` 默认改为 `no-explicit-restriction`，不再强制 `evidenceUrl`、`checkedAt`、`note`；`conditional` 未满足条件降为警告，只有 `prohibited` 仍阻断。
- 取消「默认避免可辨认人像」的全局要求。
- 引用其他媒体不设时长或比例上限；保留注明出处、不冒充原创、不歪曲原意。
- 画面署名简化为「引自<平台>」小字，可低对比、半透明、位置次要；完整作者、链接、日期与许可保留在台账、`SOURCES.md` 与发布说明。
- 新增总则：素材与使用相关未写明的事项一律从宽解释，不新增限制。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `material-sourcing`：采用政策、台账报告阻断条件、人物默认与署名规则。
- `article-media-assets`：导入字段、来源类型、默认采用状态与审计阻断条件。
- `modular-video-production`：`assets audit` 只在明确禁止等真实错误时失败。

## Impact

影响 `src/m2v/core/media_policy.py`、`src/m2v/engine/assets_tools.py`、素材与媒体参考文档、协作约定与 README；不改变渲染契约、分镜结构、技术 QA 与独立评审门禁。验证覆盖采用政策、台账报告与审计的受影响测试。
