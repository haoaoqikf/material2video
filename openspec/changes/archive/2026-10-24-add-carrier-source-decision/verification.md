# 验证与交付审查

## 范围

本轮只修改 Skill 创作指导、逐场设计模板、媒体说明、三个示例的 `DESIGN.md` 非重制记录与文档测试；没有修改运行时代码、分镜 JSON、场景源码、媒体、CLI 或既有成片。外部素材仍只经 `assets import` 导入并按 `useMediaAsset(id)` 取用，代码画面仍是 `scenes/` 下的 TSX。

## 验证结果

- `uv run pytest tests/test_doc_examples.py tests/test_examples_strict.py tests/test_five_life_choices_example.py tests/test_type_catalog.py`：73 项通过，0 失败（JUnit 统计）。
- `python .agents/skills/material2video/scripts/sync_docs.py --check`：通过，类型清单与目录一致。
- `openspec validate add-carrier-source-decision --strict`：通过。
- 本轮新增/修改文档的相对链接检查：通过；`visual-creative-direction.md` 新增的「载体来源决策」章节锚点可定位。
- `git diff --check`：通过，无空白错误。

## 既有问题与未验证范围

- 全量测试仍存在与本轮无关的既有失败：`tests/test_lookdev_native.py` 与 `tests/test_single_pass_delivery.py` 的假 `prepared` 字典缺少 `fps`，由提交 `bf16b3ca` 引入；本轮不夹带修复。
- `openspec validate --specs --strict` 仍有 2 项既有格式失败：`early-investing-compound-video` 与 `labor-rights-ten-events-video`；`video-production-workflow` 主规格通过。全库严格校验不能报告为全部通过。
- Windows 下 pytest 默认临时目录清理可能产生 `PermissionError`；本次使用 `--basetemp` 规避。
- 不重制视频，因此未验证新决策在真实制作中的素材可得性、许可谈判、混合边界识别与观众理解；本轮只验证文档、模板、示例记录与测试一致性。
- 不处理进行中的 `replace-traffic-example-with-five-life-choices` 变更及既有文档/脚本漂移。

## 审查结论与边界

载体来源决策已接入方案确定、候选比较、七段式、逐场设计表与媒体说明：整体定证据体制与真实／示意边界，逐场定实例；代码-only、archive-only 与混合都成立，但必须记录理由与边界。硬边界保留：图库不得冒充真实事件／人物／地点，代码不得伪造证据，许可未知阻断成片。未新增运行时字段、CLI 门禁、评分或用户确认；金融/住宅专用契约未变；三个示例只补非重制回看。

## 提交与归档

实施提交为 `ab1e2a9`。新增要求已同步到 `openspec/specs/video-production-workflow/spec.md`，主规格与变更的 `--strict` 校验通过；变更按 `2026-10-24-add-carrier-source-decision` 归档，归档提交见后续仓库历史。
