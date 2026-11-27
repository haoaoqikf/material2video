# 独立工程与分镜

本文件从 README 下沉，权威内容仍以 [`.agents/skills/material2video/references/`](../../.agents/skills/material2video/references/) 为准。具体见[分镜契约](../../.agents/skills/material2video/references/storyboard-schema.md)、[代码场景运行时](../../.agents/skills/material2video/references/code-scene-runtime.md)、[目录约定](../../.agents/skills/material2video/references/paths.md)。

## 工程和运行时

五部随附示例均为独立工程，运行源码、依赖锁、字体与资源恢复、预览、采集和导出都归作品。`lookdev`、时间线与 QA 读取本地产物。主项目提供制作指导、初始化、可选组件参考和制作管理。[`web/`](../../web/README.md) 集中维护现行参考源码与测试夹具。

新建作品使用 `project.json` v3 和分镜 v9，自带运行源码、依赖锁、资源恢复与 `SceneFilm` 合成。主项目通过本地入口委托校验、准备、片段检查与完整导出。画面可由代码生成，也可使用登记的真实媒体。架构边界见[架构说明](../../ARCHITECTURE.md)。

地图轨迹与情境叙事是可选表现手法，不是独立类型。没有 `general`、专项类型、类别层或风格注册表。作品默认生成到 `videos/<类型>/<作品名>/`；随附示例放在 [`examples/`](../../examples/README.md)。

## 材料与画面

以下 `project.json` v3 示例使用 `output` 声明宽高、帧率和声音。帧率可选 30 或 60 fps，`output` 也可声明字幕配置。

```json
{"schemaVersion":3,"id":"demo","type":"data-evolution","materials":{"storyboard":"storyboard.json"},"runtime":{"version":1,"command":["uv","run","--frozen","python","scripts/video.py"]},"output":{"width":1920,"height":1080,"fps":30,"audio":"optional"}}
```

分镜必须同时声明 `version: 9` 和 `schemaVersion: 9`。每幕使用 `template: "code"`，通过 `content.entry` 指向作品内 TSX。新工程从本地 `src/code-scene/context` 导入时间接口，组件和第三方依赖由作品显式采用，不解析 `m2v/*`。分镜字段见[分镜契约](../../.agents/skills/material2video/references/storyboard-schema.md)；存量画面参考见[代码场景运行时](../../.agents/skills/material2video/references/code-scene-runtime.md)。原文、主题、字幕、媒体、声音与事件仍使用分镜 v9。

分镜顶层 `sources` 把来源 ID 绑定到作品内文件，幕内 `content.sourceIds` 选择来源。主项目仍保留 `financial-series`、`construction`、`vehicle-model` 的材料校验与计算辅助；新工程按需携带所采用的准备模块、数据快照及绘制实现，基础模板缺模块时明确报错，不回退主项目SDK。金融计划辅助入口为 `m2v data financial-plan --project <作品目录> [--duration-seconds N]`，要求分镜恰好声明一个金融来源。

五类创作都从统一阶段指南进入。金融行情、构件与车辆专项指南按实际绑定的来源展开。固定数学模型的数据演化无需金融行情计划。旧类型作品按当前契约重新编排到 `videos/<类型>/<作品名>/`，具体操作见[修订入口](../../.agents/skills/material2video/references/video-revision.md)。

旧类型名、`project.style`、project v1/v2、分镜 v8 及旧准备记录明确拒绝。升级后的材料需重新编排并重新准备；没有兼容入口或迁移命令，旧实现从 Git 历史追溯。

## 恢复与运行

先按[首页快速开始](../../README.md#三分钟做出第一条视频)初始化工程并恢复依赖、字体和浏览器。后续可在仓库根目录通过主项目委托校验、准备或片段检查。

```powershell
uv run m2v validate --project videos/text-motion/demo
uv run m2v prepare --project videos/text-motion/demo
uv run m2v preview --project videos/text-motion/demo --limit-frames 30
```

`init` 生成完整的三秒主题工程。五类默认都不预装三维、图表或业务来源模块，正式创作时改写分镜和 `scenes/opening.tsx`。本地命令、环境和恢复前提见[独立工程说明](../../templates/standalone/README.md)，配音模型见[声音与字幕](voice-and-subtitles.md)。生成后可以直接在作品目录运行，也可由 m2v 委托。默认 `videos/<类型>/<作品名>/` 只是生成位置，显式路径和后续搬移均无须采用该目录层级。默认内容位置可通过 `--content-root` 或 `M2V_CONTENT_ROOT` 设置。

`preview` 只检查片段。最终成片与审核按[媒体评审契约](../../.agents/skills/material2video/references/review-contract.md)执行。`render --jobs N` 可并行，默认 2，内存紧张时改为 1。并行只影响耗时，帧序与成片契约保持一致。

五部示例均为独立工程，可复制到仓库外按各自 README 恢复、预览与完整导出。需要下载的示例媒体按各自 `assets/recipe.json` 恢复，生成媒体与 `outputs/` 不入库。当前示例和恢复入口见[随附示例](../../examples/README.md)。

## 命令与维护

运行 `uv run m2v --help` 查看入口与参数。类型目录通过 `m2v types` 查询；制作辅助操作使用 `m2v author`，金融来源计划使用 `m2v data financial-plan`。旧命令不保留别名。

日常验证只跑受影响的测试与真实媒体节点；正式全量回归仅在用户明确要求或人工发布验证时执行。文档投影可用 `uv run python .agents/skills/material2video/scripts/sync_docs.py --check` 检查。
