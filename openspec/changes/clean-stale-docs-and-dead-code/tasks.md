# Tasks

## 1. 中间产物清理

- [x] 1.1 删除 `work/`、`.cache/`、`.gen/`、`.pytest-tmp/`、`.pytest_cache/`、仓库根 `outputs/`、根目录 `*.log`
- [x] 1.2 删除 `web/.gen/`、全部 `__pycache__/`，并重建 `web/dist/`
- [x] 1.3 删除 `videos/_checks/` 与各作品 `outputs/` 下的检查与缓存产物，保留作品源材料、成片与旁车、准备/评审 JSON、太阳系交付预演与 `stills/`
- [x] 1.4 删除 `examples/*/outputs/` 下的缓存、检查媒体与构建产物（3.58 GB），保留准备/评审/复核记录

## 2. 死代码与测试收敛

- [x] 2.1 删除 `core/report.py`、`engine/qa.py::sheet_interval`、`engine/rhythm.py::_classify`
- [x] 2.2 `types/general/article_text.py` 收敛为 `extract_body`/`count_characters`/`active_source`
- [x] 2.3 删除 `examples/buffer-smoothing/scenes/motion-chart.tsx`、`examples/darts-trial-and-error/scenes/timeline.tsx`
- [x] 2.4 `tests/test_article_text.py` 改为只覆盖存活 API 并补 `active_source` 断言
- [x] 2.5 删除 `remotion.require_environment`（定义了但全仓库零调用）

## 3. 代码合并

- [x] 3.1 新增 `core/validate.py`，`explainer`/`cinematic`/`housing`/`financial`/`soundtrack`/`media_assets` 改用它
- [x] 3.2 新增 `engine/render_pipeline.py`（`SilentRenderSpec` + `generate`/`render` + `assert_no_audio`/`metadata_confirm`/`write_provenance`/`write_report`）
- [x] 3.3 `financial_render.py` 与 `housing_render.py` 改为差异声明 + 薄封装
- [x] 3.4 新增 `types/silent_type.py`，`financial/adapter.py` 与 `housing/adapter.py` 改用它
- [x] 3.5 `explainer_render.py` 复用 `metadata_confirm` 与 `write_report`
- [x] 3.6 更新受影响的测试替身目标（`test_financial_*`、`test_render_performance.py`、`test_single_pass_delivery.py`、`test_render_session.py`、`test_bundle_cache.py`、`test_delivery_access.py`）

## 4. 代码拆分

- [x] 4.1 `engine/remotion.py` → `engine/remotion/` 包（`process`/`bundling`/`session`/`inputs` + 重导出 `__init__`），`implementation_files()` 纳入指纹
- [x] 4.2 `types/financial/financial.py` → `materials.py` + `plan.py` + 公开面重导出
- [x] 4.3 `types/general/code_scenes.py` → `code_scenes/` 包（`config` + `capture`）
- [x] 4.4 `cli.py` → `cli.py` + `commands.py`（命令处理器外移）
- [x] 4.5 `web/src/code-scene/cinematic.tsx` → `cinematic/`（`camera`/`postfx`/`space` + 重导出）
- [x] 4.6 `web/src/compositions/FinancialTimeSeries.tsx` 抽出 `financial/chart.tsx` 与 `financial/overlay.tsx`
- [x] 4.7 示例 `scripts/generate-paths.mjs` → `scripts/lib/paths.mjs` + 入口
- [x] 4.8 `tests/test_financial_video.py` 拆成材料/计划/交付三个文件，共享夹具上移 `tests/financial_helpers.py`

## 5. 文档合并与拆分

- [x] 5.1 `soundtrack` 契约合并到 `article-media-and-sound.md`，原 `media-contract.md` 只留指针
- [x] 5.2 档位对照表只在 `cinematic-video.md`，`SKILL.md` 改为规则 + 指针
- [x] 5.3 `production-workflow.md` 的重复命令块改为指向 `SKILL.md`
- [x] 5.4 交付权限、成片溯源、性能报告、字体覆盖只在 `delivery-and-provenance.md` / `design-tokens.md`
- [x] 5.5 README 实现细节下沉到参考文档
- [x] 5.6 修正 `web/README.md`、`design-tokens.md`、`paths.md`、`docs/PROJECT_PLAN.md`、示例 `VERIFICATION.md` 的过期内容
- [x] 5.7 拆分 `render-contract.md` → `code-scene-runtime.md` + `render-engine.md`
- [x] 5.8 拆分 `paths-and-outputs.md` → `paths.md` + `delivery-and-provenance.md`
- [x] 5.9 拆分 `media-contract.md` → `prepared-and-subtitles.md` + `voice-and-rhythm.md`
- [x] 5.10 全仓库更新旧文件名链接与锚点，核对全部相对链接可达

## 6. 配置与规格

- [x] 6.1 修正 `.gitignore` 被写坏的 `.gen/` 注释行
- [x] 6.2 更新 `types/catalog.json` 的 `skillGuide` 文案并运行 `sync_docs.py` 重新生成三处清单
- [x] 6.3 建立 OpenSpec 变更 `clean-stale-docs-and-dead-code`（proposal/specs/design/tasks）

## 7. 验证与归档

- [x] 7.1 `uv run pytest -q` 全量通过，`pnpm -C web test`、`pnpm -C web typecheck`、`pnpm -C web build` 通过
- [x] 7.2 `sync_docs.py --check` 无漂移；`openspec validate clean-stale-docs-and-dead-code` 通过
- [x] 7.3 可达性复扫：不可达模块只剩 `types/financial/commands.py` 与 `engine/design_tokens.py`
- [x] 7.4 残留引用扫描：死代码名、旧文档名、旧 v7 表述全库无命中（归档历史与明确否定表述除外）
- [x] 7.5 提交并归档变更，同步 `openspec/specs/` 主规格
