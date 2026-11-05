# 让积累，参与下一次：当前R5规范示例

## 命题、观看任务与边界

让观众理解：留下的成果参与下一轮，使增长的基础随之变化。数字问题引出期待，单个雪球提供直觉，表格建立递推，折线与柱形分别揭示过程及节点差值，公式压缩已经看到的关系，结尾回到命题。采用现有R5成片，不重新选案。

初始100，每轮按现有总量增加1%，对照每轮固定加1；均不追加外部投入。唯一模型在`scenes/model.ts`。雪球是寓言，不把体积映射成1%或把模型当现实预测。数字论证及公式处保留可读的模型口径。

## 视觉与运动

近黑舞台、米白与暖金，白色表示固定增量对照、金色表示按总量增长。中文M2V Sans，数字M2V Inter，公式使用登记KaTeX字体。大数、大字、横向动作、表格、开放坐标交替形成尺度与阅读方式变化，不做同构卡片。

主入场easeOutExpo、场内及跨场easeInOutCubic；起势、移动、减速、落定与阅读分开。每拍一个主要焦点，动作和字幕允许有用途的重叠。所有状态按帧纯求值，随机使用固定种子；无挂钟、自走动画或前帧累积。

## 逐场表

| 时间 | 可见事件及新增认识 | 衔接与观察重点 |
|---|---|---|
| 0–3秒 | 初始100、每轮1%、数字滚动到第8轮，提出100轮后会怎样 | 先建立问题，不先泄露答案；数字锁定后焦点交给小球 |
| 3–7秒 | 两行大字“让过去的成果 / 参与下一次”，球穿行并落定 | 字成为路径和落点；球最终落向雪面 |
| 7–11秒 | 雪球卷雪增大，9.6秒完成并局部释放；10秒起收拢上移 | 10.467秒100.00显现，10.6秒完全显示；停至11秒，在同一位置接表格首行；不使用整屏白擦 |
| 11–17秒 | 表格逐行出现101/+1、102.01/+1.01、103.03/+1.02 | 区分总量与新增，上一轮进入下一轮基础；103.03接向坐标 |
| 17–23秒 | 同起点双线先接近后分离，终点270.48/200 | 轮次匀速推进，坐标比例真实；结果可读时再释放 |
| 23–29秒 | 10/50/100轮三组柱形，差0.46/14.46/70.48 | 零基准、统一比例；差值有独立行；100轮的100抬向上标 |
| 29–35秒 | 初始量、增长因子、指数依次公开，答案270.48锁定 | 固定公式占位宽度，实际KaTeX字形量测落点；强释放后结果仍可读 |
| 35–40秒 | 数字小数点接球，结论与开场回认 | 粒子收势后文字留下，不再加新例子 |

## 实现与取舍

复用已有Counter、ChartLine/ChartMarker、Text、Snowball、Burst/Impact及MathFormula。ChartLine沿用已锁定d3-shape 3.2.0（ISC），公式沿用KaTeX 0.19.1（MIT），逐帧合成沿用Remotion 4.0.526及现有许可配置。既有纯时间组件已满足需求，无新增依赖、同类组件或自走时间线。柱形矩形仅做本片量到高度映射。R5源码迁移时不改变动作和图形。

保留四处整屏Impact事件起点：2.700、22.067、27.467、33.100秒，分别对应数字锁定、曲线结果、柱形结果和公式答案；9.6秒雪球只保留局部接触Burst。事件起点不是光效面积/亮度峰值。未实现提案中的窄带扫光，不声称每次释放均使用不同新技术。

第10秒修复换取数字认回与表格承接，代价是失去原满屏近景冲击及球内数字的直接关联。这是有针对性的取舍，不代表慢转场普遍更好。近期设计过程及复盘见[CASE_STUDY](CASE_STUDY.md)，参考采用范围见[记录](style-reference.md)。

## 逐场细节说明

以下为现有 R5 源码的细节记录补充，未新增效果、重渲媒体或重新作出验收结论。帧、曲线与参数以对应源码和事件为唯一执行源。

| 场景 | 已有细节、用途与取舍 | 实现引用 |
|---|---|---|
| 数字开场 | 数字随轮次变化，滚动期两层残影在锁定前退出；数字退出与标题进入分开，球从数字位置出发接棒；无角色表情 | [hook.tsx](scenes/hook.tsx) 的 number-lock、title-start |
| 大字与球 | 球沿弧线进入大字区域，再做高度受限的两次起落；局部 Burst 对应落点，最终落向雪面；采用位置变化，不额外声称有压扁形变 | [hook.tsx](scenes/hook.tsx) 的 handoff、bounce、fall |
| 雪球 | 半径与位置来自同一进度，接触释放来自对应事件；结束时球壳收拢并退出，地面先让位，100.00 在表格首行位置出现并停留 | [hook.tsx](scenes/hook.tsx) 的 snow-impact、snow-wipe、handoffEnd；[snow.tsx](scenes/snow.tsx) |
| 表格 | 当前行局部变亮、位置落定，曲线与小球把上一行关联到下一行；103.03 沿弧线移向折线起点；本例没有加速滚动，不把参考片效果写为已实现 | [proof.tsx](scenes/proof.tsx) 的 Ledger、flight |
| 双线 | 轮次数匀速推进，路径与端点数字从同一模型求值；结果出现后才释放，线退场时端点球沿弧线落向第一柱 | [proof.tsx](scenes/proof.tsx) 的 Curve、curve-flash、drop |
| 柱形 | 各组错峰生长，同组柱高与数字使用同一进度；完成后公开独立差值行，100轮的100抬向上标；本例柱高无回弹，也无球持续随柱顶上升 | [proof.tsx](scenes/proof.tsx) 的 Bars、bar-flash、exit |
| 公式 | 占位保留排版宽度，指数接入按实际字形落点；答案先计数锁定再释放，局部 Burst 与整屏 Impact 有各自事件，不能遮掉结论 | [resolution.tsx](scenes/resolution.tsx) 的 tex、answer-lock、answer-release |
| 回扣 | 小数点位置生成球并沿弧线移到句末，结论短促尺度强调后静止；保留阅读，不再引入新例子或环境运动 | [resolution.tsx](scenes/resolution.tsx) 的 dot、closing-land、titleScale |

## 整场编排的适用边界

当前R5已用球与大字互动、表格到图线到柱形、数字到上标及局部/整屏不同释放组织观看任务，源码引用见上表。它没有为每句说明制作翻转图标，也不代表本轮文字图标丰富度已实现。现有四处整屏Impact是本片事件选择，不是所有作品的配额；新风格允许按用途多次硬切与冲击切镜，不要求本例补做无用途特效。此次仅同步说明与新GUIDE造成的指纹失效，旧媒体/旧评审不授权修改后的当前准备；恢复与重新prepare后验证技术契约，未声称重新完成视觉终审。

## 当前制作合同

### 按观看任务核对现有实现

本节仅核对上表引用的R5源码，未生成新媒体或补造评审。大字段的150/174字号承担主题，表格64/70数字承担比较，公式使用110字号的KaTeX；这些是本片实际层级，不是推荐给所有无旁白作品的字号。表格用“现有总量/本轮新增”区分递推，曲线用同起点分离呈现过程，柱形以独立差值行解释节点差距，公式用指数接入压缩关系，各有不同观看任务。

球在大字段组织视线与落点，在表格/曲线间接棒；没有为每个条件增加图标。参考窗口及实际采用范围仍以[style-reference.md](style-reference.md)为准，不能用其某一段替代其他观看任务的对照，也不能用本节源码说明证明实时节奏或参考目标已通过。后续明确重制应先选择当轮最弱关系试制；本次不追溯重渲。

```m2v-checkpoints
{
  "version": 2,
  "cycleId": "compound-connect-r5-example-20261105",
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "reviewPlan": {
    "basis": "采用R5八节拍成片。完整试制含开场数字/大字/雪球，以及表格→折线→柱形；最后公式和结论独立终审覆盖。无新增静态目标图风险，提案图不作已通过目标图。",
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
              "text": "差距，从0.46扩大到70.48。",
              "window": [
                388,
                518
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
