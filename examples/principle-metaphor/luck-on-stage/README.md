# 运气到底是什么

`dark-proof` 的第二部随附示例：41 秒、1920×1080、30 fps，无旁白和配乐，仅使用可恢复的原创事件音。圆形尝试标记串起尝试、记录与三柱比较；概率盘、九格面积和结论不使用小球。主线为：预期成功次数 = 尝试次数 × 单次成功概率。开场第三次命中直接成为记录起点；命中记录只作示意，不代表必然结果。

保留球的飞行以球心为光效头部，离散光滴沿球体历史轨迹下坠，减速和落点时收回；柱图的 1、3、9 阶段逐级变色。结果落点有分级闪释，公式结果最强。约 12.4–13.2 秒由记录末行接出短穿环，进入概率盘；结尾从尝试次数和单次成功概率两个独立因素引出唯一一次“多尝试，提高成功概率”。

与[复利示例](../../data-evolution/compound-connect/README.md)并列：本片用尝试动作引入问题，再由比例盘、三柱和面积逐项改变条件；复利片侧重数值从比喻进入表格、图表和公式。

## 重建

在仓库根执行：

```powershell
uv run python fonts/fetch.py
uv run python examples/principle-metaphor/luck-on-stage/assets/fetch.py
uv run m2v prepare --project examples/principle-metaphor/luck-on-stage
uv run m2v render --project examples/principle-metaphor/luck-on-stage --jobs 2
uv run m2v qa --project examples/principle-metaphor/luck-on-stage
```

源材料为 `project.json`、`storyboard.json`、`scenes/`、`assets/sound-recipe.json`、`assets/sound-checks.json`。音频按固定摘要恢复；生成媒体和 `outputs/` 不入库。设计与事实边界见 [DESIGN](DESIGN.md)、[SOURCES](SOURCES.md)、[SOUND](SOUND.md)，当前验证见 [VERIFICATION](VERIFICATION.md)。原 `videos/general/luck-on-stage` 的历史记录不作为本示例当前审核结论。

## 本地运行

本示例是独立工程，可以直接在作品目录运行，也可以由 `m2v` 委托同一入口：

```powershell
pnpm install --frozen-lockfile --ignore-workspace
uv sync --frozen
pnpm run setup --download --install-browser
pnpm run validate
pnpm run build
pnpm run render
```

字体缺失时把文件放入 `M2V_FONT_CACHE` 或 `fonts/.cache/`，再执行 `uv run python fonts/fetch.py`；摘要不符会拒绝覆盖。媒体与音效按 `assets/` 配方恢复。环境与恢复细节见[独立基础模板说明](../../../templates/standalone/README.md)。
