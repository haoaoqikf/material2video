# 删除两类视频的验证记录

## 删除范围

- 删除两个示例工程、两个空作品类型目录、两个站点作品页、四个专属站点媒体文件和一篇博客。
- 初始清点包含 14,907 个目录和 161,262 个文件，含 343 个 Git 跟踪文件。删除文件的逻辑体积为 5,598,418,517 字节。共享硬链接、Git 历史和文件系统分配使该值与卷可用空间的增量不同。
- 重新生成站点社交预览图，使用三部保留示例的画面。

## 验证结果

- 类型列表只返回图文动效、数据演化和三维空间。三类均从临时目录初始化并校验通过。两个旧身份在初始化、主项目校验和独立校验中均被拒绝。
- 两份 OpenSpec 提案严格校验通过。生成文档、站点卡片与本地链接、JSON 示范及类型目录镜像检查通过。
- 归档时核对 24 份增量规格、44 项要求，47 份主规格严格校验通过。对齐后的待实施提案再次通过严格校验。
- 测试按受影响文件筛选，排除常规批次的 media 和 slow，并单独运行两个直接受影响的 media 节点。
- 常规批次排除 16 项。Pytest 报告本地缓存目录写入权限警告，测试通过。此次验证覆盖示例材料和场景构建，完整成片导出超出定向测试范围。

| 测试文件 | 通过 | 失败 | 跳过 |
| --- | ---: | ---: | ---: |
| `tests/common/test_guidance_routes.py` | 29 | 0 | 0 |
| `tests/common/test_optional_visual_review.py` | 15 | 0 | 0 |
| `tests/common/test_scene_design.py` | 25 | 0 | 0 |
| `tests/common/test_subtitle_presentation.py` | 4 | 0 | 0 |
| `tests/common/test_three_type_contract.py` | 12 | 0 | 0 |
| `tests/common/test_tts_kokoro.py` | 9 | 0 | 0 |
| `tests/common/test_type_catalog.py` | 2 | 0 | 0 |
| `tests/standalone/test_scaffold.py` | 6 | 0 | 0 |
| `tests/standalone/test_tts_model_registry.py` | 5 | 0 | 0 |
| `tests/types/scene_film/test_cinematic_storyboard.py` | 26 | 0 | 0 |
| `tests/types/scene_film/test_general_frame_rate.py` | 34 | 0 | 0 |
| `tests/types/scene_film/test_sound_library.py` | 1 | 0 | 0 |
| `tests/types/scene_film/test_subtitle_size.py` | 22 | 0 | 0 |
| `tests/works/examples/test_example_hygiene.py` | 3 | 0 | 0 |
| `tests/works/examples/test_example_media.py` | 1 | 0 | 0 |
| `tests/works/examples/test_examples_v9.py` | 7 | 0 | 0 |
| 合计 | 201 | 0 | 0 |

## 保留的历史提及

既有历史文件按原文保留，另有本次归档的提案记录删除的身份。

- 本次归档的 `proposal.md`
- `docs/release-notes/v0.1.0.md`
- `openspec/changes/archive/2026-11-07-unify-five-video-types/proposal.md`
- `openspec/changes/archive/2026-11-07-unify-five-video-types/specs/five-video-types/spec.md`
- `openspec/changes/archive/2026-11-08-make-video-projects-standalone/baseline.json`
- `openspec/changes/archive/2026-11-08-make-video-projects-standalone/consumers.json`
- `openspec/changes/archive/2026-11-08-make-video-projects-standalone/implementation-examples.md`
- `openspec/changes/archive/2026-11-08-make-video-projects-standalone/implementation-management.md`
- `openspec/changes/archive/2026-11-08-make-video-projects-standalone/inventory.md`
- `openspec/changes/archive/2026-11-08-make-video-projects-standalone/specs/five-video-types/spec.md`
- `openspec/changes/archive/2026-11-08-make-video-projects-standalone/tasks.md`
- `openspec/changes/archive/2026-11-12-remove-obsolete-examples/proposal.md`
- `openspec/changes/archive/2026-11-12-remove-obsolete-examples/specs/standalone-video-projects/spec.md`
- `openspec/changes/archive/2026-11-13-add-kokoro-tts-backend/proposal.md`
- `openspec/changes/archive/2026-11-13-add-qwen3-tts-voice-clone-backend/design.md`
- `openspec/changes/archive/2026-11-13-add-qwen3-tts-voice-clone-backend/proposal.md`
- `openspec/changes/archive/2026-11-14-align-narrated-video-materials-and-kokoro/design.md`
- `openspec/changes/archive/2026-11-14-align-narrated-video-materials-and-kokoro/specs/speech-synthesis-backends/spec.md`
- `openspec/changes/archive/2026-11-14-align-narrated-video-materials-and-kokoro/verification.md`
- `openspec/changes/archive/2026-11-19-replace-compound-video-examples/specs/standalone-video-projects/spec.md`
- `openspec/changes/archive/2026-11-20-default-podcast-voice-for-all-narrated-videos/design.md`
- `openspec/changes/archive/2026-11-20-default-podcast-voice-for-all-narrated-videos/specs/assistant-voice-selection/spec.md`
- `openspec/changes/archive/2026-11-23-add-market-cap-portrait-example/specs/standalone-video-projects/spec.md`
