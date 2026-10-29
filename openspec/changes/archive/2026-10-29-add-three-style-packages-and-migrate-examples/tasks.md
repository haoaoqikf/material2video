## 1. OpenSpec 提案与规格

- [x] 1.1 创建变更 `add-three-style-packages-and-migrate-examples`，写入 proposal、design 与 3 个新能力 delta；验证：`openspec validate add-three-style-packages-and-migrate-examples --strict` 通过。
- [x] 1.2 写入 8 个已修改能力 delta（`style-registry`、`vibe-fable-style`、`article-explainer`、`article-workspace`、`modular-video-production`、`example-media-recovery`、`video-frame-rate`、`video-production-workflow`），REMOVED 项写 Reason/Migration，MODIFIED 项完整保留原 Scenario；验证：`openspec validate --specs` 与变更校验通过。

## 2. 共享能力与路径

- [x] 2.1 更新 `src/m2v/commands.py` 的 `_validate_project_location` 守卫与注释，确认 `styles/examples/<style-id>/<slug>/` 不被类型路径校验误拒；验证：新增/更新路径测试通过。
- [x] 2.2 更新 `src/m2v/core/workspace.py` 注释与 `article-workspace` 相关错误信息；验证：工作区/输出路径测试通过。
- [x] 2.3 更新 `.gitignore`：新增 `styles/examples/*/*/assets/media/`，替换顶层 `examples/*` 媒体与 article 规则；验证：`git check-ignore` 覆盖三个迁移示例的媒体目录，`git ls-files styles/examples` 不含媒体与产物。
- [x] 2.4 确认 `src/m2v/core/styles.py` 的 `RESERVED_DIRECTORIES = {"examples"}` 保持不变，新增包被动态发现；验证：`uv run m2v styles --json` 返回 5 个包。

## 3. 三个风格包

- [x] 3.1 新建 `styles/doc-archive/`：`style.json`（general 1920×1080、`requires.narration = "none"`、无 assets）、`tokens.json`、`GUIDE.md`，并实现档案媒体框、章节文字、信号线、波形、节点图、闪光环、序列连接、署名块等组件；验证：包可加载，组件 import 只来自 `react`、`m2v/`、`./`。
- [x] 3.2 新建 `styles/count-ledger/`：清单、tokens、GUIDE，实现圆片、行列/网格布局、状态混色、数值文字、世界坐标相机插值/投影组件；验证：包可加载，组件确定性测试通过。
- [x] 3.3 新建 `styles/deep-journey/`：清单（不限制旁白、无 assets）、tokens、GUIDE，实现星场、轨道环、大气/光照、行星材质、章节轨、状态行、信息面板、字幕 scrim、边界脚注组件；验证：3D 组件通过 `m2v/code-scene` 导入，包内构建通过。
- [x] 3.4 为三个包补测试：注册、manifest/tokens、类型画幅、组件静态确定性、指纹覆盖、全组件构建、同帧确定性、未登记导入、`requires.narration`；验证：新增测试通过。

## 4. 回接与迁移

- [x] 4.1 在原 `examples/<slug>/` 位置把三个场景改为导入新风格组件，保持各自 `m2v validate` 与 `prepare` 通过；验证：三个示例 validate/prepare 成功，代表帧与旧版对照并记录有意差异。
- [x] 4.2 只 `git mv` tracked 文件到 `styles/examples/<style-id>/<slug>/`，不整目录移动 `outputs/`；移动或按配方重生成 `assets/media/`、`assets/sound/`；验证：新路径 `m2v validate` 通过，旧 `outputs/` 未被跟踪。
- [x] 4.3 为三个 `project.json` 增加 `style.id`（`doc-archive`、`count-ledger`、`deep-journey`）；验证：`m2v status` 显示所选风格与指纹。
- [x] 4.4 更新示例 README / DESIGN / VERIFICATION 中的路径与措辞，检查示例脚本（`generate-paths.mjs`、`check-motion.mjs`、`render-*.py`、`assets/fetch.py`、`assets/sound/generate.py`）的路径假设；验证：README 命令可执行，脚本无旧路径。
- [x] 4.5 新建 `styles/examples/README.md` 索引 5 个风格示例，区分风格包与示例作品；验证：相对链接有效。

## 5. 删除 examples 与更新引用

- [x] 5.1 确认 `git ls-files examples` 为空、三个迁移示例 validate/prepare 通过后，删除顶层 `examples/`；验证：`git ls-files examples` 为空，目录不存在。
- [x] 5.2 重写 `tests/example_catalog.py` 为 5 个风格示例的名单（`ALL_EXAMPLES` + `CONTENT_CONTRACTS`），路径改为 `styles/examples/<style-id>/<slug>/`；验证：名单与目录一致。
- [x] 5.3 把 `tests/test_examples_strict.py` 迁移为 `test_style_examples_strict.py`，保留通用不变量与三片内容契约，移除“最多 3 个”上限；验证：迁移后的严格测试通过。
- [x] 5.4 迁移 14 个引用示例的测试路径，更新 `web/src/compoundMath.test.ts`、`tests/tools/style_reference.py`、`tests/test_doc_examples.py`；验证：定向测试通过。
- [x] 5.5 更新 `tests/test_vibe_fable_style.py` 的精确集合为 5 个包，确认 `test_font_registry.py` 字体集合不变；验证：风格注册测试通过。
- [x] 5.6 更新 README、AGENTS、ARCHITECTURE、`styles/README.md`、`.agents/skills/material2video/references/` 与 `docs/PROJECT_PLAN.md`；验证：无残留顶层 `examples/` 链接，`sync_docs.py --check` 通过。

## 6. 验证与评审

- [x] 6.1 运行 `uv run m2v styles --json`，确认恰好 5 个包且 `styles/examples` 不出现；运行 5 个示例 `validate`、3 个迁移示例 `prepare`；验证：命令成功，输出符合预期。
- [x] 6.2 运行代表性 `preview` / `render` / `qa` 与组件确定性、包指纹隔离测试；验证：技术检查通过，改示例不改包指纹。
- [x] 6.3 运行 `uv run pytest`（含 slow）、`pnpm -C web test`、`sync_docs.py --check`；验证：全绿或如实记录未验证项。
- [x] 6.4 独立子代理视觉评审：抽查迁移前后代表帧、手机尺寸与风格包实际使用；验证：评审记录齐全，未验证项披露。

## 7. 归档与提交

- [x] 7.1 检查暂存范围，排除媒体、字体二进制、`outputs/` 与其他已有改动；提交实现与文档；验证：commit 仅包含本变更。（提交 `0b8d971`）
- [x] 7.2 任务全部完成后同步 `openspec/specs/` 并归档变更，提交归档结果；验证：`openspec validate --specs` 通过，主规格反映 5 个包与风格示例目录。
