# 一座城市，为什么会堵车？

1080×1920 竖屏、60 fps、standard、目标 75 秒（实际 60～90 秒，当前准备产物约 66.6 秒）。
面向手机竖屏观众：先看一段没有事故的走走停停，再拉远到一条没有红绿灯和出口的环路，
最后把「车辆向前、低速区域向后」与两种车流密度的对照说清楚。

分镜采用 `topic` 输入，没有原文；完整旁白、画面与图表都来自作品自己的代码和
`assets/traffic/traffic.json` 中的离线示意轨迹。所有数值标注为示意，不是实测或交通预测。

## 时间线

| 场景ID | 时间 | 内容 | 画面推进 |
|---|---:|---|---|
| `jam-open` | 0–6.5秒 | 没有事故，车流却走走停停 | 局部车道跟随低速区域，制动灯明灭 |
| `loop-overview` | 6.5–16.6秒 | 拉远到闭合环路 | 从顶部连续拉远，交代无红绿灯、无出口、无事故 |
| `brake-zoom` | 16.6–24.4秒 | 回放到 1 号车的一次刹车 | 缩略环路 + 局部车距 + 速度条 |
| `wave-back` | 24.4–39.5秒 | 车辆向前，低速区域向后 | 红带跟随慢区，蓝色虚线箭头指向后方 |
| `density-compare` | 39.5–53.5秒 | 同一扰动下的两种密度 | 上下直路同一段 + 第 6 辆车速度曲线 |
| `jam-close` | 53.5–66.6秒 | 没有事故也会堵车 | 环路回看，收束句与唯一片尾 |

### 旁白与画面

| 旁白段 | 对应画面 |
|---|---|
| `jam-open-0` | 开场车道与「没有事故 / 没有封路 / 没有红绿灯」标签 |
| `loop-overview-0` | 拉远后的完整环路与车辆编号 |
| `brake-zoom-0` | 1 号车减速、局部车距和速度条 |
| `wave-back-0` | 后车依次亮起制动灯 |
| `wave-back-1` | 蓝色传播箭头出现，图例写明两个方向 |
| `density-compare-0` | 高密度直路与放大的响应曲线 |
| `density-compare-1` | 低密度直路与逐渐恢复的曲线 |
| `jam-close-0` | 收束句「拥堵更像一种向后传播的波」 |
| `jam-close-1` | 片尾示意声明与机制来源 |

无配乐；仅在 1 号车减速与方向揭示时使用两声低增益提示音。观众可见文案不含仓库
文件名、路径或制作材料指引，署名与来源集中为唯一简短片尾。

## 轨迹与数据

`assets/traffic/generate.py` 离线生成 `assets/traffic/traffic.json`：椭圆环路按累计弧长
采样，车辆位置、速度与制动状态以 10 Hz 关键帧保存；两组共享道路、初速与首车扰动的
幅度和持续时间，只有车辆数量与由此产生的响应不同。生成脚本会拒绝负速度、穿车和
低速区域不向后移动的结果；`tests/test_traffic_example.py` 重复生成并逐值比对仓库文件。

画面与 ECharts 图表都从同一份采样插值，不存在另一套手工曲线。

## 重建与验收

```powershell
uv run python examples/traffic-jam-wave/assets/traffic/generate.py
uv run m2v validate --project examples/traffic-jam-wave
uv run m2v prepare --project examples/traffic-jam-wave
uv run m2v preview --project examples/traffic-jam-wave --start-seconds 0 --end-seconds 10
uv run m2v render --project examples/traffic-jam-wave
uv run m2v qa --project examples/traffic-jam-wave --profile standard
```

成片位于 `videos/examples/traffic-jam-wave/outputs/video.mp4`，生成媒体、准备音频与
复核图像均不入库。制作复核记录见 [交付验证](VERIFICATION.md)。

[视觉设计](DESIGN.md) · [机制与来源](SOURCES.md) · [交付验证](VERIFICATION.md)
