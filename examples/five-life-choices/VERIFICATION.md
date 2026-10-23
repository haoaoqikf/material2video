# 交付验证

本文件记录本次重制实际执行的检查与结论；生成媒体、候选、基线、评审包与帧图保存在本地 `videos/examples/five-life-choices/outputs/`，不入库。

## 自动化检查

| 检查 | 命令 | 结果 |
|---|---|---|
| 材料校验 | `uv run m2v validate --project examples/five-life-choices` | 通过 |
| 时间轴准备 | `uv run m2v prepare --project examples/five-life-choices` | 通过；preparedFingerprint `39deaed72d187513dd96a8b49dcae3f7ae1502baf64c268fb2fcc7c0e31146b7`，1800 帧 / 60 秒 / 1920×1080 / 30 fps / 无声 |
| 代表静帧 | `uv run m2v lookdev --project examples/five-life-choices --stills 12 --sample-seconds 6` | 通过；静帧与样片保存在 `outputs/lookdev/`，不作为导出门禁 |
| 关键窗口片段 | 逐段 `m2v preview`（开场、城市、行业、伴侣、投资、学习、结尾） | 已用于粗样与返工复查；预览短于全片，不参与交付门禁 |
| 几何行为测试 | `pnpm -C web test` | 92 passed；含路径表端点/零长度、连续距离采样、行业同世界速度与屏幕连续性、年龄平台期不冻结主体、连接端点、树父子关系与确定性 |
| Web 类型与构建 | `pnpm -C web typecheck` / `pnpm -C web build` | 通过 |
| 示例与文档测试 | `uv run pytest tests/test_five_life_choices_example.py tests/test_examples_strict.py tests/test_doc_examples.py tests/test_general_type.py tests/test_storyboard_copy.py tests/test_source_policy.py` | 通过 |
| 全片生成 | `uv run m2v render --project examples/five-life-choices` | 通过；已交付 1800 帧、1920×1080、30 fps、60.0 秒、无声；SHA-256 `273ef6b6eaca201f8eac1ef576749c6179a4917d4604dbfefe51c679272f69a7` |
| 技术 QA | `uv run m2v qa --project examples/five-life-choices` | 通过；冻结帧 0、重复帧 0、近静止比 0；无音轨，静音验收通过；音画差 0.00036 秒；字幕配色对比度 19.43；claims 覆盖检查通过（未评估可见性）。技术结果不等于视觉完成 |

### 性能对照

- 旧版：1800 帧，render 阶段 345.67 秒，约 0.192 秒/帧，total 664.98 秒。
- 重制版：1800 帧，render 阶段 374.87 秒，约 0.208 秒/帧，total 705.27 秒。
- 结论：重制版逐帧成本约高 8.5%，**不宣称性能提升**。原因是结尾增加了带父子关系的一、二级分支、行业/学习/结尾使用窄光带与更多标签；路径、树、城市楼体与网络均预计算，不在帧循环中重建整棵树。旧性能记录保留在 `outputs/remake-baseline/b01-20261024/video.performance.json`。

### 测试环境说明

- 全量 `uv run pytest` 在本机仍有 3 个与本重制无关的既有失败：`tests/test_lookdev_native.py::test_native_crossfade_and_subtitle_composite`、`tests/test_single_pass_delivery.py::test_renderer_repeated_full_export_calls_generate_once[general]`、`tests/test_single_pass_delivery.py::test_general_materializes_only_intersecting_scenes_and_offsets`。它们使用不含 `fps` 的合成 prepared 字典并触发 `KeyError: 'fps'`，未修改本片材料、场景或渲染链路；本片相关测试与上述命令均通过。
- `pytest` 缓存目录在当前 Windows 权限下无法写入，出现 `PytestCacheWarning` 与临时目录清理 `PermissionError`；不影响测试用例结果。

## 视觉复核

- 第一次导演审查（D01）在完整粗预演后、精制前执行，只投喂帧序列；结论为局部返工。必改项：行业拉远时主体出画、投资图终点回到更早年龄、结尾“持续学习”标签被收束句压住、部分等待段偏长。处理与证据见 `videos/examples/five-life-choices/outputs/visual-notes.md` 与[D01 报告](../../videos/examples/five-life-choices/outputs/review-pack/D01-rough-20261024/report.md)。
- 最终候选由两名隔离代理分别完成第二次全片导演审查（F01c，55 页逐页）与视觉/文案复核（F02c，55 页 + 852/393/200 宽），并与旧版做核心事件匿名比较（C02）。F01c/F02c 在 SHA `b638…` 上完成；最终交付 `273e…` 仅改动结尾标签淡出与收束句位置，已局部复查。F01c 唯一必改“收束后行业标签消失”通过“五标签一起淡出、收束前完成观察”消除；F02c 的 393 小字、copy-list 范围与行业/收益措辞作为覆盖限制或已处理项披露。报告与证据见 `outputs/visual-notes.md`。
- 手机基准：852×479 CSS 像素；另查 393 宽与 200 宽缩略图。关键结论在 852 宽下不低于 24 CSS px，对象标签不低于 10 CSS px。

## 已知限制

- 未实时播放全片，也未实际试听（成片无音轨）；以 QA 全片分页帧序列、关键帧、关键窗口 preview 与自动技术检查替代。采样之间的瞬时运动仍需在原始帧序列中复核。
- 去文字诊断未单独生成；不能用“文字可读”代替美术表现。该限制随最终报告披露。
- 深黑背景与结尾较暗画面可能触发 QA 的暗部候选；已对照设计确认，非空场或误删。
- 没有真实发布数据，不推算或声称跳出率、留存或惊艳程度。
- 投资曲线与行业高度差是叙事示意，不构成收益承诺、行业排名或固定人生时间表。
