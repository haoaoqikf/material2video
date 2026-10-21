# 车向前，堵车为什么向后？

1080×1920 竖屏、60 fps、统一制作、目标 75 秒（实际 60～90 秒，当前准备产物约 60.9 秒）。
面向手机竖屏观众：先看车辆前进而低速区域后移，再倒回一次减速，解释响应如何传递，
最后用同一扰动的两种密度和“堵到前面却什么也没有”收束。

分镜采用 `topic` 输入，没有原文；完整旁白、画面与图表都来自作品自己的代码和
`assets/traffic/traffic.json` 中的离线示意轨迹。所有数值标注为示意，不是实测或交通预测。

## 时间线

| 场景ID | 时间 | 内容 | 画面推进 |
|---|---:|---|---|
| `opposite` | 0–12.1秒 | 车辆向前，拥堵却向后 | 局部车道跟随低速区域，蓝/红箭头对照两个方向 |
| `origin` | 12.1–20.5秒 | 倒回一次减速 | 缩略环路交代无瓶颈条件，局部车队逐车亮起制动灯 |
| `relay` | 20.5–32.2秒 | 慢的是区域，不是同一批车 | 环路全景，蓝框车辆持续前进，红色慢区不断换车 |
| `density` | 32.2–46.7秒 | 同样的减速，两种结果 | 上下直路共用一段采样，第 6 辆车速度曲线对照 |
| `return` | 46.7–60.9秒 | 堵到前面，却什么也没有 | 环路回看，收束句与唯一片尾 |

### 旁白与画面

| 旁白段 | 对应画面 |
|---|---|
| `h1` | 车队向前，红色低速区域向后移动 |
| `h2` | 「拥堵，向后」与反向箭头出现，抛出谁在倒退的问题 |
| `o1` | 环路交代无路口、无出口，局部车队逐车减速 |
| `r1` | 蓝框车辆前进，红色慢区换车 |
| `r2` | 「同一团拥堵，不同的车」点明区域而非车在后退 |
| `d1` | 高密度直路与第 6 辆车更大的速度跌幅 |
| `d2` | 低密度直路与较小的跌幅，标注预设模型与示意边界 |
| `e1` | 环路中低速区域继续向后传播 |
| `e2` | 「你可能刚刚穿过了一道波」与唯一片尾来源说明 |

无配乐与音效，只保留中文旁白和烧录字幕。观众可见文案不含仓库文件名、路径或制作
材料指引，署名与来源集中为唯一简短片尾。

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
uv run m2v qa --project examples/traffic-jam-wave
```

成片位于 `videos/examples/traffic-jam-wave/outputs/video.mp4`，生成媒体、准备音频与
复核图像均不入库。制作复核记录见 [交付验证](VERIFICATION.md)。

[视觉设计](DESIGN.md) · [机制与来源](SOURCES.md) · [交付验证](VERIFICATION.md)
