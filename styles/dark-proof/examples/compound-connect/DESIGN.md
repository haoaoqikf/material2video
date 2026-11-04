# 《接》：让结果，成为下一次的起点

## 本轮来源与边界

用户先要求分析未达到参考效果的原因，随后采用2026-11-04重设计方案并指示执行。64秒、无旁白无配乐，仅必要音效、同一100单位资源与30轮取走／接回对照，取代旧版十案例。详细方案见[变更设计](../../../../openspec/changes/archive/2026-11-04-redesign-compound-connect-reference-quality/design.md)；这是一轮重新制作，旧版通过不授权新版。

旧成片与源码基线：`outputs/baselines/c8254550d52149ba95635f2ee528907c/`；旧视频SHA256为`c2aa9d38b3ee2948c042734cfd099f42b5926a19073bf51ea16cbdf58676a70e`，材料保存在该目录source/。当前源码与旧视频存在历史差异，保留事实不伪造对应。

## 全片原则

同样100单位、每轮产出为当轮投入的10%；取走组保存产出，总量100+10n；接回组把产出并入下一轮，总量100×1.1^n。30轮为400对1744.94，整数1,745为四舍五入。全部数字由scenes/model.ts求值，资源与读数同源。每完整圆片10单位，碎片按面积表示；移动中的产出包按面积表示总量。已取走的300不消失、不挪给另一组。

以近黑底、米白粗数字、暖金局部光、清楚资源轮廓形成视觉家族。抵达减速，回流转向两端平滑；定向路径的运动由当前帧求值。仅一次硬切，位于曲线终态转为同一两组结果对比；结尾回到同一接点，不新增案例。英文字仅是开场／片名短标签。屏幕短句使用现有ScreenSubtitle与宿主安全区，60px较重字重；模型方法只在建立窗口小字出现。

参考《重复》只进入设计及隔离比较，不进入画面或音轨。关键采用项为唯一强主角、轮廓与层级、源点光轨、连续因果、先机制后公式、结果消化与首尾回场。题材、字面文案、具体秒数和音色允许不同。完整对照见[参考契约](outputs/style-reference.md)。

## 实际时间与制作来源

`assets/compose.py`是文案、事件与时间编排的编辑入口；按动作与阅读安排短句，生成分镜和以下唯一合同。64秒、1920帧；第二轮段落24秒，数据段31秒、结果41秒、原因48秒、片尾56秒。具体帧以storyboard的事件与props.phases为准；无TTS、narrationWindows或music输入。

| 段 | 观看任务 | 主要状态 |
|---|---|---|
| question | 建立问题 | 30次；重复就会复利吗 |
| setup | 建立投入与产出规则 | 100，首轮+10；每片10单位 |
| take | 保存取走的结果 | 投入100、已取300、合计400 |
| return | 认回同一产出包 | +10返回并入100，投入才变110 |
| again | 新增部分也参与产出 | +11→121；+12.1→133.1 |
| history | 同轴比较完整历史 | n=0共同100；n=10/20/30拉开 |
| compare | 比较同轮总量 | 400／1744.94与约4.36倍 |
| reason | 回场解释差别 | 同一分流点；公式晚到 |
| close | 动作总结为片名 | 回路接通；接；结论留到末帧 |

首个完整核心试制覆盖17–31秒，附10–17秒上下文。静帧不证明回流成立，当前媒体的独立观察按审核策略执行；唯一问题表在outputs/visual-notes.md。独立目标图由概念美术建立，源码截图不冒充目标图。

## 制作状态

核心试制已经独立盲看及目标对照复查。首次最长读数穿过圆形边界的问题保留原失败记录，修订后已由同一独立观察者复查；扩展实现后仍须绑定当前版本重验。全片已经实现；用户于2026-11-04要求立即停止审核并提交归档，以便下一轮修改。最后目标对照未正式导入，不声明全部制作门完成；真实观察与限制写入VERIFICATION及outputs/visual-notes.md。

数据曲线采用同一线性纵轴0–1800；整数轮端点来自账本，轮间显示插值动画时轮次标记为“n→n+1”，不将中间值标成已完成的整数轮。41秒结果为统一30轮总量。公式及片名各自保留独立字形空间，光轨不横穿公式；开场数字向左缩小交接，避免30与100叠字。


```m2v-checkpoints
{
  "version": 2,
  "cycleId": "compound-connect-return-20261104",
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "reviewPlan": {
    "basis": "用户采用的单一回流实验；强轮廓与局部光、返回因果与先后顺序须在扩展前独立观察。",
    "risks": [
      {
        "id": "return-appearance",
        "kind": "static-expression",
        "scope": {
          "checkpointIds": [
            "cp-return"
          ]
        },
        "reason": "关键采用项见outputs/style-reference.md：大数字、清楚轮廓、局部自发光及主体层级。",
        "requiredEvidence": [
          "design/keyframes/return-establish.png",
          "design/keyframes/return-result.png"
        ]
      },
      {
        "id": "return-sequence",
        "kind": "structure-timing",
        "scope": {
          "checkpointIds": [
            "cp-return",
            "cp-again"
          ]
        },
        "reason": "必须先有产出，再返回并入，下一轮才开始；组别交接须有前后文。",
        "requiredEvidence": [
          "production/checkpoints/cp-return/window.mp4",
          "production/checkpoints/cp-again/window.mp4"
        ]
      },
      {
        "id": "same-packet",
        "kind": "core-event",
        "scope": {
          "checkpointIds": [
            "cp-return",
            "cp-again"
          ]
        },
        "reason": "认回产出包，110和121有可见资源来源，光效不能代替数量关系。",
        "requiredEvidence": [
          "production/checkpoints/cp-return/window.mp4",
          "production/checkpoints/cp-again/window.mp4"
        ]
      }
    ]
  },
  "scenes": [
    {
      "id": "compound-connect",
      "durationFrames": 1920,
      "shots": [
        {
          "id": "question",
          "tier": "A",
          "window": [
            0,
            120
          ]
        },
        {
          "id": "setup",
          "tier": "B",
          "window": [
            120,
            300
          ]
        },
        {
          "id": "take",
          "tier": "B",
          "window": [
            300,
            510
          ]
        },
        {
          "id": "return",
          "tier": "A",
          "window": [
            510,
            720
          ],
          "timeStructure": {
            "establish": {
              "window": [
                510,
                600
              ],
              "audience": "观看对象变化，分辨其先后",
              "visible": "100与两组身份",
              "attention": "投入簇与返回资源",
              "toleranceFrames": 3,
              "failure": "先更新数字或资源包无法认回"
            },
            "change": {
              "window": [
                600,
                696
              ],
              "audience": "观看对象变化，分辨其先后",
              "visible": "产出从出口返回",
              "attention": "投入簇与返回资源",
              "toleranceFrames": 3,
              "failure": "先更新数字或资源包无法认回"
            },
            "result": {
              "window": [
                696,
                720
              ],
              "audience": "观看对象变化，分辨其先后",
              "visible": "110与新增圆片落定",
              "attention": "投入簇与返回资源",
              "toleranceFrames": 3,
              "failure": "先更新数字或资源包无法认回"
            }
          }
        },
        {
          "id": "again",
          "tier": "A",
          "window": [
            720,
            930
          ],
          "timeStructure": {
            "establish": {
              "window": [
                720,
                728
              ],
              "audience": "观看对象变化，分辨其先后",
              "visible": "110成为下一轮起点",
              "attention": "投入簇与返回资源",
              "toleranceFrames": 3,
              "failure": "先更新数字或资源包无法认回"
            },
            "change": {
              "window": [
                728,
                884
              ],
              "audience": "观看对象变化，分辨其先后",
              "visible": "产出11并入为121，再产出12.1",
              "attention": "投入簇与返回资源",
              "toleranceFrames": 3,
              "failure": "先更新数字或资源包无法认回"
            },
            "result": {
              "window": [
                884,
                930
              ],
              "audience": "观看对象变化，分辨其先后",
              "visible": "133.1落定，新增部分已经参与产出",
              "attention": "投入簇与返回资源",
              "toleranceFrames": 3,
              "failure": "先更新数字或资源包无法认回"
            }
          }
        },
        {
          "id": "history",
          "tier": "A",
          "window": [
            930,
            1230
          ]
        },
        {
          "id": "compare",
          "tier": "A",
          "window": [
            1230,
            1440
          ]
        },
        {
          "id": "reason",
          "tier": "B",
          "window": [
            1440,
            1680
          ]
        },
        {
          "id": "close",
          "tier": "A",
          "window": [
            1680,
            1920
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "cp-question",
          "shotId": "question",
          "frame": 60,
          "window": [
            0,
            120
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "重复，就会复利吗？",
              "window": [
                9,
                117
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "投资建议",
            "保证收益"
          ],
          "measurement": {
            "allowedOverlaps": [
              [
                "return-packet",
                "active-resource"
              ],
              [
                "return-packet",
                "active-value"
              ],
              [
                "output-resource",
                "saved-resource"
              ]
            ],
            "thresholdSource": "DESIGN：主读数12px手机等效；正文短句≤30字由组件约束，两个主读数合计≤30字符。",
            "bodyRoles": [
              "active-value",
              "output-value"
            ],
            "minFont393": 12,
            "maxTextCharacters": 30,
            "subtitleRoles": [
              "screen-subtitle"
            ]
          }
        },
        {
          "id": "cp-setup",
          "shotId": "setup",
          "frame": 210,
          "window": [
            120,
            300
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "每轮产出＝当轮投入的10%。",
              "window": [
                132,
                294
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "投资建议",
            "保证收益"
          ],
          "measurement": {
            "allowedOverlaps": [
              [
                "return-packet",
                "active-resource"
              ],
              [
                "return-packet",
                "active-value"
              ],
              [
                "output-resource",
                "saved-resource"
              ]
            ],
            "thresholdSource": "DESIGN：主读数12px手机等效；正文短句≤30字由组件约束，两个主读数合计≤30字符。",
            "bodyRoles": [
              "active-value",
              "output-value"
            ],
            "minFont393": 12,
            "maxTextCharacters": 30,
            "subtitleRoles": [
              "screen-subtitle"
            ]
          }
        },
        {
          "id": "cp-take",
          "shotId": "take",
          "frame": 405,
          "window": [
            300,
            510
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "产出取走，下一轮仍从100开始。",
              "window": [
                306,
                429
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "投入100＋已取300＝400。",
              "window": [
                438,
                510
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "投资建议",
            "保证收益"
          ],
          "measurement": {
            "allowedOverlaps": [
              [
                "return-packet",
                "active-resource"
              ],
              [
                "return-packet",
                "active-value"
              ],
              [
                "output-resource",
                "saved-resource"
              ]
            ],
            "thresholdSource": "DESIGN：主读数12px手机等效；正文短句≤30字由组件约束，两个主读数合计≤30字符。",
            "bodyRoles": [
              "active-value",
              "output-value"
            ],
            "minFont393": 12,
            "maxTextCharacters": 30,
            "subtitleRoles": [
              "screen-subtitle"
            ]
          }
        },
        {
          "id": "cp-return",
          "shotId": "return",
          "frame": 699,
          "window": [
            510,
            720
          ],
          "expected": [
            {
              "role": "active-resource",
              "count": 11
            }
          ],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "另一组，同样从100出发。",
              "window": [
                516,
                603
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "把这10，接回下一轮。",
              "window": [
                609,
                717
              ]
            }
          ],
          "claims": [
            {
              "id": "active-first",
              "value": 110,
              "unit": "units",
              "basis": "100+100×10%"
            }
          ],
          "forbidden": [
            "投资建议",
            "保证收益"
          ],
          "measurement": {
            "allowedOverlaps": [
              [
                "return-packet",
                "active-resource"
              ],
              [
                "return-packet",
                "active-value"
              ],
              [
                "output-resource",
                "saved-resource"
              ]
            ],
            "thresholdSource": "DESIGN：主读数12px手机等效；正文短句≤30字由组件约束，两个主读数合计≤30字符。",
            "bodyRoles": [
              "active-value",
              "output-value"
            ],
            "minFont393": 12,
            "maxTextCharacters": 30,
            "subtitleRoles": [
              "screen-subtitle"
            ]
          },
          "minEventFrames": 12,
          "statePlan": [
            {
              "window": [
                510,
                696
              ],
              "expected": [
                {
                  "role": "active-resource",
                  "count": 10
                }
              ]
            },
            {
              "window": [
                696,
                720
              ],
              "expected": [
                {
                  "role": "active-resource",
                  "count": 11
                }
              ]
            }
          ]
        },
        {
          "id": "cp-again",
          "shotId": "again",
          "frame": 887,
          "window": [
            720,
            930
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "110，再产生11，合计121。",
              "window": [
                726,
                819
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "新增的部分，也参与下一轮。",
              "window": [
                825,
                927
              ]
            }
          ],
          "claims": [
            {
              "id": "active-second",
              "value": 121,
              "unit": "units",
              "basis": "110+110×10%"
            }
          ],
          "forbidden": [
            "投资建议",
            "保证收益"
          ],
          "measurement": {
            "allowedOverlaps": [
              [
                "return-packet",
                "active-resource"
              ],
              [
                "return-packet",
                "active-value"
              ],
              [
                "output-resource",
                "saved-resource"
              ]
            ],
            "thresholdSource": "DESIGN：主读数12px手机等效；正文短句≤30字由组件约束，两个主读数合计≤30字符。",
            "bodyRoles": [
              "active-value",
              "output-value"
            ],
            "minFont393": 12,
            "maxTextCharacters": 30,
            "subtitleRoles": [
              "screen-subtitle"
            ]
          },
          "minEventFrames": 8
        },
        {
          "id": "cp-history",
          "shotId": "history",
          "frame": 1080,
          "window": [
            930,
            1230
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "刚开始，差得不多。",
              "window": [
                936,
                1050
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "第10轮、第20轮、第30轮……",
              "window": [
                1056,
                1224
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "投资建议",
            "保证收益"
          ],
          "measurement": {
            "allowedOverlaps": [
              [
                "return-packet",
                "active-resource"
              ],
              [
                "return-packet",
                "active-value"
              ],
              [
                "output-resource",
                "saved-resource"
              ]
            ],
            "thresholdSource": "DESIGN：主读数12px手机等效；正文短句≤30字由组件约束，两个主读数合计≤30字符。",
            "bodyRoles": [
              "active-value",
              "output-value"
            ],
            "minFont393": 12,
            "maxTextCharacters": 30,
            "subtitleRoles": [
              "screen-subtitle"
            ]
          }
        },
        {
          "id": "cp-compare",
          "shotId": "compare",
          "frame": 1335,
          "window": [
            1230,
            1440
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "同样30轮，400 对 1,745。",
              "window": [
                1239,
                1350
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "接回总量，约为取走的4.36倍。",
              "window": [
                1356,
                1437
              ]
            }
          ],
          "claims": [
            {
              "id": "withdraw-total",
              "value": 400,
              "unit": "units",
              "basis": "100+30×10"
            },
            {
              "id": "reinvest-total",
              "value": 1744.94,
              "unit": "units",
              "basis": "100×1.1^30；两位小数"
            }
          ],
          "forbidden": [
            "投资建议",
            "保证收益"
          ],
          "measurement": {
            "allowedOverlaps": [
              [
                "return-packet",
                "active-resource"
              ],
              [
                "return-packet",
                "active-value"
              ],
              [
                "output-resource",
                "saved-resource"
              ]
            ],
            "thresholdSource": "DESIGN：主读数12px手机等效；正文短句≤30字由组件约束，两个主读数合计≤30字符。",
            "bodyRoles": [
              "active-value",
              "output-value"
            ],
            "minFont393": 12,
            "maxTextCharacters": 30,
            "subtitleRoles": [
              "screen-subtitle"
            ]
          }
        },
        {
          "id": "cp-reason",
          "shotId": "reason",
          "frame": 1560,
          "window": [
            1440,
            1680
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "取走，每次都从原点出发。",
              "window": [
                1446,
                1554
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "接回，每次都带着上一次。",
              "window": [
                1560,
                1674
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "投资建议",
            "保证收益"
          ],
          "measurement": {
            "allowedOverlaps": [
              [
                "return-packet",
                "active-resource"
              ],
              [
                "return-packet",
                "active-value"
              ],
              [
                "output-resource",
                "saved-resource"
              ]
            ],
            "thresholdSource": "DESIGN：主读数12px手机等效；正文短句≤30字由组件约束，两个主读数合计≤30字符。",
            "bodyRoles": [
              "active-value",
              "output-value"
            ],
            "minFont393": 12,
            "maxTextCharacters": 30,
            "subtitleRoles": [
              "screen-subtitle"
            ]
          }
        },
        {
          "id": "cp-close",
          "shotId": "close",
          "frame": 1800,
          "window": [
            1680,
            1920
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "让结果，成为下一次的起点。",
              "window": [
                1695,
                1920
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "投资建议",
            "保证收益"
          ],
          "measurement": {
            "allowedOverlaps": [
              [
                "return-packet",
                "active-resource"
              ],
              [
                "return-packet",
                "active-value"
              ],
              [
                "output-resource",
                "saved-resource"
              ]
            ],
            "thresholdSource": "DESIGN：主读数12px手机等效；正文短句≤30字由组件约束，两个主读数合计≤30字符。",
            "bodyRoles": [
              "active-value",
              "output-value"
            ],
            "minFont393": 12,
            "maxTextCharacters": 30,
            "subtitleRoles": [
              "screen-subtitle"
            ]
          }
        }
      ]
    }
  ]
}
```
