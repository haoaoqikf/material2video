# 复利

## 当前图片重设计

用户最新要求重新设计字体和背景、先看几张图片。本轮只比较暖纸宋体、钴蓝窄体、赤陶展厅三个静态候选，未选择新的全片基线，正式视频未改。实现和实际验证范围见[图片设计记录](design/editorial-samples.md)。以下完整制作记录属于此前在制工作，不代表本轮获准继续整片。

当前先重选字体与背景，按同一个30年结果比较三幅静态样图：暖白建筑、深蓝展厅、朱红编辑海报。用户最新要求“这种字体设计还是太一般了，背景也要改一下，重新设计，给我几张图片看看”，并要求先看图。本轮未修改正式入口、分镜或成片，也未继续制作完整视频。

## 当前网页原生样图

| 方向 | 字体与背景 |
|---|---|
| 暖白建筑 | 紧凑粗黑中文、统一无衬线数字；左文右物、暖白斜光与浅色台面 |
| 深蓝展厅 | 窄体中文标题、较轻数字；深蓝光域、冷银资本与金色收益 |
| 朱红编辑 | 中文和数字共用Noto Serif SC；红白分区与编辑式留白 |

均为真实DOM文字、Three.js圆片和CSS/SVG背景，不使用整图贴面。1整枚=1,000元，两组同单位、同尺度；结果为40枚与约174.5枚，分数面积及读数由既有数学模型派生。必要口径经过原生与393宽度检查，宋体按登记恢复，二进制不入库。

```powershell
uv run m2v sample capture --project examples/data-evolution/compound-interest --entry scenes/typography-directions.tsx --props design/trial-props.json --duration-seconds 0.3 --frame 1 --frame 4 --frame 7
```

9帧容器每3帧展示一张静态，既不是正式切换动效，也不验证真实停留、生成归队、声音或全片。旧C开发材料和旧独立记录保留，不能作为新样图或整片完成的依据。研究、采用边界和实际验证分别见[研究](RESEARCH.md)、[总设计](DESIGN.md)和[验证](VERIFICATION.md)。

## 重建

前十次圆片落点声明在 `storyboard.json` 的 `scenes[0].events`；场景和对应音效共用 `drop-1`～`drop-10`。修改一项事件帧后重新 prepare，即可共同移动该次落点与声音；落点按整数帧量化。此改动需重新生成与复核，历史成片验证不自动覆盖当前材料。

后续重制按[素材选择规范](../../../.agents/skills/material2video/references/visual-material-selection.md#视频优先与代码适用场景)判断：本片的数量、收益归队与再投入过程适合代码精确合成，无需为视频优先额外寻找外部素材；如新增真实外部画面，再执行视频优先、图片补位。本说明不改变现有作品与评审状态。

```powershell
uv run python examples/data-evolution/compound-interest/assets/fetch.py
uv run m2v validate --project examples/data-evolution/compound-interest
uv run m2v prepare --project examples/data-evolution/compound-interest
uv run m2v preview --project examples/data-evolution/compound-interest --start-seconds 8 --end-seconds 13
uv run m2v render --project examples/data-evolution/compound-interest
uv run m2v qa --project examples/data-evolution/compound-interest
```

成片位于 `examples/data-evolution/compound-interest/outputs/video.mp4`。目录与项目 ID 为 `compound-interest`；不提供旧五选择兼容入口。

- [制作设计与参考迁移](DESIGN.md)
- [数学口径、素材与声音来源](SOURCES.md)
- [验证与制作状态](VERIFICATION.md)

环境床与事件音按 [固定配方](assets/recipe.json) 恢复，已有摘要不符文件拒绝覆盖。视频、声音和评审图片为派生产物，不入库。最终制作结论以VERIFICATION绑定的文件版本为准。

本示例的画面组件与参数保存在本作品 `scenes/`，可独立重建。

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
