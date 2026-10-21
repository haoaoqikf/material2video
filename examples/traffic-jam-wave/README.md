# 堵了半天，前面为什么什么都没有？

1080×1920 竖屏、60 fps、统一制作。时长按内容、实测旁白与观察时间确定，不设固定秒数；
本轮准备产物 70.98 秒、4259 帧。
面向手机竖屏观众：先经历「堵了半天，开到前面却什么都没有」，再看车流向前、低速区域向后，
从一次轻刹车追到环路换车，最后回到驶出拥堵却不见障碍的经历。

分镜采用 `topic` 输入，没有原文；完整旁白、画面与图表都来自作品自己的代码和
`assets/traffic/traffic.json` 中的离线示意轨迹。所有数值标注为示意，不是实测或交通预测。

## 场景

| 场景ID | 内容 | 画面推进 |
|---|---|---|
| `empty` | 堵了半天，前面什么都没有 | 蓝框车驶出红色慢区，前方道路通畅；后视镜里仍是一片红灯 |
| `rewind` | 拥堵在往后跑 | 回放标记出现，红色慢区逆着车流向后移动，青/红箭头对照两个方向 |
| `brake` | 从一次轻刹车开始 | 局部车队逐车亮起制动灯，编号与车距标注来自同一轨迹 |
| `relay` | 换的是车，不是路 | 无瓶颈环路全景，蓝框车持续前进，红色慢区不断换车 |
| `density` | 同样的刹车，两种结果 | 先出现上下两条直路与密度差异，再出现第 6 辆车速度曲线作补充对照 |
| `return` | 你穿过了一道波 | 回到空路与后视镜，结论句与唯一片尾来源说明，无来源口播 |

### 旁白与画面

| 旁白段 | 对应画面 |
|---|---|
| `e1` | 车 8 号驶出红色慢区，前方道路通畅 |
| `e2` | 后视镜 inset 出现，红灯仍留在身后 |
| `w1` | 回放标记与固定道路参照，红区开始向后移动 |
| `w2` | 青色「车流向前」与红色「慢区向后」箭头出现 |
| `b1` | 局部放大车队，反应时间线与车距标注 |
| `b2` | 制动灯沿途逐车亮起，红色慢区覆盖受影响车辆 |
| `l1` | 环路全景，无路口、出口与事故 |
| `l2` | 蓝框车前进，红色慢区换到后车 |
| `l3` | 环心结论「同一团拥堵，不同的车」 |
| `d1` | 先出现两条直路的密度差异，随后速度曲线淡入 |
| `d2` | 曲线完整呈现，「补充解释」与示意边界保留 |
| `f1` | 回到空路，车继续向前 |
| `f2` | 后视镜放大，红区退向身后 |

无配乐，只保留中文旁白、烧录字幕与两次低增益内置提示音（回放与首次刹车）。观众可见
文案不含仓库文件名、路径或制作材料指引，署名与来源集中为唯一简短片尾；片尾来源只以画面
声明出现，不再口播。本轮停顿节奏采用微调后的逗号 0.22、句号 0.65、段末 0.80、引子 0.12
秒，字幕峰值 8.28 字/秒，超限 0。

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
复核图像均不入库。逐场验收、传播判断与制作复核记录见 [交付验证](VERIFICATION.md) 及
交付目录 `videos/examples/traffic-jam-wave/outputs/` 中的 `visual-notes.md`、`reach-potential-report.md`。

[视觉设计](DESIGN.md) · [机制与来源](SOURCES.md) · [交付验证](VERIFICATION.md)
