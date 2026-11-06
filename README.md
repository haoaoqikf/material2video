# Material2Video（材料成片）

Material2Video 是离线短视频制作工具链。五类视频共用 `project.json` v2、分镜 v9、代码场景准备、短预演、单一 `SceneFilm` composition 和制作证据流程。画面可由代码生成，也可使用登记过的真实媒体。架构边界见 [ARCHITECTURE.md](ARCHITECTURE.md)，操作流程见 [material2video Skill](.agents/skills/material2video/SKILL.md)。

## 当前视频类型

<!-- generated:type-catalog:start -->
- `text-motion`：代码生成文字和图形，侧重排版与动效
- `data-evolution`：结构化数据的可视化变化
- `principle-metaphor`：程序生成物体和场景，说明抽象原理
- `spatial-3d`：三维模型和场景的空间渲染
- `documentary-edit`：真实视频、照片与档案的叙事剪辑
<!-- generated:type-catalog:end -->

地图轨迹与情境叙事是可选表现手法，不是独立类型。没有 `general`、专项类型、类别层或风格注册表。作品统一放在 `videos/<类型>/<作品名>/`；随附示例放在 [`examples/`](examples/README.md)。

## 安装与快速开始

```powershell
uv sync
pnpm -C web install
uv run python fonts/fetch.py
pnpm -C web build
uv run playwright install chromium
uv run m2v types
uv run m2v init --type text-motion --project demo
uv run m2v validate --project videos/text-motion/demo
uv run m2v prepare --project videos/text-motion/demo
uv run m2v preview --project videos/text-motion/demo --limit-frames 30
```

`init` 生成可准备的三秒主题示例；正式创作时改写分镜和 `scenes/opening.tsx`。五类使用同一命令：`validate`、`prepare`、`preview`、`lookdev`、`render`、`qa`、`status`、`review` 与制作门命令。`preview` 只检查片段；最终成片与审核按[制作检查点](.agents/skills/material2video/references/checkpoint-gates.md)执行。`render --jobs N` 可按帧区间并行。作品可通过 `--content-root` 或 `M2V_CONTENT_ROOT` 放在仓库外。

## 命令

运行 `uv run m2v --help` 查看入口与参数。类型目录通过 `m2v types` 查询；制作辅助操作使用 `m2v author`，金融来源计划使用 `m2v data financial-plan`。旧命令不保留别名。

## 材料与画面

`project.json` 只接受以下结构；`output` 可声明宽高、30/60 fps、声音和字幕配置：

```json
{"schemaVersion":2,"id":"demo","type":"data-evolution","materials":{"storyboard":"storyboard.json"},"output":{"width":1920,"height":1080,"fps":30,"audio":"optional"}}
```

分镜必须同时声明 `version: 9` 和 `schemaVersion: 9`。每幕使用 `template: "code"`，通过 `content.entry` 指向作品内 TSX，代码从 `m2v/code-scene` 导入共享绘制与逐帧 API。完整字段见[分镜契约](.agents/skills/material2video/references/storyboard-schema.md)和[代码场景运行时](.agents/skills/material2video/references/code-scene-runtime.md)。原文、主题、字幕、媒体、声音、事件、纯时间采集及制作证据都沿用统一链路。

数据演化可以引用 `financial-series` 来源；三维空间可以引用 `construction` 或 `vehicle-model` 来源。分镜顶层 `sources` 把来源 ID 绑定到作品内的请求、行情、构件、模型与资产文件；幕内 `content.sourceIds` 显式选择本幕使用的来源。准备阶段验证材料、素材摘要、画幅、帧率、时长，并把来源及计算实现纳入准备指纹。画面代码从 `m2v/code-scene/sources` 引入 `FinancialSeriesScene`、`ConstructionScene`、`VehicleScene`，也可用 SDK 的 `useSceneSource(id)` 自行绘制。金融计划通过 `m2v data financial-plan --project <作品目录> [--duration-seconds N]` 生成，要求分镜恰好声明一个金融来源。

创作辅助命令改为 `m2v author`：源文审查、候选稿、素材导入和音效操作分别见 `m2v author --help` 与[媒体和声音契约](.agents/skills/material2video/references/article-media-and-sound.md)。外部画面素材使用 `assets/media-sources.json` 留证；`m2v assets report`、`contact-sheet`、`audit` 用于台账和技术检查。字体二进制按 [`fonts/registry.json`](fonts/registry.json) 恢复并校验，不纳入 Git。

旧类型名、`project.style`、project v1、分镜 v8 及旧准备记录明确拒绝。升级后的材料需重新编排并重新准备；没有兼容入口或迁移命令。

## 示例与文档

七部示例按五类分组，清单和恢复命令见 [examples/README.md](examples/README.md)。画面专属组件放在各示例 `scenes/`；跨作品可复用的计数、图表和轨道能力在共享代码场景 SDK。示例媒体按各自 `assets/recipe.json` 恢复；生成媒体与 `outputs/` 不入库。

- [项目规划](docs/PROJECT_PLAN.md)：未来路线与未实现能力。
- [制作 Skill](.agents/skills/material2video/SKILL.md)：阶段入口、材料、画面、声音与评审规则。
- [架构说明](ARCHITECTURE.md)：代码分层与依赖方向。
- [OpenSpec 规格](openspec/specs/)：已实现行为。
- [项目协作约定](AGENTS.md)：验证、提交与资产管理。

日常验证只跑受影响的测试与真实媒体节点；正式全量回归仅在用户明确要求或人工发布验证时执行。文档投影可用 `uv run python .agents/skills/material2video/scripts/sync_docs.py --check` 检查。
