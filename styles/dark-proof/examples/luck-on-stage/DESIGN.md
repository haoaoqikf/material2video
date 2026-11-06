# 运气到底是什么：45 秒示例设计

## 命题与事实边界

同一个圆形上场标记从失败记录进入次数、概率、柱图和面积乘法。观众最终应理解“预期成功次数 = 上场次数 × 单次成功概率”。`E(S)=Np` 是线性期望；单次概率不会因重复上场自动变大，预期值不保证实际命中。红色仅表示示意未中，金色表示示意命中、成功区域或主要结果。

## 2026-11-06 形象修订

用户明确要求全片不再使用旧版尖顶角色。保持 45 秒、七场、原有文案、数学口径、红金结果语义及事件声音；形象本身是可调整的历史设计选择。旧版 0–45 秒七场均使用同一个形象，因此从制作与迭代阶段重入，统一改成实心圆形上场标记，仍沿路径进入、随结果变色并在落点短暂压扁。圆的无方向轮廓与次数、概率盘及柱形的简洁几何语言一致；不新增装饰或解释文字。

旧版视频 SHA-256 为 `1295107F9C3C084AB8A2375D1DD026B5634ADBE169041F0DDD6EF91B83EDCEFE`，准备指纹为 `4ac5803bf8474e13a0dd59d8ee4aa9fecba16acc11273ecf0defd794677cf172`。比较候选基线为 `outputs/baselines/cbbea26eec7b4144a1ada2c8a6e3481d/`；旧版角色源码副本为 `outputs/revision-sources/cbbea26eec7b4144a1ada2c8a6e3481d/attempt.tsx`。受影响的是七场的主体外观与局部接触范围，原有评审结论仅对应旧版。新候选须检查完整帧序列、手机尺寸和七场之间的形象连续性。

## 全片原则

近黑底、米白主体、金色结果、红色未中。用大字与同一角色保持注意力，再让数字、盘、柱和面积成为新的认识任务。一次只改变一个比较条件；图形和数字来自相同数据，切换后留稳定阅读。动作以弧线、接触、压扁和减速落定组织，声音跟随命名事件；光效不盖过必要文字。

## 已确认的全片光影编排

用户已确认[光影与穿越方案](outputs/reference-analysis.md)。本轮基线为 `outputs/baselines/fe166957232b4169996a307ea62ec807/`，旧候选 SHA-256 为 `0AB2FF63A7CD731C22B07E92D810C633C65F5BF74159FA0CDDC56576AF4EBC00`；修改前的场景、分镜和设计记录在同 ID 的 `outputs/revision-sources/` 下。旧通过不授权本轮实现。

统一动作是「近身微光与离散金点 → 减速/自然下落 → 接触 → 分级释放 → 余光下坠」。开场删除白色锥形拖尾和漂浮椭圆；失败球下落变暗，红色轻反馈；第三次命中在下落末端释放局部金光。记录30落定只轻点，概率30%锁定用中弱局部环，柱图9落定用中强局部环；面积横纵扩展的接触降为轻反馈，唯一主爆移至37秒公式完整落定。结尾球加速下落、轻压缩、少量余光后安静留读。真实支撑面上才出现接触影，概率标记保持贴着边界。

14.4–15.2秒短穿环沿两幕同一个24帧时间求值：小球聚入金环、环向外扩张与径向碎光产生纵深、中心移到下一场圆盘位置、外环减速并分为十段。字幕不随镜头缩放。前后必须能认回圆环结构，跨切点不得突然换中心；若实际样片不能成立，按已确认备选缩成扩环接棒。三组比较条件及45秒总时长继续由现有分镜表达。

参考《重复》的局部结果释放与44.7–46.8秒空间穿越，证据及外观差值见 `outputs/style-reference.md`。采用亮核快起、金环外扩、碎光独立下坠、结果留读，以及前场动作生成下一场结构；不采用参考角色、岩石、具体数值或音轨。运动以克制的两端平滑移动和加速下坠为主，接触只短促压缩一次。光源固定在球体左上；飞行光点随速度收回，不用持续长尾。

外部方案已检索：现有 `@react-three/postprocessing 3.2.0`（MIT）、`postprocessing 6.39.5`（Zlib）支持Bloom，但只处理WebGL，不能直接给当前SVG图表加光。新增3D合成会扩大依赖和验证范围，本片复用成熟的 `sampleTrail`、`particleField`、`Burst`、`burstField` 与 `ScreenBurstLayer`；作品层仅编排事件、强弱及跨场连续状态，不新增共享组件或渲染契约。

## 逐场设计

| 时间 | 观看任务 | 画面与衔接 | 失败现象 |
|---|---|---|---|
| 0–5秒 | 失败后继续，建立期待 | 两次未中后命中，角色进入记录 | 路径与结果矛盾，字抢动作 |
| 5–12秒 | 理解每次尝试都计数 | 开场第三次命中接成记录起点，再累积至30；角色随计数起落 | 开场结果与记录脱节，或高潮后读不到30 |
| 12–22秒 | 分清次数与单次概率 | 两句大字转入十等分盘，从10%展示到30% | 盘区、边界与数字脱节；误写为累计概率 |
| 22–29秒 | 逐项改变条件 | 同零基准三柱先改次数，再改概率 | 同时改两条件或柱高失真 |
| 29–39秒 | 看见乘法结构 | 面积横向三倍、纵向三倍，再汇成30×30%=9 | 九格被误当实际九次命中 |
| 39–45秒 | 回到可采取的结论 | 角色落在“多上场，把每一次做好”句末 | 遮字或新增概念 |

## 当前材料与审核边界

本目录从 `videos/general/luck-on-stage` 的可编辑材料复制，保留原片的构思与数学口径。原片审核只作历史来源；本示例以自己的准备、成片与[验证记录](VERIFICATION.md)判定。原生和手机尺寸均需复核角色、图表、字幕与过渡。无需照搬复利片的雪球或连续图表形式；两片共享风格，而非分镜。
## 制作合同

```m2v-checkpoints
{
  "version": 2,
  "cycleId": "luck-example-20261106",
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "reviewPlan": {
    "basis": "用户确认光影与短穿环重做方案。先验证开场自然落定、跨场环形接棒、公式主爆与文字保护，再同轮覆盖记录、概率和柱图。G5内部全片检查，G6由未参与前期的新代理综合终审。",
    "risks": [
      {
        "id": "light-landing",
        "kind": "core-event",
        "scope": {
          "checkpointIds": [
            "cp-redesign-hook",
            "cp-redesign-ledger",
            "cp-redesign-bars",
            "cp-redesign-area"
          ]
        },
        "reason": "主球下落、接触与光效触发必须同源，亮核退去后结果继续可读；参考采用范围见outputs/style-reference.md。",
        "requiredEvidence": [
          "production/checkpoints/cp-redesign-hook/window.mp4",
          "production/checkpoints/cp-redesign-ledger/window.mp4",
          "production/checkpoints/cp-redesign-bars/window.mp4",
          "production/checkpoints/cp-redesign-area/window.mp4"
        ]
      },
      {
        "id": "ring-handoff",
        "kind": "core-event",
        "scope": {
          "checkpointIds": [
            "cp-redesign-bridge",
            "cp-redesign-probability"
          ]
        },
        "reason": "14.4–15.2秒两幕共享穿环时间，出口须可认回为概率盘；不能靠字幕补接。",
        "requiredEvidence": [
          "production/checkpoints/cp-redesign-bridge/window.mp4",
          "production/checkpoints/cp-redesign-probability/window.mp4"
        ]
      },
      {
        "id": "light-timing",
        "kind": "structure-timing",
        "scope": {
          "checkpointIds": [
            "cp-redesign-hook",
            "cp-redesign-bridge",
            "cp-redesign-probability",
            "cp-redesign-area"
          ]
        },
        "reason": "新增下落、跨切点穿环、快亮核与余辉必须保留阅读窗口和因果次序。",
        "requiredEvidence": [
          "g5-contact-light.png",
          "production/checkpoints/cp-redesign-area/window.mp4"
        ]
      }
    ]
  },
  "scenes": [
    {
      "id": "hook",
      "durationFrames": 150,
      "shots": [
        {
          "id": "hook-shot",
          "tier": "B",
          "core": true,
          "window": [
            0,
            150
          ],
          "timeStructure": {
            "establish": {
              "window": [
                0,
                12
              ],
              "audience": "片名与门框建立",
              "visible": "片名与门框建立",
              "attention": "圆形标记、落点、文字和当前光环",
              "toleranceFrames": 1,
              "failure": "球突然定住、飞行伪地影、光效无触发来源、跨场中心跳动或遮挡必要文字"
            },
            "change": {
              "window": [
                12,
                90
              ],
              "audience": "两次未中，红色反馈后球自然下落消隐",
              "visible": "两次未中，红色反馈后球自然下落消隐",
              "attention": "圆形标记、落点、文字和当前光环",
              "toleranceFrames": 1,
              "failure": "球突然定住、飞行伪地影、光效无触发来源、跨场中心跳动或遮挡必要文字"
            },
            "reveal": {
              "window": [
                90,
                126
              ],
              "audience": "第三次穿过后顺势下落到落定点",
              "visible": "第三次穿过后顺势下落到落定点",
              "attention": "圆形标记、落点、文字和当前光环",
              "toleranceFrames": 1,
              "failure": "球突然定住、飞行伪地影、光效无触发来源、跨场中心跳动或遮挡必要文字"
            },
            "result": {
              "window": [
                126,
                140
              ],
              "audience": "命中触发局部金环与碎光",
              "visible": "命中触发局部金环与碎光",
              "attention": "圆形标记、落点、文字和当前光环",
              "toleranceFrames": 1,
              "failure": "球突然定住、飞行伪地影、光效无触发来源、跨场中心跳动或遮挡必要文字"
            },
            "hold": {
              "window": [
                140,
                150
              ],
              "audience": "结果继续可读并接入第三次记录",
              "visible": "结果继续可读并接入第三次记录",
              "attention": "圆形标记、落点、文字和当前光环",
              "toleranceFrames": 1,
              "failure": "球突然定住、飞行伪地影、光效无触发来源、跨场中心跳动或遮挡必要文字"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-redesign-hook",
          "shotId": "hook-shot",
          "frame": 130,
          "window": [
            0,
            150
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "这次没中，再来一次",
              "window": [
                18,
                78
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "好运，发生在某次上场",
              "window": [
                90,
                146
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "保证成功",
            "必然成功",
            "十次必成一次"
          ],
          "sampleStep": 1,
          "minEventFrames": 1,
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "1920横屏与393宽实际观察；讲解96px起，不作为跨作品阈值"
          }
        }
      ]
    },
    {
      "id": "ledger",
      "durationFrames": 210,
      "shots": [
        {
          "id": "ledger-shot",
          "tier": "A",
          "core": true,
          "window": [
            0,
            210
          ],
          "timeStructure": {
            "establish": {
              "window": [
                0,
                28
              ],
              "audience": "表格与第3次计数建立",
              "visible": "表格与第3次计数建立",
              "attention": "当前记录、计数及其上方圆形标记",
              "toleranceFrames": 2,
              "failure": "颜色丢失、计数不同步、圆形标记抢字或高速抖动"
            },
            "change": {
              "window": [
                28,
                150
              ],
              "audience": "红金记录滚动，计数与圆形标记节拍联动",
              "visible": "红金记录滚动，计数与圆形标记节拍联动",
              "attention": "当前记录、计数及其上方圆形标记",
              "toleranceFrames": 2,
              "failure": "颜色丢失、计数不同步、圆形标记抢字或高速抖动"
            },
            "reveal": {
              "window": [
                150,
                166
              ],
              "audience": "滚动提前刹车，30落定",
              "visible": "滚动提前刹车，30落定",
              "attention": "当前记录、计数及其上方圆形标记",
              "toleranceFrames": 2,
              "failure": "颜色丢失、计数不同步、圆形标记抢字或高速抖动"
            },
            "result": {
              "window": [
                166,
                192
              ],
              "audience": "圆形标记最后落下并收势",
              "visible": "圆形标记最后落下并收势",
              "attention": "当前记录、计数及其上方圆形标记",
              "toleranceFrames": 2,
              "failure": "颜色丢失、计数不同步、圆形标记抢字或高速抖动"
            },
            "hold": {
              "window": [
                192,
                210
              ],
              "audience": "保留30与结果行供阅读",
              "visible": "保留30与结果行供阅读",
              "attention": "当前记录、计数及其上方圆形标记",
              "toleranceFrames": 2,
              "failure": "颜色丢失、计数不同步、圆形标记抢字或高速抖动"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-redesign-ledger",
          "shotId": "ledger-shot",
          "frame": 190,
          "window": [
            0,
            210
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "先增加上场次数",
              "window": [
                14,
                200
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "保证成功",
            "必然成功",
            "十次必成一次"
          ],
          "sampleStep": 3,
          "minEventFrames": 3,
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "1920横屏与393宽实际观察；讲解96px起，不作为跨作品阈值"
          }
        }
      ]
    },
    {
      "id": "bridge",
      "durationFrames": 90,
      "shots": [
        {
          "id": "bridge-shot",
          "tier": "B",
          "core": true,
          "window": [
            0,
            90
          ],
          "timeStructure": {
            "establish": {
              "window": [
                0,
                40
              ],
              "audience": "多上场建立，球靠近文字",
              "visible": "多上场建立，球靠近文字",
              "attention": "圆形标记、落点、文字和当前光环",
              "toleranceFrames": 1,
              "failure": "球突然定住、飞行伪地影、光效无触发来源、跨场中心跳动或遮挡必要文字"
            },
            "change": {
              "window": [
                40,
                63
              ],
              "audience": "第二句显现，球沿弧线加速下落",
              "visible": "第二句显现，球沿弧线加速下落",
              "attention": "圆形标记、落点、文字和当前光环",
              "toleranceFrames": 1,
              "failure": "球突然定住、飞行伪地影、光效无触发来源、跨场中心跳动或遮挡必要文字"
            },
            "reveal": {
              "window": [
                63,
                72
              ],
              "audience": "球落定并短暂停留",
              "visible": "球落定并短暂停留",
              "attention": "圆形标记、落点、文字和当前光环",
              "toleranceFrames": 1,
              "failure": "球突然定住、飞行伪地影、光效无触发来源、跨场中心跳动或遮挡必要文字"
            },
            "result": {
              "window": [
                72,
                84
              ],
              "audience": "球聚入金环，圆环扩张并产生纵深",
              "visible": "球聚入金环，圆环扩张并产生纵深",
              "attention": "圆形标记、落点、文字和当前光环",
              "toleranceFrames": 1,
              "failure": "球突然定住、飞行伪地影、光效无触发来源、跨场中心跳动或遮挡必要文字"
            },
            "hold": {
              "window": [
                84,
                90
              ],
              "audience": "保持同一穿环中心与下一场接续",
              "visible": "保持同一穿环中心与下一场接续",
              "attention": "圆形标记、落点、文字和当前光环",
              "toleranceFrames": 1,
              "failure": "球突然定住、飞行伪地影、光效无触发来源、跨场中心跳动或遮挡必要文字"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-redesign-bridge",
          "shotId": "bridge-shot",
          "frame": 70,
          "window": [
            0,
            90
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": [
            "保证成功",
            "必然成功",
            "十次必成一次"
          ],
          "sampleStep": 1,
          "minEventFrames": 1,
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "1920横屏与393宽实际观察；讲解96px起，不作为跨作品阈值"
          }
        }
      ]
    },
    {
      "id": "probability",
      "durationFrames": 210,
      "shots": [
        {
          "id": "probability-shot",
          "tier": "A",
          "core": true,
          "window": [
            0,
            210
          ],
          "timeStructure": {
            "establish": {
              "window": [
                0,
                36
              ],
              "audience": "穿环出口形成十等分盘，10%成功区与90%未中区建立",
              "visible": "穿环出口形成十等分盘，10%成功区与90%未中区建立",
              "attention": "成功边界、当前概率与起始标记",
              "toleranceFrames": 2,
              "failure": "比例不符、边界角色脱节或单次概率被误读为累计"
            },
            "change": {
              "window": [
                36,
                112
              ],
              "audience": "成功边界扩展，圆形标记随边界移动",
              "visible": "成功边界扩展，圆形标记随边界移动",
              "attention": "成功边界、当前概率与起始标记",
              "toleranceFrames": 2,
              "failure": "比例不符、边界角色脱节或单次概率被误读为累计"
            },
            "reveal": {
              "window": [
                112,
                140
              ],
              "audience": "30%锁定并显出起点差距",
              "visible": "30%锁定并显出起点差距",
              "attention": "成功边界、当前概率与起始标记",
              "toleranceFrames": 2,
              "failure": "比例不符、边界角色脱节或单次概率被误读为累计"
            },
            "result": {
              "window": [
                140,
                192
              ],
              "audience": "成功和未中比例与数字稳定",
              "visible": "成功和未中比例与数字稳定",
              "attention": "成功边界、当前概率与起始标记",
              "toleranceFrames": 2,
              "failure": "比例不符、边界角色脱节或单次概率被误读为累计"
            },
            "hold": {
              "window": [
                192,
                210
              ],
              "audience": "角色离开边界接向比较",
              "visible": "角色离开边界接向比较",
              "attention": "成功边界、当前概率与起始标记",
              "toleranceFrames": 2,
              "failure": "比例不符、边界角色脱节或单次概率被误读为累计"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-redesign-probability",
          "shotId": "probability-shot",
          "frame": 190,
          "window": [
            0,
            210
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "让每一次，更有胜算",
              "window": [
                14,
                202
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "保证成功",
            "必然成功",
            "十次必成一次"
          ],
          "sampleStep": 1,
          "minEventFrames": 1,
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "1920横屏与393宽实际观察；讲解96px起，不作为跨作品阈值"
          }
        }
      ]
    },
    {
      "id": "bars",
      "durationFrames": 210,
      "shots": [
        {
          "id": "bars-shot",
          "tier": "A",
          "core": true,
          "window": [
            0,
            210
          ],
          "timeStructure": {
            "establish": {
              "window": [
                0,
                40
              ],
              "audience": "第一组从同一零基线长到1",
              "visible": "第一组从同一零基线长到1",
              "attention": "正在改变的条件及对应柱顶",
              "toleranceFrames": 2,
              "failure": "条件同时变化、稳定柱高失真或没有比较窗口"
            },
            "change": {
              "window": [
                40,
                124
              ],
              "audience": "只改次数，第二组长到3",
              "visible": "只改次数，第二组长到3",
              "attention": "正在改变的条件及对应柱顶",
              "toleranceFrames": 2,
              "failure": "条件同时变化、稳定柱高失真或没有比较窗口"
            },
            "reveal": {
              "window": [
                124,
                163
              ],
              "audience": "再改概率，第三组长到9",
              "visible": "再改概率，第三组长到9",
              "attention": "正在改变的条件及对应柱顶",
              "toleranceFrames": 2,
              "failure": "条件同时变化、稳定柱高失真或没有比较窗口"
            },
            "result": {
              "window": [
                163,
                180
              ],
              "audience": "单个圆形标记落定，结果数字保留",
              "visible": "单个圆形标记落定，结果数字保留",
              "attention": "正在改变的条件及对应柱顶",
              "toleranceFrames": 2,
              "failure": "条件同时变化、稳定柱高失真或没有比较窗口"
            },
            "hold": {
              "window": [
                180,
                210
              ],
              "audience": "同基线同比例完整比较",
              "visible": "同基线同比例完整比较",
              "attention": "正在改变的条件及对应柱顶",
              "toleranceFrames": 2,
              "failure": "条件同时变化、稳定柱高失真或没有比较窗口"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-redesign-bars",
          "shotId": "bars-shot",
          "frame": 190,
          "window": [
            0,
            210
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "先看：10次，每次10%",
              "window": [
                10,
                62
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "只增加次数",
              "window": [
                72,
                122
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "再提高单次概率",
              "window": [
                130,
                206
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "保证成功",
            "必然成功",
            "十次必成一次"
          ],
          "sampleStep": 1,
          "minEventFrames": 1,
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "1920横屏与393宽实际观察；讲解96px起，不作为跨作品阈值"
          }
        }
      ]
    },
    {
      "id": "area",
      "durationFrames": 300,
      "shots": [
        {
          "id": "area-shot",
          "tier": "A",
          "core": true,
          "window": [
            0,
            300
          ],
          "timeStructure": {
            "establish": {
              "window": [
                0,
                48
              ],
              "audience": "初始1份面积与10×10%建立",
              "visible": "初始1份面积与10×10%建立",
              "attention": "改变的维度与可数面积",
              "toleranceFrames": 2,
              "failure": "面积与数值不符、九格被误读为实际命中或公式挤压阅读"
            },
            "change": {
              "window": [
                48,
                132
              ],
              "audience": "横向变宽3倍，得到3份",
              "visible": "横向变宽3倍，得到3份",
              "attention": "改变的维度与可数面积",
              "toleranceFrames": 2,
              "failure": "面积与数值不符、九格被误读为实际命中或公式挤压阅读"
            },
            "reveal": {
              "window": [
                132,
                194
              ],
              "audience": "纵向变高3倍，九格与9对应",
              "visible": "纵向变高3倍，九格与9对应",
              "attention": "改变的维度与可数面积",
              "toleranceFrames": 2,
              "failure": "面积与数值不符、九格被误读为实际命中或公式挤压阅读"
            },
            "result": {
              "window": [
                194,
                240
              ],
              "audience": "九格让位，数值收拢成公式",
              "visible": "九格让位，数值收拢成公式",
              "attention": "改变的维度与可数面积",
              "toleranceFrames": 2,
              "failure": "面积与数值不符、九格被误读为实际命中或公式挤压阅读"
            },
            "hold": {
              "window": [
                240,
                300
              ],
              "audience": "公式完整落定后释放全片主光，随后保留30×30%=9稳定阅读",
              "visible": "公式完整落定后释放全片主光，随后保留30×30%=9稳定阅读",
              "attention": "改变的维度与可数面积",
              "toleranceFrames": 2,
              "failure": "面积与数值不符、九格被误读为实际命中或公式挤压阅读"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-redesign-area",
          "shotId": "area-shot",
          "frame": 280,
          "window": [
            0,
            300
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "次数 × 单次成功概率",
              "window": [
                12,
                44
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "次数变3倍",
              "window": [
                50,
                124
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "概率也变3倍",
              "window": [
                136,
                213
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "预期成功9次",
              "window": [
                242,
                296
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "保证成功",
            "必然成功",
            "十次必成一次"
          ],
          "sampleStep": 1,
          "minEventFrames": 1,
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "1920横屏与393宽实际观察；讲解96px起，不作为跨作品阈值",
            "allowedOverlaps": [
              [
                "area-model",
                "area-result"
              ],
              [
                "attempt-character",
                "area-result"
              ]
            ]
          }
        }
      ]
    },
    {
      "id": "closing",
      "durationFrames": 180,
      "shots": [
        {
          "id": "closing-shot",
          "tier": "B",
          "core": false,
          "window": [
            0,
            180
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "cp-redesign-closing",
          "shotId": "closing-shot",
          "frame": 160,
          "window": [
            0,
            180
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": [
            "保证成功",
            "必然成功",
            "十次必成一次"
          ],
          "sampleStep": 3,
          "minEventFrames": 3,
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "1920横屏与393宽实际观察；讲解96px起，不作为跨作品阈值"
          }
        }
      ]
    }
  ]
}
```
