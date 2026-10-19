## Why

仓库经过多轮大改（删除 article-narrative 身份、受控模板、视觉主题与旧动画子系统）后，留下三
类残留：无人消费的实现（`core/report.py`、`qa.sheet_interval`、`rhythm._classify`、字数门禁
API）、与实现矛盾的文档段落（general 被写成 v7、已删除的令牌表、已废除的 130～170 字门禁），
以及约 4.3 GB 中间产物。同时同一份契约在代码与文档里各有多份副本，过大的文件又把不同职责混在
一起。结果是每次改动都要先判断「这处是不是旧路径」，文档描述的能力与代码实际能力持续背离。

## What Changes

- **删除死代码**：`core/report.py`、`engine/qa.py::sheet_interval`、`engine/rhythm.py::_classify`、
  `types/general/article_text.py` 的字数门禁 API、两个依赖已删除主题机制的示例场景。
- **合并重复实现**：校验原语 → `core/validate.py`；无声类型渲染管线 → `engine/render_pipeline.py`；
  无声类型适配器 → `types/silent_type.py`；无声音轨复核只留一份。
- **拆分过大文件**：`engine/remotion.py` → 包（进程/打包/会话/输入）；`types/financial/financial.py`
  → `materials.py` + `plan.py`；`types/general/code_scenes.py` → 包；`cli.py` → `+ commands.py`；
  `web/src/code-scene/cinematic.tsx` 与 `web/src/compositions/FinancialTimeSeries.tsx` 按职责抽出；
  示例 `scripts/generate-paths.mjs` → `lib/paths.mjs` + 入口；`tests/test_financial_video.py` 按
  材料/计划/交付三分。
- **合并与拆分文档**：`soundtrack` 契约、档位对照表、cinematic 命令块、交付权限与成片溯源段落各留
  一处真源；`render-contract.md` → `code-scene-runtime.md` + `render-engine.md`；
  `paths-and-outputs.md` → `paths.md` + `delivery-and-provenance.md`；`media-contract.md` →
  `prepared-and-subtitles.md` + `voice-and-rhythm.md`；README 的实现细节下沉到参考文档。
- **删除中间产物**：`work/`、`.cache/`、`.gen/`、`.pytest-tmp/`、仓库根 `outputs/`、`videos/_checks/`
  与各作品 `outputs/` 下的检查与缓存产物；保留作品源材料、已交付成片与其旁车、准备/评审 JSON。
- **修正过期文档**：`web/README.md` 的 v7 段落、`design-tokens.md` 已不存在的令牌表、
  `docs/PROJECT_PLAN.md` 已完成的迁移条目、`.gitignore` 第 25 行的坏行、示例 VERIFICATION 的历史章节。
- **BREAKING（规格层面）**：`video-production-workflow` 的「输入到输出全链路门禁」不再要求
  130～170 字与 35～45 秒——该门禁的实现早已删除，规格只是没跟上。

## Capabilities

### New Capabilities

（无：本次不引入新能力。）

### Modified Capabilities

- `video-production-workflow`：「输入到输出全链路门禁」需求改写为当前契约——保留「article 输入须有
  当前有效审查 pass」「候选稿须有明确采用证据」「不合格输入不得自动进入后续制作」，删除字数与时长
  门禁，并把场景替换为当前可验证的行为。

## Impact

- **代码**：`src/m2v/{core,engine,types}` 与 `web/src/` 的模块布局变化；公开函数签名、错误消息与
  stdout 协议保持不变（唯一例外：四个入口的 composition 元数据不匹配文案统一为一种措辞，判定不变）。
- **测试**：`tests/test_article_text.py` 收敛为只覆盖存活 API；三个测试文件的替身目标随合并调整；
  `tests/test_financial_video.py` 拆分；其余用例不变。
- **文档**：`.agents/skills/material2video/**`、`README.md`、`web/README.md`、`docs/PROJECT_PLAN.md`、
  `examples/solar-system-journey/VERIFICATION.md`。
- **磁盘**：删除约 4.3 GB 中间产物（全部为已忽略路径，不进版本控制）。
- **不受影响**：渲染契约、分镜结构、视觉规范、类型目录与 CLI 命令集均不变。
