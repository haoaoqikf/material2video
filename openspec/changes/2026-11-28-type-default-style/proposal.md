## Why

作品的视觉方向与审核基准目前依赖逐次选案。为三类作品各指定一组可核验的公开参考，能让创作者与独立评审者对照同一目标，也能保留按题材调整的空间。

## What Changes

- 三类各发布一个带修订号的默认参考集，涵盖整体标杆、专项参考与官方规范。数据演化沿用用户指定的 Apple Keynote Presentation Style。各条网址、观察用途及已核验证据见 [research.md](research.md)。
- 初始化将参考清单与摘要固化在作品本地绑定文件。目录更新只影响后续初始化。用户显式覆盖保存原话、时间、来源和有效范围。
- 机器核验绑定、参考可达性或本地快照、摘要、授权、范围、评审目标修订一致性及旧版拒绝。视觉完成度与专项机制由独立盲审和同轮实际对照核验，缺证保持 `insufficient`。
- 沿用 `project.json` v3 和分镜 v9。当前制作入口要求本地参考绑定，既有 v3 作品补齐绑定后可继续校验。三个示例和现役作品逐部复核、取证，按实际差距调整画面。

## Capabilities

### New Capabilities

- `type-default-style` 定义默认参考集、作品固化、显式覆盖和证据门禁。

### Modified Capabilities

- `three-video-types` 为三类入口及固定示例增加默认参考集绑定。
- `reference-style-transfer` 将默认整体标杆、专项参考及官方规范纳入研究和实际对照。
- `independent-subagent-review` 在盲审封存后的同轮对照中按生效参考与实际观看条件核验。
- `keynote-design-system` 明确默认参考集与本地画面取值的职责。
- `standalone-video-projects` 将参考绑定纳入独立工程交付、准备及证据有效性。
- `material-selection-library` 明确正式导入复用作品绑定校验，素材登记维持独立。

## Impact

后续实施涉及类型目录、作品初始化、本地校验与准备、评审包、制作指南、固定示例和可定位的现役作品。参考快照用于保存观察证据，作品本地代码继续负责实际画面。此次修订范围为提案文档。
