# 声音设计

示例无旁白，声音承担节奏推进与事件同步。60 秒原创程序化配乐与事件音均由 `assets/synthesize.py` 确定性生成，24 kHz PCM16 单声道、CC0-1.0；`assets/recipe.json` 固定摘要、时长、采样率与声道。

## 角色与事件

| 角色 | recipe id | storyboard `sourceRef` | 事件 | 帧 | 作用 |
|---|---|---|---|---:|---|
| 配乐 | `bed` | `assets/media/bed.wav` | — | 0–1800 | 112 BPM 程序化 score：低频脉冲、反拍 tick、和声垫、8 分 hat、riser 与 impact；41.0 秒硬切 duck 0.4 秒，58–60 秒收束 |
| 第一刀 | `fold` | `assets/media/fold.wav` | `first-cut` | 20 | 凿子入木的短促切削 |
| 切深刻度 | `grain` | `assets/media/grain.wav` | `depth-8` | 132 | 深度尺落定的细粒点击 |
| 第一滴 | `grain` | `assets/media/grain.wav` | `day-1` | 186 | 水滴落在石板上的起点 |
| 第一百滴 | `moon` | `assets/media/moon.wav` | `drop-100` | 396 | 100 天累積的低频回响 |
| 刀数起点 | `spiral` | `assets/media/spiral.wav` | `counter-1` | 426 | 里程表开始滚动 |
| 第 37 刀滑刃 | `fold` | `assets/media/fold.wav` | `slip-37` | 500 | 唯一一次失衡的切削 |
| 第 100 刀 | `fold` | `assets/media/fold.wav` | `cut-100` | 560 | 金色落点的完成音 |
| 复利定义 | `origin` | `assets/media/origin.wav` | `loop-1` | 612 | 产出接回投入的回环起点 |
| 条件 1 | `grain` | `assets/media/grain.wav` | `rule-1` | 640 | 再投入标记落位 |
| 条件 2 | `grain` | `assets/media/grain.wav` | `rule-2` | 665 | 时间标记落位 |
| 条件 3 | `grain` | `assets/media/grain.wav` | `rule-3` | 690 | 反馈标记落位 |
| 第 2 层 | `spiral` | `assets/media/spiral.wav` | `turn-2` | 760 | 二叉分叉第 2 层展开 |
| 第 4 层 | `spiral` | `assets/media/spiral.wav` | `turn-4` | 810 | 叶节点增至 16 |
| 第 6 层 | `spiral` | `assets/media/spiral.wav` | `turn-6` | 870 | 叶节点增至 64 |
| 第 10 折 | `fold` | `assets/media/fold.wav` | `fold-10` | 940 | 纸层开始翻倍 |
| 第 20 折 | `fold` | `assets/media/fold.wav` | `fold-20` | 980 | 尺度过月球一半 |
| 第 30 折 | `fold` | `assets/media/fold.wav` | `fold-30` | 1020 | 曲线进入陡段 |
| 第 42 折 | `moon` | `assets/media/moon.wav` | `fold-42` | 1050 | 越过地月距离的落点 |
| 线性 42 步 | `grain` | `assets/media/grain.wav` | `linear-42` | 1130 | 4.2 毫米的对照落点 |
| 翻倍 42 步 | `fold` | `assets/media/fold.wav` | `double-42` | 1210 | 439,804.65 公里的对照落点 |
| 唯一硬切 | `board` | `assets/media/board.wav` | `hard-cut` | 1230 | 两堆纸 → 网络的低频撞击，配乐 duck |
| 前 45 条 | `network` | `assets/media/network.wav` | `first-45` | 1300 | 前 10 个概念的内部连接 |
| 新增 945 条 | `network` | `assets/media/network.wav` | `add-945` | 1370 | 最后 10 个接入前 90 个 |
| 21× | `grain` | `assets/media/grain.wav` | `ratio-21` | 1395 | 比例读数落定 |
| 第 1 格 | `grain` | `assets/media/grain.wav` | `cell-1` | 1420 | 棋盘从 1 粒开始 |
| 第 32 格 | `grain` | `assets/media/grain.wav` | `cell-32` | 1505 | 上半盘堆高 |
| 第 64 格 | `board` | `assets/media/board.wav` | `cell-64` | 1545 | 2^63 粒的落点 |
| 99 根线 | `return` | `assets/media/return.wav` | `lines-99` | 1665 | 第一节点连回其余 99 个 |
| “接”字 | `finale` | `assets/media/finale.wav` | `glyph` | 1740 | 4,950 条弦收拢成字形 |
| 片名 | `origin` | `assets/media/origin.wav` | `title` | 1762 | 片名落定与收尾 |

## 混音约定

- `soundtrack.music` 显式写 `gainDb: 0`、`loop: false`、`fadeInMs: 0`、`fadeOutMs: 0`；动态由 score 自身包络承担，避免二次淡入。
- 事件音全部通过 `eventId` 绑定分镜事件，不另写毫秒偏移；`outputs/events.json` 与音效起点使用同一事件帧。
- 配乐按场次分段：0–6 / 6–14 / 14–20 / 20–24 / 24–30 / 30–36 / 36–41 / 41–47 / 47–52 / 52–60 秒，和声与鼓组密度随场次变化；41.0 秒硬切处保留 0.4 秒 duck。
- 母版目标约 −14 LUFS / −1 dBTP；事件音峰值按角色设定，最终以 `m2v qa` 的实测响度为准。
- 参考片音轨未复用、未转码，也不进入本示例。
