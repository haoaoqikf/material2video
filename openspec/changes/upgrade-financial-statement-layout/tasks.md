## 1. 规格与文档

- [x] 1.1 更新 `.agents/skills/material2video/references/financial-timeseries-video.md` 的布局、字号、颜色、分隔线、收束区与开场编排描述，并注明其他作品不在本轮重新生成。
- [x] 1.2 更新 `README.md` 的金融类型当前能力描述；检查受影响的相对链接与 JSON 示例。

## 2. 前端画面实现

- [x] 2.1 在 `design.ts` 增加 profile 分隔线色，并保持 accent 仅进入背景；同步设计测试。
- [x] 2.2 在 `chart.tsx` 更新暖近黑背景、正文与规则色常量；在 `overlay.tsx` 增加收束区账目、两条分隔线、等宽数字与容量检查。
- [x] 2.3 在 `FinancialTimeSeries.tsx` 重排内容层并实现开场编排；保持曲线、坐标、端点与裁剪探针不变。
- [x] 2.4 更新前端测试中的坐标、字号、颜色与标记断言，新增收束区并排、分隔线、动态布局键和开场运动测试。

## 3. 苹果作品再生成

- [x] 3.1 将苹果作品 `request.json` 的 `design.profile` 改为 `ledger`，保留本金、年份、日期范围与 `titleMode`/`personality`。
- [x] 3.2 运行 `uv run m2v validate`、`prepare` 和 `render`，只重新生成 `videos/financial-timeseries/apple-since-2007`；核对 1080×1920、30 fps、60 秒、无音轨与自动验收通过。
- [x] 3.3 抽取开场、中段、终幕与 360×640 缩放帧，按 Frontend Design 与 Motion Design 做实际画面批评；把结论与同一帧前后对照写入作品 `DESIGN.md`，不新增门禁。

## 4. 验证与交付

- [x] 4.1 运行金融相关 Python 测试、前端测试与构建；确认只暂存本变更的代码、文档与 OpenSpec 材料。
- [x] 4.2 运行 OpenSpec 严格校验，提交实施结果；同步 `openspec/specs/` 主规格并归档变更。
