# 让积累，参与下一次：R6 设计

## 命题与边界

让观众看见“本轮新增留在下一轮”如何改变增长基础。初始100，每轮按现有总量增加1%，与每轮固定加1比较；不追加外部投入。雪球只提供直觉，不映射精确1%或预测现实回报。唯一模型在 `scenes/model.ts`。

## 全片原则

近黑舞台，米白表示固定增量，暖金表示按现有总量增长。同一金色焦点从开场数字、雪球、表格、折线与柱顶接向公式；每换一种信息形式，都要增加一项认识。中文 M2V Sans、数字 M2V Inter、公式使用登记的 KaTeX 字体。大字、图表与字幕承担主体信息，模型口径仍可读。动作先有因果和落点，再给结果观察窗口；整屏释放只用于数字锁定、柱图最终比较与公式答案。

## 逐场设计

| 时间 | 新增认识 | 主要画面与衔接 | 失败现象 |
|---|---|---|---|
| 0–11秒 | 从100和1%提出问题；雪球只说明已有体量影响下一次 | 数值与轮次同一步长推进；数字锁定后小球穿过命题，接触雪面并增长，收拢到表格首行100.00 | 轮次和数值错配、接棒认不回、寓言被误当精确模型 |
| 11–17秒 | 区分现有总量与本轮新增 | 表格逐行递推，活动行和数值放大；103.03接入曲线起点 | 列头或模型口径太弱，误以为每轮只加1 |
| 17–23秒 | 看同起点双线从接近到分离 | 图区横向展开，金色端点与增大读数同源；起点读数避开左侧坐标，结束后安静落向第一柱 | 起点读数越界、端点跳位、强光抢读数 |
| 23–29秒 | 比较10、50、100轮差值 | 同零基准三组柱错峰生长，到达终值才显示轮次与正确终值；当前差值带轮次在柱组左上方放大揭示，金色球逐组引导，末组才整屏强调 | 动画中显示错误暂态数值、比例失真、标签碰撞或固定位置引起误配 |
| 29–40秒 | 公式压缩前文，回答开头并回认命题 | 指数由100轮接入，答案锁定后释放；小球回到结论句末 | 公式突然出现、结果或结尾读不完 |

## 实现与取舍

R6借鉴[运气示例](../../principle-metaphor/luck-on-stage/README.md)的主字阶、持续焦点和结果优先，而保留本片多载体论证。曲线图区和标签更大；曲线处撤去整屏冲击，柱顶和公式粒子收敛。数字、标记、图形都从同一数学模型求值，缓动按帧纯计算。复用既有 Counter、ChartLine、Burst、Impact、MathFormula 和 Remotion，不引入新组件或依赖。详细前后取舍见[创作复盘](CASE_STUDY.md)，当前成片状态见[验证](VERIFICATION.md)。

## 当前制作合同

```m2v-checkpoints
{
  "version": 2,
  "cycleId": "compound-connect-r6-example-20261106",
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "reviewPlan": {
    "basis": "R6精修沿用八节拍论证结构，核对图表字阶、数值接棒与释放收敛；开场、图表和公式按当前候选重新观察。",
    "risks": [
      {
        "id": "multi-form-rhythm",
        "kind": "structure-timing",
        "scope": {
          "checkpointIds": [
            "cp-hook",
            "cp-proof"
          ]
        },
        "reason": "数字滚动、文字互动、跨形式焦点接棒和爆闪强弱须用完整过程确认，关键采用项见style-reference.md与DESIGN逐场表。",
        "requiredEvidence": [
          "production/checkpoints/cp-hook/window.mp4",
          "production/checkpoints/cp-proof/window.mp4"
        ]
      },
      {
        "id": "retained-model",
        "kind": "core-event",
        "scope": {
          "checkpointIds": [
            "cp-proof"
          ]
        },
        "reason": "表格必须说明新增参与下一轮；折线与柱形分别揭示过程和轮次差距，不是同一数字换皮。",
        "requiredEvidence": [
          "production/checkpoints/cp-proof/window.mp4"
        ]
      }
    ]
  },
  "scenes": [
    {
      "id": "hook",
      "durationFrames": 330,
      "shots": [
        {
          "id": "hook-shot",
          "tier": "A",
          "window": [
            0,
            330
          ],
          "core": true,
          "timeStructure": {
            "establish": {
              "window": [
                0,
                81
              ],
              "audience": "先形成问题再跟随同一焦点",
              "visible": "起点100、1%假设与滚动数值",
              "attention": "中心数字",
              "toleranceFrames": 3,
              "failure": "焦点丢失或未看清对象变化"
            },
            "change": {
              "window": [
                81,
                210
              ],
              "audience": "先形成问题再跟随同一焦点",
              "visible": "小数点离开数字，在大字间运动",
              "attention": "小球与字间落点",
              "toleranceFrames": 3,
              "failure": "焦点丢失或未看清对象变化"
            },
            "reveal": {
              "window": [
                210,
                288
              ],
              "audience": "先形成问题再跟随同一焦点",
              "visible": "小球接触地面并卷雪增大",
              "attention": "雪球与雪面",
              "toleranceFrames": 3,
              "failure": "焦点丢失或未看清对象变化"
            },
            "result": {
              "window": [
                288,
                330
              ],
              "audience": "先形成问题再跟随同一焦点",
              "visible": "局部释放后收拢到表格起点，露出100.00并停留",
              "attention": "雪球与100.00",
              "toleranceFrames": 3,
              "failure": "焦点丢失或未看清对象变化"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-hook",
          "shotId": "hook-shot",
          "frame": 288,
          "window": [
            0,
            330
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "从100开始，100轮后会怎样？",
              "window": [
                0,
                78
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "雪球越大，下一次卷起的雪越多。",
              "window": [
                222,
                300
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "年化收益",
            "保证成功",
            "必然成功"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "横屏字幕安全区与393宽显示",
            "allowedOverlaps": [
              [
                "hero-number",
                "hero-number"
              ],
              [
                "focus-ball",
                "hero-number"
              ],
              [
                "focus-ball",
                "title-first"
              ],
              [
                "focus-ball",
                "title-second"
              ],
              [
                "focus-ball",
                "snowball"
              ]
            ]
          },
          "sampleStep": 3,
          "minEventFrames": 3
        }
      ]
    },
    {
      "id": "proof",
      "durationFrames": 540,
      "shots": [
        {
          "id": "proof-shot",
          "tier": "A",
          "window": [
            0,
            540
          ],
          "core": true,
          "timeStructure": {
            "establish": {
              "window": [
                0,
                64
              ],
              "audience": "观察前后状态并获得新信息",
              "visible": "初始100与前两行增长",
              "attention": "活动行",
              "toleranceFrames": 3,
              "failure": "前后关系丢失或信息形式只是在重复结论"
            },
            "change": {
              "window": [
                64,
                180
              ],
              "audience": "观察前后状态并获得新信息",
              "visible": "新增量参与后续增长，表格生成坐标",
              "attention": "总量与下一行新增",
              "toleranceFrames": 3,
              "failure": "前后关系丢失或信息形式只是在重复结论"
            },
            "reveal": {
              "window": [
                180,
                352
              ],
              "audience": "观察前后状态并获得新信息",
              "visible": "两条线先接近后分开，终点数值可读",
              "attention": "金色端点",
              "toleranceFrames": 3,
              "failure": "前后关系丢失或信息形式只是在重复结论"
            },
            "result": {
              "window": [
                352,
                522
              ],
              "audience": "观察前后状态并获得新信息",
              "visible": "10/50/100轮的差距逐次变大",
              "attention": "当前柱组",
              "toleranceFrames": 3,
              "failure": "前后关系丢失或信息形式只是在重复结论"
            },
            "hold": {
              "window": [
                522,
                540
              ],
              "audience": "观察前后状态并获得新信息",
              "visible": "100抬向指数位置",
              "attention": "100",
              "toleranceFrames": 3,
              "failure": "前后关系丢失或信息形式只是在重复结论"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-proof",
          "shotId": "proof-shot",
          "frame": 498,
          "window": [
            0,
            540
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "多出来的，也留给下一轮。",
              "window": [
                8,
                144
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "开始差不多，后来逐渐拉开。",
              "window": [
                190,
                304
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "差距出现了。",
              "window": [
                310,
                352
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "差距，正在放大。",
              "window": [
                388,
                474
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "从0.46，扩大到70.48。",
              "window": [
                482,
                530
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "年化收益",
            "保证成功",
            "必然成功"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "横屏字幕安全区与393宽显示"
          },
          "sampleStep": 3,
          "minEventFrames": 3
        }
      ]
    },
    {
      "id": "resolution",
      "durationFrames": 330,
      "shots": [
        {
          "id": "resolution-shot",
          "tier": "B",
          "window": [
            0,
            330
          ],
          "core": false
        }
      ],
      "checkpoints": [
        {
          "id": "cp-resolution",
          "shotId": "resolution-shot",
          "frame": 288,
          "window": [
            0,
            330
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "每一轮，都站在上一轮之上。",
              "window": [
                8,
                163
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "年化收益",
            "保证成功",
            "必然成功"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "横屏字幕安全区与393宽显示"
          },
          "sampleStep": 3,
          "minEventFrames": 3
        }
      ]
    }
  ]
}
```
