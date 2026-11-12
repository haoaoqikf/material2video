# 删除验证与独立复核

日期：2026-11-12。

- 两个指定目录已完整删除，包含本地依赖、缓存、恢复媒体和输出；专属布局测试一并删除。首次 Git 清理遇到 Windows 长路径限制，使用单次命令 `core.longPaths=true` 后清理成功，未修改全局配置。
- 同步删除仓库缓存中的两部作品旧验证日志、旧复核图片与专属测试字节码；其他作品使用的同名声音素材保留。
- 示例清单仅保留五部，图文动效清单为空，五类初始化仍受测试保护。其他五部示例的源码和材料未改动。
- 更新当前入口、架构、协作规则、规划与制作手册；历史档案移除专属内容并注明清理范围。两个历史 JSON 中保留的五部作品对象与改动前逐项一致。

## 定向验证

- 69 项通过：`tests/works/examples/test_examples_v9.py`、`test_example_hygiene.py`、`tests/standalone/test_scaffold.py`、`tests/common/test_doc_facts.py`、`test_guidance_routes.py`、`test_scene_design.py`。包括五部示例实际材料校验、可达依赖扫描与逐场构建，以及五类完整工程初始化。
- 6 项通过：`tests/common/test_font_coverage.py::TestShippedWorksAreCovered` 与 `tests/common/test_font_subsetting.py::TestSubsetting::test_all_three_works_can_be_subset_without_missing_glyphs`，覆盖清单直接调用方的字体检查。
- OpenSpec 变更严格校验、`sync_docs.py --check` 和 Git 空白检查通过。最终提交前再次检查更新文档的链接、JSON 和残余引用。
- 最终检查五部目录与测试登记完全一致；73 份修改文档的围栏和本次删除导致的链接失效检查通过，JSON 可解析、保留历史对象一致、暂存无二进制文件。活动文档链接测试在所有新增材料纳入 Git 后再次通过。
- 首次测试命令误写场景设计节点，收集时退出，未计入通过数；改为正确文件范围后通过。已有 `.pytest_cache` 写权限问题通过本次测试关闭缓存插件处理，未修改缓存权限或测试配置。

## 独立审查

独立只读子代理 `/root/review_removal` 审查差异、调用关系和清理边界。首轮发现历史档案中的混合段落误删、匿名专属残留、重复列表与表格/标题结构退化；修复后复核通过，无阻断项。评审未重复执行测试，通过数由主代理实际执行记录提供。

逻辑影响仅为移除随附作品与登记，不改变通用运行时、五类身份或渲染契约；无新增算法、依赖、计算或 I/O 成本。历史清理范围较广，人工语义复核仍有边界；本次未运行全仓回归、浏览器采集或重新渲染其余作品。

代码质量评分：96/100，独立复核扣分依据为历史材料清理的人工语义核验边界。
