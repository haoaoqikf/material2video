## 1. 材料与规范

- [x] 1.1 `materials.py` 增加可选 `design` 块校验：profile/titleMode/personality 枚举、accent #RRGGBB、拒绝与 profit/loss 相同。
- [x] 1.2 更新 `financial-timeseries-video.md`：两行 masthead、design 块、accent 边界、运动分层、纵轴 24px。
- [x] 1.3 OpenSpec 规格同步：可选 design、主体优先标题、profile/accent、运动要求、纵轴 24px。

## 2. 前端设计系统

- [x] 2.1 新增 `web/src/types/financial/design.ts`：类型、PROFILES、resolveDesign、withAlpha。
- [x] 2.2 `chart.tsx`：request.design 类型、标题字号、共享 `easeInOutCubic`、`firstFrameForDate`。
- [x] 2.3 `overlay.tsx`：subject/premise 两行 masthead、titleMode、contentLayoutKey、底部说明。
- [x] 2.4 `FinancialTimeSeries.tsx`：profile/accent 背景、开场编排、坐标/年份/端点/光晕运动。
- [x] 2.5 更新前端测试：标题模式、profile、accent 边界、motion 时序、360×640 布局。

## 3. Python 测试

- [x] 3.1 `test_financial_materials.py` 增加 design 校验用例：合法、缺省、非法枚举、非法 accent、与红绿相同。
- [x] 3.2 确认 `test_financial_plan.py`、`test_financial_render.py` 不需要改计划/渲染契约。

## 4. Apple 试点

- [x] 4.1 Apple request 增加 `design` 块。
- [x] 4.2 `validate` / `prepare` / `render`。
- [x] 4.3 抽 0.5s、1s、30s、59s 帧，按两个 skill 复核；记录到作品 DESIGN.md/visual-notes。

## 5. Google IPO 新片

- [x] 5.1 `m2v init --type financial-timeseries --project videos/financial-timeseries/google-since-ipo`。
- [x] 5.2 抓取 Yahoo GOOGL 原始快照，生成 request/prices（5586 个交易日、两次拆股、SHA、来源）。
- [x] 5.3 `financial plan` 生成 60 秒 v8 计划。
- [x] 5.4 `validate` / `prepare` / `render`；抽帧检查 360×640、开场、扩展、结尾。

## 6. 验证与提交

- [x] 6.1 `uv run pytest`、`pnpm -C web test`、`pnpm -C web build`。
- [x] 6.2 `sync_docs.py --check`、`openspec validate --all`。
- [x] 6.3 确认其他四条作品 outputs 未改动；`videos/` 不入库。
- [x] 6.4 提交代码、测试、文档、OpenSpec；归档并同步主规格。
