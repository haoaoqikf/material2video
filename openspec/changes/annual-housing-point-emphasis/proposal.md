## Why

年度住宅均价当前在年份之间插值，读数看起来像连续变化的实时价格，观众不容易把读数对应到每年的统计值。逐年到达时短暂停留并强调对应节点，可明确年度数据的离散属性。

## What Changes

- 年度均价动画到达每个年度点时停留约 0.5 秒，高亮该点并显示对应年份和价格。
- 同步更新时间轴行为规格、住宅均价制作说明和 README 当前能力描述。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `housing-timeseries`: 明确年度节点的停留、高亮和价格读数行为。

## Impact

- 影响 `HousingTimeSeries` 的帧映射与画面状态，以及对应 Remotion 测试。
- 不改变 `series.json` 材料结构、视频尺寸、帧率、时长、音轨或来源口径。
