# 运气到底是什么

`dark-proof` 的第二部随附示例：45 秒、1920×1080、30 fps，无旁白和配乐，仅使用可恢复的原创事件音。水滴状尝试者把记录、次数、概率、柱图和面积乘法接成同一条论证：预期成功次数 = 上场次数 × 单次成功概率。开场第三次命中直接成为记录起点；命中记录只作示意，不代表必然结果。

与[复利示例](../compound-connect/README.md)并列：本片侧重一个角色持续引导和条件逐项改变；复利片侧重数值从比喻进入表格、图表和公式。

## 重建

在仓库根执行：

```powershell
uv run python fonts/fetch.py
uv run python styles/dark-proof/examples/luck-on-stage/assets/fetch.py
uv run m2v validate --project styles/dark-proof/examples/luck-on-stage
uv run m2v prepare --project styles/dark-proof/examples/luck-on-stage
uv run m2v render --project styles/dark-proof/examples/luck-on-stage --jobs 2
uv run m2v qa --project styles/dark-proof/examples/luck-on-stage
```

源材料为 `project.json`、`storyboard.json`、`scenes/`、`assets/sound-recipe.json`、`assets/sound-checks.json`。音频按固定摘要恢复；生成媒体和 `outputs/` 不入库。设计与事实边界见 [DESIGN](DESIGN.md)、[SOURCES](SOURCES.md)、[SOUND](SOUND.md)，当前验证见 [VERIFICATION](VERIFICATION.md)。原 `videos/general/luck-on-stage` 的历史记录不作为本示例当前审核结论。
