# 运气到底是什么：45 秒示例设计

## 命题与事实边界

同一个水滴状尝试者从失败记录进入次数、概率、柱图和面积乘法。观众最终应理解“预期成功次数 = 上场次数 × 单次成功概率”。`E(S)=Np` 是线性期望；单次概率不会因重复上场自动变大，预期值不保证实际命中。红色仅表示示意未中，金色表示示意命中、成功区域或主要结果。

## 全片原则

近黑底、米白主体、金色结果、红色未中。用大字与同一角色保持注意力，再让数字、盘、柱和面积成为新的认识任务。一次只改变一个比较条件；图形和数字来自相同数据，切换后留稳定阅读。动作以弧线、接触、压扁和减速落定组织，声音跟随命名事件；光效不盖过必要文字。

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
    "basis": "先试制最弱计数与图表，独立盲看后同轮对照同用途参考及旧版；再试制面积乘法。G5内部检查，G6全新代理，不借旧周期通过。",
    "risks": [
      {
        "id": "redesign-count",
        "kind": "core-event",
        "scope": {
          "checkpointIds": [
            "cp-redesign-ledger"
          ]
        },
        "reason": "红金记录、计数和水滴联动，原参考计数窗及旧版分别对照，见style-reference。",
        "requiredEvidence": [
          "production/checkpoints/cp-redesign-ledger/window.mp4"
        ]
      },
      {
        "id": "redesign-charts",
        "kind": "core-event",
        "scope": {
          "checkpointIds": [
            "cp-redesign-probability",
            "cp-redesign-bars"
          ]
        },
        "reason": "边界角色、条件逐项改变与同尺度比较；参考只迁移方法，不迁移概率口径，见style-reference。",
        "requiredEvidence": [
          "production/checkpoints/cp-redesign-probability/window.mp4",
          "production/checkpoints/cp-redesign-bars/window.mp4"
        ]
      },
      {
        "id": "redesign-multiplication",
        "kind": "core-event",
        "scope": {
          "checkpointIds": [
            "cp-redesign-area"
          ]
        },
        "reason": "横纵扩展面积与预期1/3/9对应，不画成实际命中，见style-reference。",
        "requiredEvidence": [
          "production/checkpoints/cp-redesign-area/window.mp4"
        ]
      },
      {
        "id": "redesign-timing",
        "kind": "structure-timing",
        "scope": {
          "checkpointIds": [
            "cp-redesign-ledger",
            "cp-redesign-probability",
            "cp-redesign-bars",
            "cp-redesign-area"
          ]
        },
        "reason": "无旁白大字、变速计数、逐条件比较和面积揭示须检查完整阅读及时序。",
        "requiredEvidence": [
          "production/checkpoints/cp-redesign-ledger/window.mp4",
          "production/checkpoints/cp-redesign-probability/window.mp4",
          "production/checkpoints/cp-redesign-bars/window.mp4",
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
          "core": false,
          "window": [
            0,
            150
          ]
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
              "audience": "表格与第1次计数建立",
              "visible": "表格与第1次计数建立",
              "attention": "当前记录、计数及其上方水滴",
              "toleranceFrames": 2,
              "failure": "颜色丢失、计数不同步、水滴抢字或高速抖动"
            },
            "change": {
              "window": [
                28,
                150
              ],
              "audience": "红金记录滚动，计数与水滴节拍联动",
              "visible": "红金记录滚动，计数与水滴节拍联动",
              "attention": "当前记录、计数及其上方水滴",
              "toleranceFrames": 2,
              "failure": "颜色丢失、计数不同步、水滴抢字或高速抖动"
            },
            "reveal": {
              "window": [
                150,
                166
              ],
              "audience": "滚动提前刹车，30落定",
              "visible": "滚动提前刹车，30落定",
              "attention": "当前记录、计数及其上方水滴",
              "toleranceFrames": 2,
              "failure": "颜色丢失、计数不同步、水滴抢字或高速抖动"
            },
            "result": {
              "window": [
                166,
                192
              ],
              "audience": "水滴最后落下并收势",
              "visible": "水滴最后落下并收势",
              "attention": "当前记录、计数及其上方水滴",
              "toleranceFrames": 2,
              "failure": "颜色丢失、计数不同步、水滴抢字或高速抖动"
            },
            "hold": {
              "window": [
                192,
                210
              ],
              "audience": "保留30与结果行供阅读",
              "visible": "保留30与结果行供阅读",
              "attention": "当前记录、计数及其上方水滴",
              "toleranceFrames": 2,
              "failure": "颜色丢失、计数不同步、水滴抢字或高速抖动"
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
          "core": false,
          "window": [
            0,
            90
          ]
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
              "audience": "10%成功区与90%未中区建立",
              "visible": "10%成功区与90%未中区建立",
              "attention": "成功边界、当前概率与起始标记",
              "toleranceFrames": 2,
              "failure": "比例不符、边界角色脱节或单次概率被误读为累计"
            },
            "change": {
              "window": [
                36,
                112
              ],
              "audience": "成功边界扩展，水滴随边界移动",
              "visible": "成功边界扩展，水滴随边界移动",
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
              "audience": "单个水滴落定，结果数字保留",
              "visible": "单个水滴落定，结果数字保留",
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
              "audience": "30×30%=9完整稳读并明确预期",
              "visible": "30×30%=9完整稳读并明确预期",
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
          "sampleStep": 3,
          "minEventFrames": 3,
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "1920横屏与393宽实际观察；讲解96px起，不作为跨作品阈值",
            "allowedOverlaps": [
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
