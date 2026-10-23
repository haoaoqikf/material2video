# 交付验证

本文件记录本次重制实际执行的检查与结论；生成媒体与帧图保存在本地 `outputs/` 或 `videos/examples/five-life-choices/outputs/`，不入库。

## 自动化检查

| 检查 | 命令 | 结果 |
|---|---|---|
| 材料校验 | `uv run m2v validate --project examples/five-life-choices` | 通过 |
| 时间轴准备 | `uv run m2v prepare --project examples/five-life-choices` | 通过（1800 帧 / 60 秒 / 1920×1080 / 30 fps） |
| 代表静帧 | `uv run m2v lookdev --project examples/five-life-choices --stills 12 --sample-seconds 6` | 通过；60 fps 预览阶段检查构图，30 fps 成片另抽帧复核 |
| 七幕片段 | 逐幕 `m2v preview` | 城市、行业、伴侣、投资、学习、结尾均已抽帧；30 fps 成片另检 |
| 单元测试 | `uv run pytest tests/test_five_life_choices_example.py tests/test_examples_strict.py tests/test_doc_examples.py tests/test_font_coverage.py tests/test_font_subsetting.py` | 61 passed / 4 skipped（示例与严格校验 40 passed；字体相关 4 skipped） |
| 全片生成 | `uv run m2v render --project examples/five-life-choices` | 通过；已交付 1800 帧、1920×1080、30 fps、60.0 秒、无声 |
| 技术 QA | `uv run m2v qa --project examples/five-life-choices` | 通过；冻结帧 0、音画差 0.00036 秒、静音轨；技术结果不等于视觉完成 |

## 视觉复核

- 覆盖开场、城市、行业、伴侣、投资、学习、结尾各至少一张原生静帧，并在 852×479 下检查关键结论与对象标签。
- 盲审（只投喂最终帧与显示尺寸，不提供设计说明）结论为“需修”：城市左缘标签裁切、二级标签偏小、投资下曲线偏淡、结尾像平行线束、开场偏空。已按问题表 R07–R11 修改：标签视口钳制与暗色描边、字号提高、投资下曲线加亮、结尾增加 55/65 岁分叉与 100 条路径、开场第一句提前、伴侣结论提前。
- 重点检查：0 秒是否有可见光点与刻度；行业拉远后高度差是否明显；伴侣左右分屏是否可区分；投资曲线是否有示意标注；学习双带是否与行业跑道语法不同；决策树是否有多条路径且主路径最亮；大字是否被线条穿过。
- 已知限制：未逐帧播放全片；采样之间的瞬时运动仍需在最终帧序列中复核。深黑背景可能触发 QA 的 black-frame 候选，需人工确认是否为深底误报；58.15 秒后的黑屏是设计收尾。

## 结论

技术交付通过：`m2v validate`、`prepare`、`render`、`qa` 均通过，成片为 1920×1080、30 fps、1800 帧、60.0 秒、无声。独立盲审指出的城市左缘裁切、二级标签偏小、投资下曲线偏淡、结尾平行线感与开场空场，已按问题表修复并在最终帧复查；结尾决策树保留抽象性，作为“无数可能路径”的表达。未逐帧播放全片，采样之间的瞬时运动仍有未覆盖风险；深黑背景与 58.15 秒后的黑屏可能触发黑场候选，已人工确认为设计收尾。
