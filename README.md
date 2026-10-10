# article2video

把观点型文章转化为竖屏**单场景动态叙事短视频**的个人内容生产项目。

**一个观点，一个场景，一段动态叙事。**

单场景动态叙事（Single-Scene Visual Narrative）围绕一个核心观点构建持续存在的视觉世界，通过场景内动画、镜头运动、文字与状态变化完成表达，而不是依靠多个独立场景切换。这里的“场景”是整条视频持续存在的视觉世界；技术上的 `stages[]` 是叙事阶段，可以有多个。

例如表达“低成本、高频试错”：人物、飞镖与靶构成持续场景，投掷次数、命中状态、镜头和文字在场景内部变化，共同推动论证。

## 当前能力

项目以项目级 Skill 驱动创作：AI 阅读文章、完成输入审查、选择视觉隐喻并撰写 v4 分镜；共享 React composition（Remotion）按帧渲染画面，确定性脚本准备媒体、校验、合成并验收 MP4。脚本负责可确定的长度、结构和时间轴检查，不调用模型或推断文章语义。

当前标准为：正文及最终口播各 **130～170 字**（目标约150字）；分镜声明时长与配音派生的实际成片时长各为 **35～45秒**。输入审查必须先于口播重写与分镜生成；审查失败时保留原文、给出问题和候选改写，须用户明确采用并重新审查后才能制作。完整契约见 [输入文章审查](.agents/skills/article2video/references/input-review.md)。

v4 使用一个全片 `world`、稳定对象身份、全局状态/镜头/beat 时间轴和多个 `stages[]` 推进叙事。tree 与 code 两种 renderer 共用同一时间上下文；模式数量只作提示，单一隐喻贯穿全片是允许的。有效输入审查、最终口播字数、实际时长、关键阶段与全片评审及五项连续性结论共同构成正式渲染门禁。关键幕先静音动态试制；全片节奏评分必须至少 4/5 且依据定位到有声预演，否则正式渲染阻断。v1～v3 分镜在所有执行入口拒绝，须按 v4 重新编排。

单场景原则、输入审查、时长门禁和连续性评审已落地；各示例的改编与验收记录见 `examples/<slug>/`。历史多幕作品不因阶段数多而自动满足单场景方向，须以当前分镜和评审记录判断。后续路线见[项目规划](docs/PROJECT_PLAN.md)。

## 专题能力

**金融时间序列视频：已支持手机竖屏假设投资价值折线。** AI 编程工具按公司或指数及日期范围核验公开免费日收盘价；request 可设置投资年份和本金，默认从区间首年投入 1,000,000 标的计价币种。以该年首个交易日收盘买入，顶部单行显示不带币种的投资假设标题，右侧小字显示最近实际收盘日期、收益率和收益；收益与市值使用中文万/亿/万亿数量级并以“元”结尾，不展示特定币种名称，底层计算仍使用行情原始计价单位且不换汇。折线显示组合价值，并按盈亏同步切换红绿。不计分红再投资、手续费及税费。动画计划为 version 7、1080×1920、30 fps，横轴分阶段扩展且起点向左铺开，纵轴随已展示组合价值自适应；纵轴刻度和来源口径说明采用小字号。底部显示来源、统计口径和一行历史表现及投资建议风险提示；正式导出须通过绑定材料、资产和完整静音预演的评审，并检查 360×640 缩放与安全区。无事件标注、K 线或周期选择。旧计划通过 `migrate-line` 完整备份并显式迁移，渲染只读固定本地数据。制作流程见[金融时间序列视频专题参考](.agents/skills/article2video/references/financial-timeseries-video.md)。

使用方式、材料格式和验收规则见[专题制作参考](.agents/skills/article2video/references/financial-timeseries-video.md)；可用命令为 `financial_video.py init|validate|render`。金融图表绘图区从 x=92 开始，纵轴刻度使用 14 px 并可进入 x=24 专用安全区，投资价值折线为 3 px。该专题不经过文章字数、口播和有声评审门禁，文章入口保持原行为。


## 快速开始

```bash
uv sync
pnpm -C web install
pnpm -C web build
uv run playwright install chromium

# 严格校验示例
uv run python .agents/skills/article2video/scripts/validate.py examples/buffer-smoothing/storyboard.json --strict

# 运行相关测试
uv run pytest
pnpm -C web test
```

制作新作品的顺序为：

```text
输入审查 → 核心观点与隐喻设计 → 分镜及动画编排 → 配音准备
→ 实际时长检查 → 评审与渲染
```

文章和产物放在 `videos/<slug>/`，该目录已忽略、不入库；也可通过 `--content-root` 或 `A2V_CONTENT_ROOT` 将内容放在仓库外。之后按 [文章生成分镜](.agents/skills/article2video/references/article-to-storyboard.md)、[制作流程](.agents/skills/article2video/references/production-workflow.md) 和 [目录约定](.agents/skills/article2video/references/paths-and-outputs.md) 操作。仓库固定分发 `buffer-smoothing`、`darts-trial-and-error`、`keynote-baseline` 三个示例，`examples/` 最多 3 个且后续只维护这三例。正式渲染示例：

```bash
uv run python .agents/skills/article2video/scripts/validate.py videos/<slug>/storyboard.json --strict
uv run python .agents/skills/article2video/scripts/prepare.py --storyboard videos/<slug>/storyboard.json
uv run python .agents/skills/article2video/scripts/production.py status --storyboard videos/<slug>/storyboard.json
uv run python .agents/skills/article2video/scripts/render.py --storyboard videos/<slug>/storyboard.json --media videos/<slug>/outputs/media/media.json
```

## 项目结构

- `.agents/skills/article2video/`：创作工作流、分镜/媒体/渲染/评审契约。
- `web/src/compositions/` 与 `web/src/runtime/`：共享 composition 和全局时间轴运行时。
- `web/src/registry/registry.json`：视觉原语唯一真源；运行 `sync_catalog.py --check` 检查生成目录是否漂移。
- `.agents/skills/article2video/scripts/`：确定性校验、媒体准备、预览、评审和渲染工具。
- `examples/`：可运行作品、动画设计和评审记录；作品文章和分镜纳入版本控制。
- `openspec/changes/`：进行中的能力变更；`openspec/specs/`：已归档并落地的规格。
- `docs/PROJECT_PLAN.md`：产品路线；[AGENTS.md](AGENTS.md)：仓库协作、验证与交付规则。

## 当前边界

文章理解与分镜生成由 AI 工具根据项目 Skill 执行；仓库不含模型调用或自动生成服务。自动选曲、平台发布、批量渲染和成片历史版本也不在当前能力内。语义评审由 AI 阅读材料后填写并绑定制作记录，脚本负责有效性与版本门禁，不替代语义判断。
