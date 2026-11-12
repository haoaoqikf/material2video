## Why

- `vibe-night-style` 主规格有「原创试制验收」条款（八项指标、并排基准、独立冷审），但它约束的是 `videos/` 下的原创试制作品，**不覆盖 `styles/examples/` 下的示例**。
- `vibe-fable-style` 主规格完全没有等价条款，所以 B 寓言的示例从未达到任何还原度标准即合入。

## What Changes

- **规格**：`vibe-night-style` 与 `vibe-fable-style` 各新增一条「风格示例还原度验收」Requirement，要求示例产出八项指标对照、并排基准与独立冷审记录，缺项视为未完成。
- **共享原语**：新增 `web/src/code-scene/painter/camera.ts`，提供确定性的对数空间相机求值，供二维绘制层在固定世界坐标下做连续推拉；同步 `code-scene-runtime.md` 与 `painter/index.ts` 导出。
- **文档滞后修正**：`styles/vibe-night/GUIDE.md` 仍称「B 寓言不在包内」、`references/explainer-design.md` 只链 C 夜曲，一并修正。

## Capabilities

### New Capabilities

无。相机原语是 `react-code-scenes` 的增量导出，归入既有能力。

### Modified Capabilities

- `vibe-night-style`：新增「风格示例还原度验收」Requirement。
- `vibe-fable-style`：新增「风格示例还原度验收」Requirement。
- `react-code-scenes`：二维绘制层新增 `cameraAt` 相机求值原语。

## Impact

- 新增 `web/src/code-scene/painter/camera.ts` 与 `camera.test.ts`；`painter/index.ts` 增加导出。
- **不**新增视频类型、CLI 命令或分镜字段；**不**改变 `style.json` 结构、风格发现规则、制作门、审核轮次与导出门禁。
- **不**改动 `web/src/code-scene` 的录制契约与 `__M2V__` 接口；相机是纯绘制辅助函数。
- `examples/` 三个固定示例不受影响。
- 参考样片只作并排基准与量测来源，不进入成片、评审包以外的地方或风格包资产；示例 `outputs/` 仍被忽略。

> 2026-11-12 内容清理：已删除用户指定作品的专属内容；本档案仅保留其余历史范围，不代表本轮重新验证。
