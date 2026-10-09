## 1. OpenSpec 与材料契约

- [x] 1.1 完成滚动视窗行为规格、提案和技术设计；运行 `openspec validate rolling-window-financial-video --strict` 验证 OpenSpec 变更通过。
- [x] 1.2 扩展金融动画材料校验为必填 `visibleWindowMonths` 与 `valueScale=rolling-linear`，移除固定全历史 `valueRange` 要求；为缺字段、未知轴模式、无效月份数增加单元测试并运行 `uv run pytest tests/test_financial_video.py -q`。

## 2. 滚动视窗渲染

- [x] 2.1 实现可测的日历月窗口起点和退化纵轴范围计算，覆盖月底截短、闰年、起始日钳制、平坦价格序列及低值轴刻度精度。
- [x] 2.2 更新金融 composition，仅渲染可视窗口已到达点、窗口内事件标记、动态月份刻度和单一最新价格；新增边界、未来数据隐藏、价格/事件滚出及非交易日价格保持测试，并通过 `pnpm --dir web test -- FinancialTimeSeries` 与 `pnpm --dir web typecheck`。
- [x] 2.3 更新金融视频制作手册，明确默认三个月日历窗口、60 秒 NVIDIA 编排参考、滚动事件标记与窗口自适应纵轴验收；检查相对链接及 JSON 片段一致性。

## 3. NVIDIA 成片重制与交付

- [x] 3.1 使用公开免费来源刷新 NVIDIA 全部日线至最近已完成 NASDAQ 交易日，重新核验交易日覆盖及来源快照哈希，沿用已核实事件并生成 60 秒三个月滚动材料；运行金融材料 validator。
- [x] 3.2 渲染完整静音预演并抽查开头、日期窗口移动、至少两个事件及终帧；确认最新价格日期、动态刻度、曲线/事件窗口无越界或遮挡，修正后再验。
- [x] 3.3 导出正式 MP4，核验 1920×1080、30 fps、60 秒、1800 帧及无音频流；检查 Git 暂存只有代码、测试、规范和 OpenSpec 文件，提交实现。
- [ ] 3.4 按项目 OpenSpec 流程将增量规格同步至主规格并提交；确认 NVIDIA 行情与媒体仍被 Git 忽略。任务完成后自动归档变更并提交归档结果。
