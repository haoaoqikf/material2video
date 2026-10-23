# 验证与交付审查

## 范围

本轮只修改 Skill 创作指导、OpenSpec 规格、三个示例的 `DESIGN.md`、类型目录元数据与文档测试；没有修改运行时代码、分镜 JSON、场景源码、媒体、CLI 或既有成片。`src/m2v/types/catalog.json` 只改 `general.skillGuide` 文案，不改变类型行为、材料入口或渲染契约。

## 验证结果

- `python .agents/skills/material2video/scripts/sync_docs.py --check`：通过，类型清单与目录一致。
- `uv run pytest tests/test_doc_examples.py tests/test_examples_strict.py tests/test_five_life_choices_example.py tests/test_type_catalog.py`：73 项通过，0 失败（JUnit 统计）。
- `openspec validate integrate-visual-creative-direction --strict`：通过。
- `openspec validate --specs --strict`：24 项通过、2 项失败；失败为 `early-investing-compound-video` 与 `labor-rights-ten-events-video` 的既有 `## ADDED Requirements` 格式问题，与本次改动无关，`video-production-workflow` 主规格通过。
- 相对链接与锚点：本轮新增/修改链接均可解析；新文档的 16 个章节锚点可定位。`visual-review-rubric.md` 中 4 个既有示例路径（`visual-review/risk.mp4`、`before.jpg`、`after.jpg`、`video.mp4`）不是本轮新增，保持原样。
- `git diff --check`：通过，无空白错误。
- 全量 `uv run pytest`：首次运行出现 4 个失败，其中 1 个为 Windows 临时目录 `PermissionError`（四个失败用例用 `--basetemp` 单独复跑时，该用例通过），3 个为既有 `KeyError: 'fps'`；第二次全量复跑因含慢测试、超过 20 分钟被停止，未取得完整总数。目标测试与相关回归已单独覆盖，失败原因见下节。

## 既有问题与未验证范围

- 全量测试存在 3 个既有失败：`tests/test_lookdev_native.py::test_native_crossfade_and_subtitle_composite`、`tests/test_single_pass_delivery.py::test_renderer_repeated_full_export_calls_generate_once[general]` 与 `tests/test_single_pass_delivery.py::test_general_materializes_only_intersecting_scenes_and_offsets`。失败为 `KeyError: 'fps'`：提交 `bf16b3ca` 在 `capture.py` 增加 `prepared["fps"]`，但这两份测试的假 `prepared` 字典未同步；与本次文档改动无关，本轮不夹带修复。
- Windows 下 pytest 默认临时目录清理会产生 `PermissionError`；本次验证使用仓库内 `--basetemp` 目录规避，未改目录权限。
- 不重制视频，因此未验证新方法在真实成片中的感染力、连续观看感受、主观听感和平台表现；本轮只验证文档、规格、示例记录与测试一致性。
- 不处理进行中的 `replace-traffic-example-with-five-life-choices` 变更及其 `60 fps`／实际 `30 fps` 漂移；它是既有未收口变更。
- README 太阳系时长、示例 `render-rough.py` 仍传已移除的 `profile` 参数、`targetSeconds` 整数/浮点表述等既有漂移不在本轮修改范围。

## 审查结论与边界

视觉创意导演方法已接入方案确定、逐场设计、视觉复核、导演审查、示例与主规格：七段式为必答问题，不适用时记录原因与替代做法；文字预算按镜头/信息单元；关声可读只作设计诊断；禁止项是默认模板清单而非形式否决清单。未新增用户确认、评分、运行时字段或 CLI 门禁；金融/住宅专用契约未变；三个示例只补非重制回看，不改写既有交付结论。

## 全库规格检查

`openspec validate --specs --strict` 的 2 项既有失败与上一轮归档记录一致，属于这两个变更遗留的格式问题；本轮定向变更与 `video-production-workflow` 主规格严格校验通过。全库严格校验不能报告为全部通过。
