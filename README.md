# article2video

面向短视频的离线制作工具链，采用**共享制作底座、独立视频类型、统一制作入口**。当前重点发展金融时间序列等专用视频，再沉淀可复用能力，逐步扩展到通用多场景编排。

## 当前视频类型

- `financial-timeseries`：公开日收盘价材料、假设投资计算、手机竖屏折线画面和完整预演评审。
- `article-narrative`：文章 v4 单场景叙事，保留配音、状态轨道、镜头、代码世界与文章制作门禁。
- `general`：受控图文场景、金融/文章完整片段及作品级 React 场景的多场景时间轴。首版 1080×1920、30 fps，支持硬切、交叉淡化和可选口播。

文章正文、金融原始材料与作品产物属于内容，不入库。三个固定示例为 `buffer-smoothing`、`darts-trial-and-error`、`keynote-baseline`，不增删或替换。

## 快速开始

```powershell
uv sync
pnpm -C web install
pnpm -C web build
uv run playwright install chromium
uv run a2v types
uv run pytest
pnpm -C web test
```

统一入口以作品目录为唯一归属：

```powershell
uv run a2v init --type general --project videos/<slug>
uv run a2v validate --project videos/<slug>
uv run a2v prepare --project videos/<slug>
uv run a2v preview --project videos/<slug>
uv run a2v review-template --project videos/<slug>
# 人工或 AI 查看预演并填写 outputs/review.json，状态仍为 pending，须明确写入评审结论与证据。
uv run a2v review --project videos/<slug>
uv run a2v render --project videos/<slug>
```

`init` 会生成材料模板。文章工作流仍先完成原文输入审查，再编辑 v4 分镜。金融材料沿用 request、prices 和 animation-plan，可用 `a2v financial plan --project <目录>` 离线生成折线编排；旧金融材料使用显式 `a2v migrate --from financial` 迁移。旧文章仅接受有效 v4；v1～v3 必须重新编排。`render` 不修改原始材料，要求准备记录与评审仍匹配当前指纹。

可用命令：`types`、`init`、`validate`、`prepare`、`preview`、`review-template`、`review`、`status`、`render`、`migrate`。文章专属的输入审查与候选稿操作使用 `a2v article input-review|candidate|adopt-candidate`；操作性语义创作指导仍见 [article2video Skill](.agents/skills/article2video/SKILL.md)。

作品可以位于仓库外内容根；`A2V_CONTENT_ROOT` 用作默认内容根。架构和材料契约见 [OpenSpec 变更](openspec/changes/refactor-modular-video-production/proposal.md)，未来能力路线见 [项目规划](docs/PROJECT_PLAN.md)。

## 项目结构

- `src/a2v/core/`：作品契约、路径、指纹、公共错误。
- `src/a2v/engine/`：Remotion 构建与缓存、渲染会话、音视频合成和验收。
- `src/a2v/types/`：文章、金融、通用类型及显式注册。
- `src/a2v/cli.py`：`a2v` 统一命令入口。
- `web/src/compositions/`：共享 composition、金融画面、文章世界与通用场景宿主。
- `.agents/skills/article2video/references/`：材料、类型创作与评审操作参考。
- `openspec/specs/`、`openspec/changes/`：已归档规格与进行中的变更。

本轮不建设行情服务、云端队列、账号、自动发布、自动选曲或第三方插件系统。
