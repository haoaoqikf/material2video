# 参与 Material2Video

复现失败、文档错误和功能建议都欢迎反馈。提交前先搜索已有 Issue，记录分支或提交、执行目录和命令。涉及成片观感时，提供带时间点的抽帧；涉及失败时，提供脱敏的关键日志，不上传私有素材或凭据。

## 开发环境与验证

使用带 `.git` 的仓库检出，准备 Python 3.11+、uv、Node.js 22.12+ 和 pnpm 10.15.0。只做 Python 开发时先运行 `uv sync`。前端构建或渲染还需要按[字体仓说明](fonts/README.md)恢复登记字体；独立作品按[独立工程说明](templates/standalone/README.md)在作品目录安装依赖和浏览器，不借用 `web/` 的依赖。

| 目的 | 从仓库根目录执行 |
| --- | --- |
| Python 专项测试 | `uv run pytest 路径::测试名`，或选择直接受影响的文件；默认排除 `media`、`slow`，完整 `uv run pytest` 只用于明确要求或正式发布验证 |
| Python 静态检查 | 已在环境安装 Ruff 时运行 `uv run ruff check src tests`；它不在当前开发依赖中，可用 `uv run --with ruff ruff check src tests` 临时运行，不改锁文件 |
| 安装共享前端依赖 | `pnpm -C web install --frozen-lockfile` |
| 前端验证 | `pnpm -C web run typecheck`、`pnpm -C web run test`；构建时运行 `pnpm -C web run build` |

涉及渲染时，在受影响作品内运行相应的 `pnpm run preview`、`pnpm run render` 或 `pnpm run qa`，按变更范围记录证据。提交前运行 `git diff --cached --check` 并查看暂存文件；不提交生成媒体、依赖、缓存、字体二进制或凭据。

## 提交与 OpenSpec

提交信息采用 `类型(可选范围): 中文动宾短句`，例如 `fix(render): 修复预览末帧采集`、`feat(assets): 增加素材台账导出` 或 `docs: 补充字体恢复步骤`。一个提交只包含同一目的的变更及其验证或配套文档。

[AGENTS.md 的 OpenSpec 工作流](AGENTS.md#openspec-工作流)是权威，以下引用其中的「必须使用 OpenSpec」条目：

> **必须使用 OpenSpec**：新增或移除能力、命令、视频类型；改变分镜结构、材料格式、渲染契约或兼容性；调整核心制作流程、评审职责、验收门禁或完成条件；跨模块的重要行为变化，或存在明显方案分歧、影响难以确定的修改。此类变更先在 `openspec/changes/` 记录提案、规格与任务，再实施并验证；完成后归档，使 `openspec/specs/` 反映已实现行为。命中这些条件时，不因同时包含简单修改而豁免。

## 维护者发布流程

1. 在 `develop` 完成正式发布验证，把版本说明写入 [`docs/release-notes/`](docs/release-notes/)，再通过 PR 合并到 `main`。
2. 在已验证的 `main` 提交打版本 tag（例如 `v0.1.0`），再在 GitHub 用同一 tag 创建 Release，以仓库内对应文件作为 Release 正文。
3. 在 GitHub 的 Pages 设置中选 GitHub Actions。[现有工作流](.github/workflows/pages.yml)在 `main` 收到涉及 `docs/site/` 的推送后自动部署；如果没有触发，手动运行该工作流并检查五个作品页。
4. 维护者在仓库 About 填写简介、已验证的作品集地址和 topics，并在仓库设置手动上传 [social preview](docs/site/assets/social-preview.png)。Pages 部署不会替换该图片设置。
