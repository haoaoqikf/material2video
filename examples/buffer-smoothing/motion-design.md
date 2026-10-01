# 对象动作设计

全片一个 world（`buffer-world`，renderer `code`，模块 `water-tank`）：入口管道 `inlet`、水箱 `tank`、出口 `outlet`、溢出口 `overflow` 四个对象从首帧到最后帧都在场上，阶段只改变输入条件与状态。动作读取全局 `beats.plan` 与剧本声明的对象状态（`stateTracks`），不使用挂钟或随机数，随机寻帧与顺序播放得到同一画面。

## 状态轨道（剧本声明，画面只读）

| 轨道 | 目标·属性 | 绑定 | 到 | 插值 |
|---|---|---|---|---|
| `tank-focus` | `tank`·`state` | beat-2 | `focus` | step-end |
| `tank-fill` | `tank`·`value` | beat-2 | 0.52 | ease-out |
| `tank-rise` | `tank`·`value` | beat-3 | 0.95 | ease-out |
| `tank-fall` | `tank`·`value` | beat-4 | 0.65 | ease-in-out |
| `tank-surge` | `tank`·`value` | beat-5 | 1.00 | linear |
| `tank-settle` | `tank`·`value` | beat-6 | 0.45 | ease-in-out |
| `outlet-steady` | `outlet`·`state` | beat-4 | `focus` | step-end |
| `overflow-show` | `overflow`·`visible` | beat-5 | true | step-end |
| `overflow-hide` | `overflow`·`visible` | overload·settle | false | step-end |
| `tank-done` | `tank`·`state` | beat-6 | `done` | step-end |

`step-end` 语义是「在绑定区间末尾生效」：`overflow` 因此在高潮幕末段（f995–f1022）才可见，正好接在字幕「最后溢出。」之后。水位（`tank.value`）是同一车道上的连续轨道，后一段从上一段的终值接着走，所以全片水位是 0 → 0.52 → 0.95 → 0.65 → 1.00 → 0.45 一条不回退的曲线。

## 逐幕动作

| 幕 | beat | 对象动作 | 镜头 | 结果 |
|---|---|---|---|---|
| pulse | beat-1 f3–f287 | 入口水滴成串推进又停顿（疏密由 `sin(frame/8)` 驱动），出口水滴同步起伏；水箱空置置灰、直通旁路高亮 | `hold` 1.000 | 没有缓冲时波动原样传到出口 |
| buffer | beat-2 f319–f499 | 水流改走水箱，水位由 0 升到 0.52，旁路置灰 | `push-in` 到 1.042 | 存储把输入与输出分开 |
| smooth | beat-3 f531–f624 / beat-4 f640–f788 | 水位升到 0.95 再回落到 0.65；出口水滴间隔一致并出现「输出保持平稳」基线 | 右移 22.4px → 回到中点 | 存量换来出口平稳 |
| overload | beat-5 f821–f995 | 水位线性升到 1.00；f995 溢出口淡入并落下水滴 | `push-in` 到 1.120 | 有限容量不能解决长期超载 |
| conclusion | beat-6 f1027–f1231 | 水位回落到 0.45，溢出口关闭，水箱状态转到 `done` | `pull-out` 回到 1.000 | 缓冲换时间，不换处理能力 |

## 示意边界

水箱容量与水滴数量都是示意量，画面不出现容量、吞吐或百分比读数；`capacity` 类数值只作为形状比例，不代表真实设备参数。溢出口表达「存储用尽」，不表达具体溢出速率。
