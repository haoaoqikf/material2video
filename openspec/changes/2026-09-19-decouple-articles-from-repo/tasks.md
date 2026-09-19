# 任务：文章与仓库解耦

## 1. Git：`videos/` 退出管理

- [x] 1.1 `git rm -r --cached videos` 取消跟踪（磁盘文件保留），`.gitignore` 增加 `/videos/` 并注明「文章内容不入库」；证据：`git ls-files videos` 为空、`git status` 不列出 `videos/`。
- [x] 1.2 `AGENTS.md` 的修改规则补一条：文章内容（`videos/`）属本机内容不入库，代码与交付文档仍需入库。

## 2. 两层根与内容根（`a2v/paths.py`）

- [x] 2.1 新增 `CONTENT_ROOT_ENV`、`content_root(explicit)`、工作区根推导；`ArticlePaths` 增 `repo_root` / `workspace_root`（全仓库统一改名，保留 `output_dir` 语义）。
- [x] 2.2 `article_paths / for_page / for_storyboard` 接受 `content_root=None`：命中 `<repo>/videos|examples/<slug>` 时工作区根 = 仓库根（既有行为），否则要求命中 `<内容根>` 下的同构目录。
- [x] 2.3 两者都不满足时报错，文案点名 `--content-root` 与 `A2V_CONTENT_ROOT`；证据：`tests/test_content_root.py::TestContentRootResolution::test_external_article_needs_a_content_root` 断言错误里同时出现两个名字。
- [x] 2.4 输入文件在仓库之外（向上找不到 skill 标记）时，仓库根回退到运行中的 bundle 所在仓库：被挂载的共享资产正是那一份，否则内容根里的文章无从取共享页面/别名资产。

## 3. 共享资产别名 `/__a2v__/`

- [x] 3.1 `a2v/static_server.py`：`LocalServer(root, port=0, cors=False, mounts=None)`、`url_for(path)`、挂载感知的 `translate_path`（归一化 + 拒绝 `..` 与越界 + 不列目录）；skill 资产目录由脚本自身位置推出，常量 `SKILL_MOUNT = "/__a2v__"`。
- [x] 3.2 `a2v/assets.py`：`local_assets(page, html, mounts=None)` 解析 `/__a2v__/x`，使渲染前扫描与字体覆盖对内容根页面同样覆盖共享资产。
- [x] 3.3 `a2v/render.py`：`_resolve_page_url` 用挂载服务器与 `url_for`；`_default_serve_root(page, content_root=None)` 先取文章工作区根、失败回落页面目录。
- [x] 3.4 页面引用规则写进文档：内容根页面用 `/__a2v__/`，仓库内页面继续相对路径（`references/visual-spec.md`「资产引用」、`references/paths-and-outputs.md`）。

## 4. 溯源 v3

- [x] 4.1 `_write_provenance` 写 `version: 3` + `workspace`（相对产物目录）+ `page`（相对工作区根，别名目录内记别名键）+ 别名资产键。
- [x] 4.2 `provenance_status` 按 `workspace` 反解、按运行中的 skill 解析别名键（页面键同样走 `key_path`）；v2 及更早判 `unknown` 并说明「旧格式，请重渲一次」。
- [x] 4.3 `a2v/media.py::asset_fingerprint` 增可选 `workspace_root` / `mounts`，默认行为不变；证据：既有 `tests/test_asset_fingerprint.py` 断言不改仍全绿。
- [x] 4.4 资产键按**文件位置**判定（`mount_key`）：共享页面内部用相对路径引用共享资产时同样记别名键，否则内容根里的每份成片复核时都会报「资产不见了」。

## 5. 命令行与入口

- [x] 5.1 `render.py` / `prepare.py` / `preview.py` / `review.py` 增加 `--content-root` 并透传（`validate.py` 只吃显式路径，不加）。
- [x] 5.2 `_shared_page` 用仓库根、`_storyboard_url` 相对工作区根；声明式路径显式传 `serve_root = article.workspace_root`，且声明式缺少归属时直接报错而不是崩在 `None` 上。
- [x] 5.3 `_default_media_dir / _default_review_dir / _reject_foreign_media_dir` 一律基于工作区根下的 `outputs/`；跨文章合成仍被拒绝。

## 6. 测试

- [x] 6.1 新增 `tests/test_static_mounts.py`：挂载命中、嵌套路径、未知前缀 404、`/__a2v__/../` 与 URL 编码越界拒绝、别名不列目录、`url_for` 静态根/挂载/不可达三种情形。（CORS 媒体服务器由既有 `tests/test_media.py::test_media_range_requests` 覆盖。）
- [x] 6.2 新增 `tests/test_content_root.py`：参数与环境变量两条设置路径、命令行优先、仓库内示例优先、CLI 透传与默认输出、未设置时的错误文案。
- [x] 6.3 新增 `tests/test_content_root_e2e.py`（`slow`）：临时内容根 + 声明式共享页面与专属页面两条路，`--limit-frames 2 --no-probe`，断言产物落 `<内容根>/outputs/<slug>/previews/silent.mp4` 且溯源可复核。
- [x] 6.4 `tests/test_render_provenance.py`：v3 往返（外置内容根 + 别名资产 → `current`）、共享资产改动/删除按别名键报出、别名键越界按「不见了」处理、缺 `workspace` → `unknown`、v2 → `unknown`。
- [x] 6.5 `tests/test_render_precheck.py` 补别名引用的共享样式/脚本仍被扫描（含别名越界不读）；`tests/test_asset_fingerprint.py` 补别名键与工作区相对键的判定。
- [x] 6.6 去掉对未跟踪内容的硬依赖：`test_figures_assets.py` 改对仓库内示例页面参数化；`test_font_coverage.py` / `test_font_subsetting.py` 的参数表移除 `videos/never-fear-interviews/storyboard.json`。

## 7. 文档

- [x] 7.1 `references/paths-and-outputs.md`：两层根模型、内容根设置与优先级、页面引用共享资产的两条规则、溯源 v3 口径、错误对照表。
- [x] 7.2 `SKILL.md`：目录职责表与标准流程注明内容根；命令速查与常见问题补内容根/别名 404；当前边界补「内容根不自动探测」。
- [x] 7.3 `README.md`：当前状态（内容根 + 解耦）、「制作一支新视频」、已完成文章表格加「本机内容不入库」说明、溯源口径更新为 v3。
- [x] 7.4 `docs/PROJECT_PLAN.md` 的多篇文章一节改为内容根模型并新增「内容根：文章与仓库解耦」小节；`assets/theme.css` 与 `references/visual-spec.md` 的示例引用补别名写法；`references/render-contract.md` 的扫描范围与溯源字段同步。

## 8. 验证与交付

- [x] 8.1 `uv run pytest -m "not slow"` 与 `uv run pytest` 全绿；`git ls-files videos` 为空。
- [x] 8.2 冒烟：不设内容根限帧渲染 `examples/why-effort-fails` 成功；设 `A2V_CONTENT_ROOT` 指向临时内容根读其文章限帧渲染成功、产物落位正确（由 6.3 的端到端用例覆盖）。
- [x] 8.3 检查暂存内容，排除密钥、缓存与生成媒体；提交本次改动（含文档与 OpenSpec 变更）。
- [x] 8.4 归档变更：同步 `openspec/specs/` 并把本变更移入 `openspec/changes/archive/`，提交归档结果。
