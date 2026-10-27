---
name: material2video
description: 使用统一 m2v 制作入口创作或修订金融时间序列、住宅时间序列、通用讲解视频。用于准备类型材料、编排、局部修改、预演、评审、渲染与排查不一致问题。
---

# Material2Video（材料成片）制作 Skill

开始前读取作品的 `project.json`，确认类型，再按类型参考准备材料。项目使用共享制作底座、独立视频类型和统一 `m2v` 入口；当前能力与命令见仓库 [README](../../../README.md)，稳定模块边界见 [ARCHITECTURE](../../../ARCHITECTURE.md)。

| 类型 | 创作指导 |
|---|---|
<!-- generated:type-catalog:start -->
| `financial-timeseries` | [金融时间序列视频](references/financial-timeseries-video.md)：核验行情口径、投资计算并通过完整候选自动验收。 |
| `general` | [作品视觉设计与制作流程](references/production-workflow.md)、[视觉创意导演方法](references/visual-creative-direction.md)、[分镜结构](references/storyboard-schema.md)、[媒体素材与音效](references/article-media-and-sound.md)、[代码场景契约](references/code-scene-runtime.md)：v8 全画布代码场景多幕讲解。 |
| `housing-timeseries` | 按 `series.json` 提供连续年度住宅销售额、面积、计算均价与来源口径；生成 1080×1920、60 fps 无声折线视频。 |
<!-- generated:type-catalog:end -->

## 制作流程

制作中调整规范或工具时，先按根目录 [AGENTS.md 的 OpenSpec 工作流](../../../AGENTS.md#openspec-工作流)判断影响范围：简单、局部、影响明确的修改可直接实施，简述原因并完成验证、文档同步和提交；涉及能力、契约、核心流程、评审职责或验收条件等重要变化时先走 OpenSpec。发现超出简单范围时先补建变更再继续，用户明确指定的流程优先。

已有作品需要改字、换图、调整旁白、节奏或结构时，先走[视频修订入口](references/video-revision.md)：从修改意图定位影响范围，沿用有效方案与证据，串联现有命令完成修订。general 的重入阶段与基线仍以[制作流程](references/production-workflow.md#重制启动)为准；修订不是自动重开全套选案，也不豁免最终复核。

- 按材料审查、时间轴准备、按需检查、一次全片生成、验收与复核的顺序推进。有自身旁白时先确定音色；无旁白作品跳过选音。生成产物是派生文件，不能代替可编辑材料。
- 预览只用于局部片段检查：默认前十秒或显式指定短窗口，不得用接近全片的窗口代替正式生成；需要看全片时执行 `render`，评审帧包从片段或正式成片抽取。
- 所有类型都由一次完整渲染生成候选，自动验收后交付同一文件。技术交付不代表制作复核完成；无需用户为常规阶段确认或试听，也不要求直接播放视频或连续收听声音。按类型用帧序列、画面量测、字幕时间戳和自动音频信号复核，并记录覆盖范围。
- 通用作品按方案确定、粗片验证、精制修订、最终验收四阶段执行，不区分普通与电影级制作档位；`productionProfile` 和 `--profile` 已移除并拒绝。用户方案足以实施时直接采用；否则比较叙事候选。阶段、关键帧门和重制基线规则见[制作流程](references/production-workflow.md)。
- 每个场景及内部镜头在 `DESIGN.md` 标 A/B/C 镜头等级：A 级记忆镜头优先投入关键帧、时间结构与动态验证，B/C 级服务 A 级但不降低可读性底线；等级本身不触发额外审核，也不进入分镜 JSON 或 CLI。时间结构只在审核计划声明结构时序风险的镜头必填。
- 制作过程中发现可复用的流程改进，应在当前工作中实施并验证；受范围限制的事项按根目录 [AGENTS.md](../../../AGENTS.md) 记录。
- 评审须区分实际缺陷、创意风险、审美偏好和证据不足。适用审核轮按[独立评审流程](references/subagent-review.md)隔离执行，轮次与人数按[审核策略](references/checkpoint-gates.md#审核计划与风险触发)派生；详细证据、问题闭环和完成边界见[视觉复核](references/visual-review-rubric.md)与[导演审查](references/director-review-and-edit.md)。
- 作品面向手机复核，但画幅服从作品设计。素材来源与许可留在作品材料，片尾只保留一份简短署名；画面不出现仓库路径或内部制作提示。
- 画面注释沿用[项目约定](../../../AGENTS.md#修改规则)的从紧范围；确需添加时一律用明显小于主体文字的小字，置于次要位置，不遮挡主体、关键数据、字幕或关键动作，不争夺焦点。示意／实拍边界标注是次要标记，以大屏原尺寸可辨、手机横屏不可辨为目标，不要求手机尺寸可读；承载必要信息的口径与字幕仍须可读；素材署名默认可读，用户明确要求随标注缩小时须把完整署名与许可留在作品材料与发布说明。空间不足先精简或调整位置；主题、对象名称、结论和正常字幕不归为注释，不设跨画幅统一像素字号。制作和修订均按[视觉复核](references/visual-review-rubric.md#反目标写进-designmd按题材检查)检查完整出现窗口。
- 制作前明确受众与表达目标，评审覆盖信息推进、自然文案和完整事件窗口；具体标准见[节奏与创作](references/creative-production.md)、[统一制作与质量工具](references/cinematic-video.md)和[视觉复核](references/visual-review-rubric.md)。

新启动 general 作品和后续重制必须按[检查点门](references/checkpoint-gates.md)在 DESIGN.md 声明制作合同 v2 并记录 G0–G6 证据；状态为制作完成条件，不增加用户审批或导出硬门禁。v1 合同明确拒绝，不自动迁移或继承通过。

制作门、审核轮、风险触发、人数、覆盖表与完成条件统一见[检查点契约](references/checkpoint-gates.md)。评审包隔离和执行方式见[独立评审流程](references/subagent-review.md)，视觉判断见[视觉复核](references/visual-review-rubric.md)。

存量在制作品沿用启动时合同，不要求切换流程、重做准备或补造评审。

可选风格独立于视频类型；选定 `project.json` 的 `style.id` 后，按[风格接入契约](references/style-pack.md)读取指导并落实到 DESIGN.md，显式使用参数、组件与资产。当前无内置风格，未选择时沿用作品设计。

## 常用命令

```powershell
uv run m2v types
uv run m2v init --type general --project <slug>
uv run m2v validate --project videos/general/<slug>
uv run m2v prepare --project videos/general/<slug>
uv run m2v preview --project videos/general/<slug>  # 可选局部片段检查（默认前十秒）
uv run m2v render --project videos/general/<slug>
uv run m2v status --project videos/general/<slug>
```

`lookdev`、`qa`、`assets audit` 和 `review` 是按需检查工具，不是完整渲染的前置条件。命令参数与迁移入口以 `uv run m2v --help` 和 README 为准。修改材料或实现后重新 `prepare`；交付候选、缓存与清理语义见[交付与溯源](references/delivery-and-provenance.md)。

金融计划与旧材料升级见[金融类型参考](references/financial-timeseries-video.md)。住宅材料规则见[住宅类型参考](references/housing-timeseries-video.md)。通用输入审查、候选稿和分镜规则见[通用输入与分镜](references/article-to-storyboard.md)及[分镜结构](references/storyboard-schema.md)。

## 音色选择

仅对有自身旁白的作品执行。助手按旁白文本和服务元数据选择，不要求试听；用户明确指定的音色优先，旁白未变时可复用已有选择。

1. 阅读按播放顺序排列的完整旁白，判断语言、受众、内容和表达风格。
2. 使用 `uv run m2v voices --json` 查询可用音色；查询失败时报告并处理，不虚构候选。
3. 将音色及选择理由、旁白摘要写入 `project.json`；手动更改音色时移除旧助手选择记录。
4. 旁白变化时重新判断并更新记录；之后执行 `prepare`。字段、摘要和覆盖语义见[配音契约](references/voice-and-rhythm.md#配音音色与语速)。

## 通用场景要点

- 先按表达目的选择外部素材、代码或混合；默认运动载体顺序为真实视频 → 代码动画/示意 → 静态图片。外部素材优先找合适的视频，图片仅作最后手段（静态原件、识别或质感），不得用静帧推拉、缩放或轻微位移伪装视频；搜索框输入、点击等适合代码的过程可直接合成。选择与回退理由复用 DESIGN.md 现有记录，不设视频占比；详细标准见[素材选择规范](references/visual-material-selection.md#视频优先与代码适用场景)。

- 通用作品当前实现基线采用 v8 分镜和作品目录内的 React `code` 全画布场景。这是实现方式，不改变「先确定目标画面、再选择实现方案」的制作原则；其他资产或预渲染内容按现有素材契约导入，由 React 场景组合与呈现，具体边界见[技术链路](references/production-workflow.md#技术链路)。旧模板、主题、`general-plan` 和片段嵌入不属于当前契约。
- 先确定表达和视觉事件，按[审核计划](references/checkpoint-gates.md#审核计划与风险触发)执行适用的目标关键帧、时序与动态验证，再扩展全片；不为普通镜头增加强制导演卡或反转。核心图形高潮另按[视觉力量设计](references/visual-impact-design.md)比较至少三种视觉机制。设计方法见[视觉创意导演](references/visual-creative-direction.md)。
- 用户要求学习、拆解或借鉴一条或多条参考视频时，先按[参考视频逆向拆解](references/reference-video-analysis.md)提炼观看驱动力与可迁移规则；明确要求外观相似时，再按[参考风格契约](references/reference-style.md)记录视觉采用项和量测，随后做独立冷审。
- 素材必须先导入并留证，再通过素材 ID 使用；声音来源、音轨和混音规则见[媒体与音效](references/article-media-and-sound.md)。参考作品默认不进入成片；只有用户明确要求复用整条参考音轨时才运行 `m2v ref audio --user-authorized "<授权说明>"` 并记录授权，渲染链不直接读取 `refs/`。
- 场景按录制时钟推进，旁白字幕默认烧录；共享动效原语以 `progress` 驱动，不内置作品主题。运行时细节见[代码场景契约](references/code-scene-runtime.md)。
- 最终复核覆盖完整成片和风险区间，记录证据摘要、时间范围、问题处理与未覆盖项。量测能力和局限见[视觉复核](references/visual-review-rubric.md)。

## 新增视频类型

在 `src/m2v/types/catalog.json` 登记类型、材料入口、初始化模板和文案，再实现该类型适配器。共享入口不按类型名硬编码分发；类型清单由目录生成。类型目录或制作门/审核策略修改后运行 `python .agents/skills/material2video/scripts/sync_docs.py`，用 `--check` 只验证、不写入。
