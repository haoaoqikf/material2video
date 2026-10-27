## Why

《美国十大市值公司》短片里，每家公司标题下的「办公场景示意」「特斯拉电动车行驶实拍」等标注在手机横屏（852 宽等效约 18.6px）仍能读清，用户认为存在感过强，要求缩到 20px、颜色更暗，做到手机横屏看不清。现有规范却把「手机尺寸下仍须可读」写成注释的硬性验收条件，与用户要求直接冲突；只改片子会让后续评审按旧规则判为缺陷。

## What Changes

- 示意／实拍边界标注改为**次要边界标记**：仍有存在感、仍须标出真实与示意的边界，但设计目标变为「大屏原尺寸可辨、手机横屏不可辨」，不再要求手机尺寸可读；遮挡、抢焦的底线不变。
- 承载必要信息的注释（口径等）与字幕**仍按手机可读**验收，不随本次放宽；该片的片尾两行素材署名按用户要求与边界标注同档缩小，完整署名、来源与许可保留在 `CREDITS.md`。
- 通用图库素材的边界标注要求同步到 `general-video-composition` 规格：标注必须持续可见、不得冒充实拍事件/公司自有产线/具体型号，但不以手机可读为条件。
- 该片重制：`scenes/common.tsx` 的注释由 42px `#7b858c` 改为 20px `#5f6970`，英伟达幕末两行署名由 60px 改为同档 20px；开场标题由「美国十大市值公司」改为「美国市值最高的十大公司」，分镜、DESIGN 与制作记录同步；市值行 44px、开场副标题 40px 不变。按源码级变更重跑 G4、G5、G6 与核心／粗片／终审三轮独立评审。
- 本变更不新增 CLI、自动门禁或合同字段；注释仍由实际画面复核，不进入 `bodyRoles` 字号量测。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `general-video-composition`：通用图库素材的「示意」边界标注从「小字且手机可读」改为「持续可见的次要边界标记，大屏可辨、手机横屏不要求可辨」，同时保留不冒充、不遮挡、不抢焦的约束。
- `us-top10-market-cap-silent-video`：片尾许可署名从「手机尺寸可读」改为与边界标注同档的次要标记，完整署名与许可保留在作品材料；其余画面文字的可读性要求不变。

## Impact

- 规范文档：`AGENTS.md`、`.agents/skills/material2video/SKILL.md` 及 `references/` 下的 production-workflow、video-revision、visual-review-rubric、visual-material-selection、subagent-review。
- 作品材料（不入库）：`videos/general/us-top10-market-cap/scenes/common.tsx`、`DESIGN.md`、`outputs/visual-notes.md`、门禁与评审证据。
- 三个固定示例的示意标注已是 18–26px，符合新目标，不做改动。
- 不改变渲染契约、分镜结构、素材许可、事实口径与交付格式。
