## Why

`styles/examples/` 下的两个风格示例（`vibe-night/fold`、`vibe-fable/pigeon`）由 `0ec7d18` 引入，README 声称「按已登记样片的选题与分镜重写」，但从未被独立对照验收过：

- `vibe-night-style` 主规格有「原创试制验收」条款（八项指标、并排基准、独立冷审），但它约束的是 `videos/` 下的原创试制作品，**不覆盖 `styles/examples/` 下的示例**。
- `vibe-fable-style` 主规格完全没有等价条款，所以 B 寓言的示例从未达到任何还原度标准即合入。

结果是两个示例与参考样片存在结构性差距而无人发现，直到并排目视与像素量测才暴露：

| 指标 | 参考 fold_C | 当前 fold | 参考 pigeon_B | 当前 pigeon |
|---|---|---|---|---|
| 平均饱和度 | 41.8–44.8% | 1.9–2.0% | 31.2–31.7% | 22.0–22.7% |
| 亮部（>160）占比 | 1.62–3.49% | 0.00–0.07% | 53.6–58.6% | 68.5–69.1% |
| 底色亮度中位 | 6.0–6.8 | 1.2–1.3 | 170–184 | 253.7（溢出） |

根因是结构性的：fold 把参考的「一台连续缩放摄影机」拆成了九个互不相干的固定机位；两套示例的主体都缺少参考的光照模型；参考的声画同步在本仓库完全缺失；氛围层被自身合成管线吃掉。

本次变更做三件事：把风格示例的还原度从「披露风险」改为**可验收**；新增共享相机原语供示例表达连续推拉；按证据修复两个示例。

## What Changes

- **规格**：`vibe-night-style` 与 `vibe-fable-style` 各新增一条「风格示例还原度验收」Requirement，要求示例产出八项指标对照、并排基准与独立冷审记录，缺项视为未完成。
- **共享原语**：新增 `web/src/code-scene/painter/camera.ts`，提供确定性的对数空间相机求值，供二维绘制层在固定世界坐标下做连续推拉；同步 `code-scene-runtime.md` 与 `painter/index.ts` 导出。
- **fold 重制**：九幕改用统一世界坐标与一条连续相机；珠子改径向渐变球体、红细胞改深红圆盘、折叠目标改六角格密团；补参考的顶部微型注释与字母行；修正章节标按全片帧计算的问题。
- **pigeon 重制**：补六镜六景别（全景 / 计时器特写 / 中景 / 近景 / 慢推 / 计时器前置）；鸽子改多层色块；修复米墙亮度溢出与 `feedPhase` 跨幕丢事件；启用已有的 `counter-row` 与 `rule-card`。
- **声音**：两套示例的 `storyboard.json` 增加 `soundtrack.effects`，复用既有合成音效库与无旁白音效通路，不再交付静音母带。
- **tokens**：`vibe-night` 增加 `colors.blood` 与 `colors.oxygen` 两个语义色，覆盖参考的「血」与「氧气」；同步 GUIDE 的色板表。
- **证据**：两个示例产出 `outputs/style-reference.md`（八项指标 + 并排 + 冷审），`lookdev` 代表帧覆盖每幕且与 `lookdev.json` 同源。
- **文档滞后修正**：`styles/vibe-night/GUIDE.md` 仍称「B 寓言不在包内」、`references/explainer-design.md` 只链 C 夜曲，一并修正。

## Capabilities

### New Capabilities

无。相机原语是 `react-code-scenes` 的增量导出，归入既有能力。

### Modified Capabilities

- `vibe-night-style`：新增「风格示例还原度验收」Requirement；色板增加 `blood` / `oxygen` 语义。
- `vibe-fable-style`：新增「风格示例还原度验收」Requirement。
- `react-code-scenes`：二维绘制层新增 `cameraAt` 相机求值原语。

## Impact

- 新增 `web/src/code-scene/painter/camera.ts` 与 `camera.test.ts`；`painter/index.ts` 增加导出。
- 修改 `styles/examples/vibe-night/fold/scenes/fold.tsx`、`styles/examples/vibe-fable/pigeon/scenes/pigeon.tsx` 及两份 `storyboard.json`；`styles/vibe-night/tokens.json`。
- 修改 `.agents/skills/material2video/references/code-scene-runtime.md`、`styles/vibe-night/GUIDE.md`、`references/explainer-design.md`、`styles/README.md`、两份示例 `README.md`。
- **不**新增视频类型、CLI 命令或分镜字段；**不**改变 `style.json` 结构、风格发现规则、制作门、审核轮次与导出门禁。
- **不**改动 `web/src/code-scene` 的录制契约与 `__M2V__` 接口；相机是纯绘制辅助函数。
- `examples/` 三个固定示例不受影响。
- 参考样片只作并排基准与量测来源，不进入成片、评审包以外的地方或风格包资产；示例 `outputs/` 仍被忽略。
