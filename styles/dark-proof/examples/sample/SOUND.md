# 声音设计

示例无旁白，声音只承担“前轻—中抬—尾收”与事件同步。环境床与事件音均由 `assets/synthesize.py` 确定性生成，24 kHz PCM16 单声道、CC0-1.0；`assets/recipe.json` 固定摘要、时长、采样率与声道。

## 角色与事件

| 角色 | recipe id | storyboard `sourceRef` | 事件 | 帧 | 作用 |
|---|---|---|---|---:|---|
| 环境床 | `bed` | `assets/media/bed.wav` | — | 0–1740 | 58 秒无旋律纹理；0.4–3.0 秒轻入，20 秒处收窄，43–51 秒略抬，53.5–58 秒收束 |
| 均值摆动 | `swing` | `assets/media/swing.wav` | `swing-1` / `swing-2` / `swing-3` | 235 / 285 / 335 | 每次翻转一条评价的短促点击 |
| 硬切撞击 | `impact` | `assets/media/impact.wav` | `hard-cut` | 600 | 20.0 秒唯一硬切的低频撞击 |
| 线起笔 | `scratch` | `assets/media/scratch.wav` | `line-start` | 620 | 手绘线开始生长 |
| 线溶解 | `dissolve` | `assets/media/dissolve.wav` | `line-gone` | 760 | 线的权威被撤走时的空气层 |
| 均值回归 | `regress` | `assets/media/regress.wav` | `regress` | 900 | 第二次观测向均值靠近 |
| 文化锚点 | `anchor` | `assets/media/anchor.wav` | `anchor` | 1070 | 盲人摸象落点 |
| 公式 | `formula` | `assets/media/formula.wav` | `formula` | 1300 | 标准误曲线落点 |
| 收束 | `finale` | `assets/media/finale.wav` | `finale` | 1580 | 回到 3/1000 的低频和弦 |

## 混音约定

- `soundtrack.music` 显式写 `gainDb: 0`、`loop: false`、`fadeInMs: 0`、`fadeOutMs: 0`；动态由环境床自身包络承担，避免二次淡入。
- 事件音全部通过 `eventId` 绑定分镜事件，不另写毫秒偏移；`outputs/events.json` 与音效起点使用同一事件帧。
- 母版目标约 −14 LUFS / −1 dBTP；事件音峰值按角色设定，最终以 `m2v qa` 的实测响度为准。
- 参考片音轨未复用、未转码，也不进入本示例。
