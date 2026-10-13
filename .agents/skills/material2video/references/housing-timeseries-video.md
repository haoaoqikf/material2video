# 年度住宅均价视频

`housing-timeseries` 专用于按年度展示住宅商品房平均销售价格，与股票金融类型分开，不包含投资计算、二手住宅均价、月度价格指数、旁白或字幕。

## 工作流

```powershell
uv run m2v init --type housing-timeseries --project <slug>
# 编辑 series.json，放入连续年份、住宅销售额/面积、均价、来源和口径说明
uv run m2v validate --project videos/housing-timeseries/<slug>
uv run m2v prepare --project videos/housing-timeseries/<slug>
uv run m2v preview --project videos/housing-timeseries/<slug>
# 查看完整预演，按 outputs/review.json 的全部准则填写评审结论
uv run m2v review-template --project videos/housing-timeseries/<slug>
uv run m2v review --project videos/housing-timeseries/<slug>
uv run m2v render --project videos/housing-timeseries/<slug>
```

作品材料与成片属于内容，应放在仓库外内容根或被忽略的 `videos/<type>/<slug>/`；不得提交房价工作材料和生成媒体。

## `series.json` 契约

- 顶层 `schemaVersion` 为 1；必须提供城市、指标、单位、来源、统计口径、计算精度提示及至少两个连续年度点。
- 每个点保存 `year`、`salesAreaWanSquareMeters`（万平方米）、`salesAmountYiYuan`（亿元）和 `averagePriceYuanPerSquareMeter`（元/平方米）。均价按 `salesAmountYiYuan / salesAreaWanSquareMeters * 10000` 计算，保留两位小数并经校验复算。
- 面积、金额和均价必须为有限正数；来源必须是无内嵌凭据的 HTTPS URL；年份不可缺失或重复；统计口径断点必须指向序列中的年份。
- 公开汇总表中的销售面积、金额精度有限，按其公布值计算的均价是近似值。应在材料和画面中明确这一点，不展示超出来源精度的意义。

## 画面规则

画布为 1080×1920、30 fps。默认 60 秒由 1 秒开场、57 秒逐年推进、2 秒静止终幕组成；曲线只揭示已到达年份，当前年份和约整元的均价同步更新。纵轴依据当前已揭示数据确定，不提前透露未来极值。

统计口径断点通过材料 `breakpoints` 声明。郑州序列标注 2005 年起销售面积和销售额统计采用新口径；底部保留计算方法、原始数据精度限制、来源机构及年份范围。完整来源 URL 和各年原始面积/金额留在作品材料中。成片不得带音轨或字幕轨。
