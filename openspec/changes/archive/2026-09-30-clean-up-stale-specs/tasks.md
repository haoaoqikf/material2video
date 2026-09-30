# Tasks: clean-up-stale-specs

## 1. 变更文档

- [x] 1.1 写 `proposal.md`：动机、变更清单、能力清单、影响面
- [x] 1.2 写 14 个能力的 delta 规格（`deterministic-third-party-adapters`、`remotion-renderer`、`frame-driven-motion`、`keynote-design-system`、`article-workspace`、`font-coverage`、`font-subsetting`、`semantic-motion-timeline`、`visual-direction-pipeline`、`article-to-storyboard`、`cinematic-directing`、`render-provenance`、`declarative-video-scenes`，加上 Purpose 直改的 `react-component-registry`）
- [x] 1.3 写 `design.md`：场景名不可删的约束与三条取舍
- [x] 1.4 `openspec validate clean-up-stale-specs` 通过

## 2. 主规格直改（Purpose 与目录残留）

- [x] 2.1 `remotion-renderer` Purpose：版本 2 → 版本 3
- [x] 2.2 `declarative-video-scenes` Purpose：去「视觉组件 / 共享页面 / 保留既有视频的工作方式」
- [x] 2.3 `react-component-registry` Purpose：组件集合 / 标注键 → 原语集合 / 属性
- [x] 2.4 `article-to-storyboard` Purpose：组件目录 → 原语目录
- [x] 2.5 删除空的 `openspec/specs/storyboard-scene-tree-migration/`（未跟踪、无 spec.md）
- [x] 2.6 `frame-driven-motion` Purpose：去「弹性曲线由物理参数给出」「外部动效实现随仓库分发」
- [x] 2.7 逐条复核 `openspec/specs/` 下每个需求块，补上遗漏的 delta（`declarative-video-scenes`、`keynote-design-system` 的图形基元与重点面墨色、`frame-driven-motion` 的纯函数条与入场轨迹条）

## 3. 归档与复核

- [x] 3.1 按 `openspec-archive-change` 流程把 delta 同步进 `openspec/specs/`，变更移入 `openspec/changes/archive/`（归档为 `2026-09-30-clean-up-stale-specs`；新增 10 / 修改 13 / 移除 26；`deterministic-third-party-adapters` 整能力退场，主规格删除）
- [x] 3.2 复核归档后的主规格：旧需求名、`IDLE_TOKENS`、`figures.js`、`版本 2 渲染契约`、`未启用预设`、`data.figure.kind`、`/__a2v__/` 均不再出现
- [x] 3.3 `openspec list --specs` 正常，`openspec validate --all` 20 项全通过

## 4. 同批代码与文档清理（不改变行为，不在本变更的规格 delta 内）

- [x] 4.1 删除 `a2v/constitution.py` 与 `tests/test_constitution.py`，同步 `inspect.py` / `keynote.py` / `cli.py` / `scripts/review.py` 的分工表述
- [x] 4.2 删除零引用符号：`inspect.py` 的 `probe_scene`/`check_page_with_storyboard`/`_TEXT_SLOT`/`_HERO_SCENE_TYPES`、`fonts.py` 的 `_FONT_URL`/`_CONTENT_STRING`/`page_fonts`/`preset_strings`/`audit_page`、`catalog.py` 的 `known_types`、`motion_plan.py` 的 `PHASES`、`paths.py` 的 `workspace_outputs`、`source_policy.py` 的第三方分类表挂载分支
- [x] 4.3 删除 Web 死代码与孤儿许可证：`runtime/timeline.ts` 的两个换算函数、`schema/storyboard.ts` 的三个类型别名、`web/LICENSES/`
- [x] 4.4 修代码内陈旧 docstring / 文案（`__init__.py`、`scripts/render.py`、`scripts/review.py`、`scripts/preview.py`、`a2v/render.py`、`a2v/paths.py`、`a2v/assets.py`、`a2v/motion.py`、`a2v/http_server.py`、`a2v/browser.py`、`a2v/media.py`、`web/vite.config.ts`、`web/src/contract/bridge.ts`、`tests/test_motion_review.py`、`tests/test_paths.py`、`tests/test_figure_contrast.py`、`tests/test_content_root_e2e.py`、`pyproject.toml`）
- [x] 4.5 修活文档硬事实：`web/README.md`、`references/visual-spec.md`、`render-contract.md`、`keynote-design-system.md`、`design-constitution.md`、`storyboard-schema.md`、`visual-review-rubric.md`、`SKILL.md`、`README.md`
- [x] 4.6 `docs/PROJECT_PLAN.md` 全文清理过期引用（当前状态区按事实改写，历史区就地括注）
- [x] 4.7 删除墓碑文档 `references/third-party-components.md`、`references/figure-catalog.md`
- [x] 4.8 验证：`uv run pytest`、`pnpm -C web test`、`pnpm -C web typecheck`、`sync_catalog.py --check`、文档引用复核脚本
- [x] 4.9 检查暂存内容并创建 Git 提交
