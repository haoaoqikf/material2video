## Why

作品目前依赖助手现场选择风格及整体标杆，同类型作品的视觉方向和审核基准难以重复。用户要求由视频类型指定唯一默认风格，只有用户明确给出指令时才可覆盖。

## What Changes

2026-11-28 起，原理隐喻和纪实素材剪辑已由 `2026-11-28-remove-two-video-types` 移除。

- 为三类各指定一个带修订号的视觉规范和固定整体参考。数据演化指定 Apple Keynote Presentation Style，其余两类的候选、原始证据和取舍见 [research.md](research.md)。
- **不兼容变更**。作品清单升级至 v4，必填 `visualStyle`。初始化固化类型默认值。显式覆盖记录用户原话、授权时间、来源和范围。同步升级类型目录与准备记录，继续用 v9 分镜。
- 在现有校验及技术 QA 中检查可量化规则，同时在现有独立盲审、同轮对照和整片复核中验证表达与制作完成度。
- 一次性重编排示例及可定位的现有作品。旧版清理由通过当前交付验证的新版本触发，历史研究、评审原件与问题记录按既有契约保留。

## Capabilities

### New Capabilities

- `type-default-style` 规定默认风格、显式覆盖、风格证据与两道验收门禁。

### Modified Capabilities

- `three-video-types` 增加类型的默认风格职责、v4 作品入口与示例验证。
- `reference-style-transfer` 用固定整体参考取代助手自选及融合风格，保留专项取证和关键目标复查。
- `independent-subagent-review` 将生效风格和整体参考用于已登记的独立目标对照。
- `keynote-design-system` 明确作品风格配置与现有共享令牌的职责，继续禁止属性切换作用域。
- `standalone-video-projects` 更新独立工程 v4、准备绑定与本地检查。
- `material-selection-library` 将既有导入衔接的作品版本更新至 v4，沿用素材格式与采用政策。

## Impact

实施范围包含类型目录、作品初始化与校验、独立模板及示例、技术 QA、评审包和交付状态、制作指南与作品格式文档。作品运行时和所用字体仍随作品恢复。采用现有 CLI 入口，无需引入风格包加载器或远端依赖。实施以用户确认本提案为前提。
