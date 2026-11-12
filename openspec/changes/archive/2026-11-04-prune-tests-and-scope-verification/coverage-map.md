# 删除与保留覆盖

删除的文案/配置副本不再作为产品行为要求；其余重复项由下表列出的行为测试承接。以下均为当前仓库测试位置。

| 删除/合并范围 | 保留覆盖与理由 |
| --- | --- |
| `test_project_skills.py` 的固定词句、标题、旧 aesthetic 文件不存在、每份指南复制四条链接 | 保留 pinned/license；`test_guidance_routes.py` 验证路由、入口、链接、JSON 和预算；`test_doc_facts.py` 通查受控 Markdown 链接和锚点 |
| 整个 `test_doc_examples.py`（旧文档不存在、固定文件列表、手册必须包含指定文件名、恢复命令字面量） | 路由与通用链接检查负责可达性；`test_example_media.py::test_fixed_example_recipes_match_registered_assets` 负责恢复配方与真实登记一致性 |
| `test_doc_facts.py::test_live_docs_have_no_known_stale_facts` 黑名单 | 当前契约由路由、目录、同步投影与 OpenSpec 校验维护；不锁死正文用词。链接锚点复用支持 HTML alias 的既有解析器 |
| `test_cinematic_media_checks.py` 的已移除 lookdev 符号/旧 approve 参数断言 | 不继续锁定历史删除清单；当前命令与参数由 CLI 通用解析及对应现行行为测试维护 |
| 三个风格文件的颜色/字号/粒子/版本/组件固定集合副本 | 清单由 `styles.load_style` 与 `test_styles.py::test_invalid_package` 验证；保留字体来源/许可、旁白特有约束、真实构建与逐帧确定性 |
| 三份 `test_selection_rejects_wrong_type_and_frame` 与指纹变更副本，两份示例指纹隔离副本 | `test_styles.py::test_selection_and_compatibility`、`test_prepared_style_dependency`（GUIDE/tokens/component/asset）、`test_example_tree_is_pruned_without_reading_or_hashing` 与符号链接/共享边界测试 |
| 三份组件静态安全扫描实现 | 合并为 `test_styles.py::test_shipped_components_are_frame_driven_and_self_contained`，遍历所有正式包的实际组件，不依赖字体二进制 |
| dark-proof 固定示例时长/帧数/字幕数量/数学文案、包内题材黑名单 | 作品内容由自身制作验收负责；保留示例 `explainer.validate`、媒体配方、版本控制卫生；通用事件/字幕/全局时间基行为由 `test_scene_events.py`、`test_capture_clock.py`、`test_code_scenes.py` 及 general 分镜校验覆盖 |
| general 独立并行整片测试、effect 整片参数、`test_general_partial_check_and_single_full_render` | 保留 none/narration 两个最小真实成片；none 合并 jobs=2、输出帧数、音轨与重复交付。effect 由 `test_article_sound.py::test_prepare_mixes_builtin_and_local_effects` 覆盖真实混音；`test_single_pass_delivery.py` 保留局部物化/偏移、缓存、输入变动、并发、旧成片保护与 sidecar 回滚 |
| `test_article_sound.py::test_local_soundtrack_fixture_is_declared_and_usable` 重复校验 | `test_validate_accepts_music_and_effects` 覆盖本地音床/内置与本地音效，真实混音独立保留；校验参数共享两份 0.05 秒 WAV 并复制，替代反复合成 8 秒 WAV |
| `test_production_gates.py::test_animatic_real_encode_and_duration` | 并入 `test_production_timing.py::test_animatic_limits_scope_and_maps_original_windows`，同时验证真实帧数、秒数、局部范围、上下文映射与 nonDelivery |
| 审核报告夹具反复调用 ffmpeg 造图/净化 | Pillow 造图，绑定单元测试只替换媒体转换；保留单个 `test_review_package_removes_image_metadata` 真实验证净化、摘要、匿名命名和源文件不改。独立调用、隔离、覆盖、同轮对照、过期及 issue 关闭逻辑仍使用真实导入器 |
| 不可达 rough 审核分支 | G5 当前 internal，不接受新 rough 独立报告；`test_policy_derives_rounds_from_risks_only` 保留 rough=0 公开统计，历史日志读取不变；覆盖不足断言改测仍有效的 final |

## 成本边界

六个混合模块改为实际媒体节点标记；另把真正启动 Node 构建的嵌套示例边界节点归入 slow。QA 五项测试共享一组视频/音频（各自复制后使用），从九次相同媒体生成降为两次。路径选择不再意外放开慢测，六个临时小套件收集测试保护文件、目录、参数化节点、混合目标、标记与 full 覆盖行为；其中 `--full` 只收集临时四项测试，不执行仓库全集。

字体未恢复时仅跳过依赖该二进制的夜曲测试；通用字幕与旁白互斥测试仍在默认层执行。媒体恢复、路径越界、摘要失效、确定性、旧成片保护和独立 issue 关闭测试未删除。

> 2026-11-12 内容清理：已删除用户指定作品的专属内容；本档案仅保留其余历史范围，不代表本轮重新验证。
