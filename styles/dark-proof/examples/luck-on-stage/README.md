# 运气到底是什么

`dark-proof` 的第二部随附示例：45 秒、1920×1080、30 fps，无旁白和配乐，仅使用可恢复的原创事件音。圆形上场标记串起尝试、记录与三柱比较；两处结论文字、单次概率盘与九格面积不使用小球，由字线、盘弧和面积边缘各自承接动作。主线为：预期成功次数 = 上场次数 × 单次成功概率。开场第三次命中直接成为记录起点；命中记录只作示意，不代表必然结果。

保留球的飞行带暖金光轨和受重力下坠的尾光，减速时收回；结果落点有分级闪释，约37秒的公式结果最强。14.4–15.2 秒由文字底线引出短穿环，接成概率盘。开场不使用白色长拖尾或漂浮地影，公式与字幕位于主光层前方。

与[复利示例](../compound-connect/README.md)并列：本片用尝试动作引入问题，再由比例盘、三柱和面积逐项改变条件；复利片侧重数值从比喻进入表格、图表和公式。

## 重建

在仓库根执行：

```powershell
uv run python fonts/fetch.py
uv run python styles/dark-proof/examples/luck-on-stage/assets/fetch.py
uv run m2v prepare --project styles/dark-proof/examples/luck-on-stage
uv run m2v render --project styles/dark-proof/examples/luck-on-stage --jobs 2
uv run m2v qa --project styles/dark-proof/examples/luck-on-stage
```

源材料为 `project.json`、`storyboard.json`、`scenes/`、`assets/sound-recipe.json`、`assets/sound-checks.json`。音频按固定摘要恢复；生成媒体和 `outputs/` 不入库。设计与事实边界见 [DESIGN](DESIGN.md)、[SOURCES](SOURCES.md)、[SOUND](SOUND.md)，当前验证见 [VERIFICATION](VERIFICATION.md)。原 `videos/general/luck-on-stage` 的历史记录不作为本示例当前审核结论。
