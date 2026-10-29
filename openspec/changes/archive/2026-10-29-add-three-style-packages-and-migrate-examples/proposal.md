## Why

仓库现有 `vibe-night`、`vibe-fable` 两个正式风格包，另有 `american-science-milestones`、`compound-interest`、`solar-system-journey` 三个固定示例。三个示例已经各自形成稳定、可辨识的视觉系统，但可复用部分仍与题材内容混在 `examples/` 里：其他作品无法选择这些外观，制作时只能手工复刻；同时顶层 `examples/` 与 `styles/examples/` 两套示例位置并存，路径、测试与文档口径分裂。

用户明确要求：把三个示例整理成三个正式风格包，取消顶层三个固定示例，把作品集中到对应风格之下；保留原有 `vibe-night`、`vibe-fable`，最终共 5 个风格；并明确区分通用能力、风格能力与视频专属能力。本变更是仓库结构与能力边界的重构，按约定必须走 OpenSpec。

## What Changes

- 新增三个正式风格包：
  - `styles/doc-archive/`（档案纪录片，源自 `american-science-milestones`）
  - `styles/count-ledger/`（可数物证/状态机，源自 `compound-interest`）
  - `styles/deep-journey/`（深空连续旅程，源自 `solar-system-journey`）
- 三个作品从顶层 `examples/<slug>/` 迁入 `styles/examples/<style-id>/<slug>/`，并在 `project.json` 声明对应 `style.id`；题材内容、分镜、素材、数学、旁白与声音全部留在示例作品，不进入风格包。
- **BREAKING** 删除顶层 `examples/` 及其“最多三个固定示例”的集合规则；仓库不再分发该三例的旧路径。风格示例统一位于 `styles/examples/<style-id>/<slug>/`，共 5 个（新增 3 个 + 现有 `vibe-night/fold`、`vibe-fable/pigeon`）。
- 更新风格注册与工作区契约：`m2v styles` 返回 5 个包；`styles/examples/` 继续作为保留目录，不参与风格发现；仓库根识别 `styles/examples/<style-id>/<slug>/`，不再识别 `examples/<slug>/`。
- 三个新包不登记 `assets`：使用宿主已注册字体，程序化材质与图形；不新增字体恢复步骤，也不携带题材素材。
- 同步更新测试、`.gitignore`、README、AGENTS、ARCHITECTURE、`styles/README.md`、skill 参考与 OpenSpec 主规格。
- 不新增视频类型、CLI 命令、分镜字段、制作门或审核轮次；不改变 `style.json` 结构、渲染契约与导出门禁；不保留旧 `examples/` 兼容入口或双路径回退。

## Capabilities

### New Capabilities

- `doc-archive-style`：档案纪录片风格包的注册内容、色板与版式、档案媒体框与信息叠加组件，以及其规范示例作品的视频专属内容契约。
- `count-ledger-style`：可数物证/状态机风格包的注册内容、三态色语义、可数对象与相机组件，以及其规范示例作品的视频专属内容契约。
- `deep-journey-style`：深空连续旅程风格包的注册内容、深空色板与 HUD 版式、3D 舞台与连续相机组件，以及其规范示例作品的视频专属内容契约。

### Modified Capabilities

- `style-registry`：登记从 2 个正式风格包扩展为 5 个；`styles/examples/` 保留目录与旁白约束说明同步。
- `vibe-fable-style`：风格示例不再占用顶层 `examples/` 名额；注册场景从 2 个包改为 5 个包。
- `article-explainer`：删除“仅分发三个固定示例”的通用要求，改为“随附风格示例集合”；三个作品的题材内容要求以 `REMOVED` + Reason/Migration 迁入各新风格规格。
- `article-workspace`：示例作品路径从 `examples/<slug>/` 改为 `styles/examples/<style-id>/<slug>/`，产物仍写作品自身 `outputs/`。
- `modular-video-production`：仓库自带示例走统一入口时的路径与产物位置同步。
- `example-media-recovery`：示例媒体恢复范围与忽略规则改为 `styles/examples/<style-id>/<slug>/assets/`。
- `video-frame-rate`：固定示例场景改为 5 个随附示例，按各自显式帧率交付；修正“三个示例均 60fps”与 `count-ledger` 30fps 的既有矛盾。
- `video-production-workflow`：固定示例措辞改为随附示例作品，保留“补写内容只作后续指导、不改写既有验收结论”。

## Impact

- 新增 `styles/doc-archive/`、`styles/count-ledger/`、`styles/deep-journey/` 与 `styles/examples/` 下三个作品目录；删除顶层 `examples/`。
- 修改 `src/m2v/commands.py` 的作品路径守卫、`src/m2v/core/workspace.py` 的注释与工作区契约；`src/m2v/core/styles.py` 的发现逻辑保持不变。
- 修改 `.gitignore`、`tests/example_catalog.py`、`tests/test_examples_strict.py` 及 14 个引用示例的测试；新增 3 个风格包测试。
- 修改 README、AGENTS、ARCHITECTURE、`styles/README.md`、`.agents/skills/material2video/references/` 中受影响的路径与说明。
- 三个旧示例的 `outputs/` 合计约 17.4G 且存在权限受限目录；只迁移 tracked 文件，不整目录移动，旧产物本地清理。
- 不新增视频类型、命令或材料字段；不改变共享字幕层、制作门、审核职责与导出门禁。
