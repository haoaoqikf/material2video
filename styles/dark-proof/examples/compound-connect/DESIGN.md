# 《接：让积累生长》

## 目标与事实边界

面向普通手机观众，以原创种子寓言解释非金融的复利效应：过去的成果继续参与创造，新增成果也成为新的增长来源。种子生长、繁衍是机制类比，不是现实生态预测；不提供增长率、年代、必然成功或学习倍数。保留1920×1080、30fps、无旁白无配乐，仅事件音。方案可调整，用户最终效果目标与明确限制优先。

旧64秒候选SHA256：91f0be29ebecf1b0e7f3443f8547060fc14461c5d537f0b158ef65ecb46d04ea；成片、记录和源码位于 outputs/baselines/102ba1dd0835424384829109ae458689/。本轮回到方案与试制阶段，不继承旧通过。周期为compound-effect-growth-20261104。

## 视觉、运动与声音

近黑底#0A0B0D，米白#F3EDDC表示已形成的主体，暖金#E6BE55表示新成果及当前作用，灰色只作土层与次要标记。M2V Sans中文、M2V Inter数字。树是有分枝、宽叶、根与种壳的具体主体，不用圈点和账户界面。母株保持可认回，新增树有不同尺度；新植株生长时用金色，成熟结种时回到米白，让新种子成为金色焦点。概念图中的整株金色仅作初始方向，不要求长期保持。末段回场改变开场种子的含义。

运动以easeOutCubic抵达、easeInOutCubic场内移动；种子弧线下落、接触反应、根与枝叶分层生长。数字落定一次尺度强调。字幕绝对帧逐字错峰，末字落定后留完整阅读；主体与字幕轮流获得焦点。新增树结种是一次中释放，全貌是最强释放，光从具体对象发出。核心动作及事件见分镜beats，不另维护帧表。第二次飞行在释放余势结束后开始，避免小种子被遮挡。场景技术边界使用cut但对象按全局帧保持连续；实际硬切只计划在45秒进入学习应用处，其余承接由画面验证。无持续随机运动填空。

复用已有共享手绘路径、dark-proof的ScreenSubtitle/Burst/Impact；外部候选GSAP SplitText、Remotion spring、Pixi filters已在本轮变更设计登记评估，已有能力足够，不新增引擎。种子与树的几何为原创题材绘制。现有原创24kHz事件音按配方恢复，绑定同一事件，不复制参考音轨。

开场与片尾的动态SVG组使用will-change: transform稳定浏览器合成层，避免渐变背景因脏矩形重绘出现1–2色阶的同帧差异；不引入计时器或跨帧状态。两处修复后均通过既有60dB正序／倒序与分块边界验证，没有降低阈值。种子交接为树是有意接触，在开场合同显式登记；全貌段以始终在场的母株作为观测角色。

## 逐场设计

| 段落 | 主体及变化 | 新认识与风险 |
|---|---|---|
| 0–12秒 opening | 一颗种子触地，生根长成母株，1粒落定强调 | 开场提出为什么积累后来越来越快，先给一个具体起点 |
| 12–38秒 core | 母株结种→同一颗种子落地成树→新树再次结种→第三株出现 | 新增部分成为新的创造来源；完整26秒试制，core/G2/G3/G4覆盖，不以数量增加代替机制 |
| 38–45秒 grove | 保持原三株，拉远发现更多正在延续的生长 | 认识增长来源变多，强释放后留结果观察 |
| 45–56秒 learning | 凑十法从8+5，复用于9+6，再拓展到19+6 | 学会的方法帮助后续理解；数字可复算，不能仅以书本图标增加代替 |
| 56–68秒 closing | 回到种子及其后续生长，命名复利效应 | 回答开场：让积累推动新的积累；不承诺现实固定收益 |

## 终审后的局部设计调整

首个完整候选因C1被独立终审打回：62秒的补充句“下一次，已经有了起点”亮显仅约0.4–0.5秒，随后转灰并与片名和正常字幕竞争。这是阅读预算与层级的设计问题。删除该重复补充句，让片名、正常字幕及种子再次生长共同收束，保持总时长68秒。G5原有帧证据已覆盖该段但漏判，当前回归明确核对片尾全部文字的阅读窗口与竞争，不用“符合原方案”关闭问题。

## 参考与试制判断

参考本地《重复》仅用于动作与风格分析，不进入渲染。关键采用项：单一具体主角、动作准备/接触/反应/收势、逐字入镜、落定强调、源点扩环与粒子、早期主体最终回报。八项指标与差异见outputs/style-reference.md。概念目标由内置ImageGen独立生成，与源码隔离；只规范轮廓、主体层级及明确来源，不照搬生成图的全部纹理。

试制须能在完整窗口中认回种子，并看见新增树再次产生种子。观察分理解、表现、代表性；先盲看落盘，再同轮目标对照。失败先归因为实现/设计/混合/待定位；核心设计失败直接退回重设计。普通局部失败不推倒全片。当前完整核心试制、G5内部检查及新代理终审与目标对照均已通过；C1片尾设计问题经局部重设计和当前独立复查关闭，原失败记录与候选保留。G0–G6当前完成。

```m2v-checkpoints
{
  "version": 2,
  "cycleId": "compound-effect-growth-20261104",
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "reviewPlan": {
    "basis": "试制完整覆盖母株结种、新株生长与新株再次结种；用户目标优先，方案可经证据调整。",
    "risks": [
      {
        "id": "growth-appearance",
        "kind": "static-expression",
        "scope": {
          "checkpointIds": [
            "cp-core"
          ]
        },
        "reason": "outputs/style-reference.md：具体主体、清楚轮廓与新增长来源须先以独立目标验证。",
        "requiredEvidence": [
          "design/keyframes/growth-establish.png",
          "design/keyframes/growth-result.png"
        ]
      },
      {
        "id": "growth-sequence",
        "kind": "structure-timing",
        "scope": {
          "checkpointIds": [
            "cp-core"
          ]
        },
        "reason": "先看见种子来源及落地，再生长，再由新增植株结种；禁止字幕解释代替过程。",
        "requiredEvidence": [
          "production/checkpoints/cp-core/window.mp4"
        ]
      },
      {
        "id": "new-source",
        "kind": "core-event",
        "scope": {
          "checkpointIds": [
            "cp-core"
          ]
        },
        "reason": "完整试制必须呈现新增部分参与后续创造，可因此退回设计。",
        "requiredEvidence": [
          "production/checkpoints/cp-core/window.mp4"
        ]
      }
    ]
  },
  "scenes": [
    {
      "id": "opening",
      "durationFrames": 360,
      "shots": [
        {
          "id": "opening-shot",
          "tier": "B",
          "window": [
            0,
            360
          ],
          "core": false
        }
      ],
      "checkpoints": [
        {
          "id": "cp-opening",
          "shotId": "opening-shot",
          "frame": 313,
          "window": [
            0,
            360
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "为什么有些积累，后来会越来越快？",
              "window": [
                6,
                141
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "一颗种子，先长成一棵树。",
              "window": [
                156,
                351
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "投资收益",
            "年化收益",
            "保证成功"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "当前画幅安全区及手机阅读观察，不设注释手机门槛",
            "allowedOverlaps": [
              [
                "opening-seed",
                "mother-tree"
              ]
            ]
          }
        }
      ]
    },
    {
      "id": "core",
      "durationFrames": 780,
      "shots": [
        {
          "id": "core-shot",
          "tier": "A",
          "window": [
            0,
            780
          ],
          "core": true,
          "timeStructure": {
            "establish": {
              "window": [
                0,
                120
              ],
              "audience": "跟随主体及它带来的后续变化",
              "visible": "母株及其种子",
              "attention": "当前动作主体",
              "toleranceFrames": 2,
              "failure": "种子来源或新增部分作用无法认回"
            },
            "change": {
              "window": [
                120,
                450
              ],
              "audience": "跟随主体及它带来的后续变化",
              "visible": "种子脱离落地，新株生长",
              "attention": "当前动作主体",
              "toleranceFrames": 2,
              "failure": "种子来源或新增部分作用无法认回"
            },
            "reveal": {
              "window": [
                450,
                600
              ],
              "audience": "跟随主体及它带来的后续变化",
              "visible": "新株再次结种并释放",
              "attention": "当前动作主体",
              "toleranceFrames": 2,
              "failure": "种子来源或新增部分作用无法认回"
            },
            "result": {
              "window": [
                600,
                780
              ],
              "audience": "跟随主体及它带来的后续变化",
              "visible": "第三株生长，原株保留",
              "attention": "当前动作主体",
              "toleranceFrames": 2,
              "failure": "种子来源或新增部分作用无法认回"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-core",
          "shotId": "core-shot",
          "frame": 679,
          "window": [
            0,
            780
          ],
          "expected": [
            {
              "role": "mother-tree",
              "count": 1
            }
          ],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "树，结出了新的种子。",
              "window": [
                9,
                120
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "其中一颗，落地、生根。",
              "window": [
                129,
                285
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "它长成了另一棵树。",
              "window": [
                300,
                435
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "新长出的树，也结出了种子。",
              "window": [
                450,
                600
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "新增的部分，也开始创造。",
              "window": [
                609,
                774
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "投资收益",
            "年化收益",
            "保证成功"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "当前画幅安全区及手机阅读观察，不设注释手机门槛",
            "allowedOverlaps": [
              [
                "mother-tree",
                "first-seed"
              ],
              [
                "child-tree",
                "first-seed"
              ],
              [
                "child-tree",
                "second-seed"
              ],
              [
                "third-tree",
                "second-seed"
              ]
            ]
          },
          "minEventFrames": 2
        }
      ]
    },
    {
      "id": "grove",
      "durationFrames": 210,
      "shots": [
        {
          "id": "grove-shot",
          "tier": "A",
          "window": [
            0,
            210
          ],
          "core": false
        }
      ],
      "checkpoints": [
        {
          "id": "cp-grove",
          "shotId": "grove-shot",
          "frame": 183,
          "window": [
            0,
            210
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "增长的来源，变多了。",
              "window": [
                9,
                201
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "投资收益",
            "年化收益",
            "保证成功"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "当前画幅安全区及手机阅读观察，不设注释手机门槛"
          }
        }
      ]
    },
    {
      "id": "learning",
      "durationFrames": 330,
      "shots": [
        {
          "id": "learning-shot",
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
          "id": "cp-learning",
          "shotId": "learning-shot",
          "frame": 287,
          "window": [
            0,
            330
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "学会一个方法。",
              "window": [
                6,
                111
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "下一题，用上它。",
              "window": [
                123,
                216
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "它又帮你，理解新的问题。",
              "window": [
                228,
                324
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "投资收益",
            "年化收益",
            "保证成功"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "当前画幅安全区及手机阅读观察，不设注释手机门槛"
          }
        }
      ]
    },
    {
      "id": "closing",
      "durationFrames": 360,
      "shots": [
        {
          "id": "closing-shot",
          "tier": "A",
          "window": [
            0,
            360
          ],
          "core": false
        }
      ],
      "checkpoints": [
        {
          "id": "cp-closing",
          "shotId": "closing-shot",
          "frame": 313,
          "window": [
            0,
            360
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "让积累，推动新的积累。",
              "window": [
                9,
                171
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "这，就是复利效应。",
              "window": [
                186,
                360
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "投资收益",
            "年化收益",
            "保证成功"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "当前画幅安全区及手机阅读观察，不设注释手机门槛"
          }
        }
      ]
    }
  ]
}
```
