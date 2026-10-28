# 声音语义表

本片的声音不按“好听”挑选，而按**观众需要识别的事件**挑选。画面与声音引用同一份幕内事件（`storyboard.json` 的 `scenes[].events`），准备阶段输出的 `outputs/events.json` 是两者的共同时间证据。

## 角色与素材

| 角色 | 事件 | assetId | 参数 | 听觉作用 |
|---|---|---|---|---|
| 计时 | `tick-*`、`tick-fast-*` | `tick` | `gainDb` −32；临近第二次喂食 −30～−28 | 让观众感到时间在走，而不是看字幕才知道 |
| 接合 | `feeder-open-1/2` | `latch` | `gainDb` −22 | 食槽打开的机械动作 |
| 到达 | `feed-1/2-arrival` | `grain` | `gainDb` −20 / −19 | 食物落进盘里；第二次略强 |
| 转圈 | `turn-1/2/3/5` | `swish` | `gainDb` −28 / −26 / −24 | 重复动作本身，不替代旁白 |
| 揭示 | `reveal` | `chord` | `gainDb` −20 | 收束，提示“食物又来了” |

全部素材来自 `assets/sound-recipe.json` 的确定性合成，来源登记在 `assets/sound-sources.json`；生成的 wav 与登记文件不入库。需要新变体时先改配方，再执行：

```powershell
uv run m2v general sounds import --project styles/examples/vibe-fable/pigeon --manifest assets/sound-recipe.json
```

## 变化怎么表达

- **密度**：计时只在 `feeder` 幕每秒一声（5 声/5 秒）；第二次喂食前 1.5 秒内放 3 声，密度提高，观众先感到“快了”。
- **强弱**：同一 `assetId` 用不同 `gainDb`；第二次落料比第一次高 1 dB，收束和弦保持 −20 dB，不靠突然变响制造情绪。
- **素材区分**：计时、接合、到达、转圈、揭示各用不同 `assetId`，不靠同一个声音变调硬凑。
- **留白**：`peck-*` 事件只驱动画面动作，不配音效；走过去吃的动作留给画面。
- **不用的手段**：本片不使用 effect 级音高（pitch）。现有素材区分、密度、增益与淡化已足够表达四类语义；若后续必须用音高，应作为合成配方的可选参数单独评估，不改混音契约。

## 事件与全片时刻

| 事件 | 全片时刻 | 声音 |
|---|---:|---|
| `feeder.tick-1` … `tick-5` | 4.0–8.0 s，每秒 | `tick` ×5 |
| `wander.turn-1` | 13.5 s | `swish` |
| `wander.feeder-open-1` | 15.0 s | `latch` |
| `coincide.feed-1-arrival` | 15.8 s | `grain` |
| `repeat.turn-2` / `turn-3` | 20.2 s / 23.6 s | `swish` ×2 |
| `again.turn-5` | 28.4 s | `swish` |
| `again.tick-fast-1…3` | 28.5–29.5 s | `tick` ×3，渐强 |
| `again.feeder-open-2` | 30.0 s | `latch` |
| `again.feed-2-arrival` | 30.2 s | `grain`，略强 |
| `again.reveal` | 32.4 s | `chord` |

音效起点由 prepare 从事件帧解析；改事件后必须重新 `prepare`，不要手改音效帧。
