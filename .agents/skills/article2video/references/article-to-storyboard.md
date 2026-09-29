# 文章生成场景树分镜

生成不是一次性套模板，而是八个可复核阶段。最终只有 `storyboard.json` 进入运行时，中间推理不构成渲染依赖。

1. **内容分镜**：提炼核心判断，拆出口播与短硬的画面文案；时长由口播按中文每秒约 4–5 字反推。
2. **导演简报**：在选原语前确定核心冲突、观众认知转折、情绪曲线、视觉母题和作品风格包；不得把原语类型当作导演策略。
3. **视频级视觉策略**：确定母题、构图倾向、密度、节奏及禁止复用项，写入 `visualDirection`。
3. **逐幕视觉转译**：为每幕先声明信息关系、焦点、构图、密度、情绪，以及**视觉论证**——受控视觉模式、核心论点、无正文视觉表达、主要视觉对象与动效语义。这一步必须在选原语之前完成，且无正文视觉表达要写「移除标题与正文后仍能看见的关系或变化」。
4. **推理拆分与节拍编排**：把该幕口播切成若干**语义段**（一段一个推理步骤），每段绑定一条 beat；beat 的 `action` 从受控动作里选真正改变状态或关系的那一个，`meaning` 写清这一步解释了什么。分段口播与字符串口播互斥，见[分镜脚本结构](storyboard-schema.md)。
5. **动画阶段与镜头**：先按 beat 规划 `establish` / `change` / `result` / `settle`，再选择节点组与错峰；非静态镜头段必须说明服务哪个 beat 与焦点，不能用整幕持续漂移装饰画面。
5. **场景编排**：默认查 [视觉原语目录](primitive-catalog.md)，用布局、内容和图形原语组合。若原语能画出静态对象、却无法表达这幕需要的状态变化、对象编排或镜头揭示，可以按明确叙事理由选择作品级代码场景；同时编写与分镜对应的 `motion-design.md` 动作脚本，引用 beat id 而不复制口播。代码场景须符合[确定性与探针契约](code-scenes.md)，不得仅为装饰性复杂度绕过场景树。
6. **节点动效**：以稳定节点 id 绑定具名配方；动效不增删节点、不改变冻结布局。
7. **全片视觉叙事自检**：严格校验会执行文字幕占比、连续文字幕与非文字模式覆盖的版本化预算（见下），以及动画论证 A 系列（见下）。
8. **闭环验收**：严格校验、布局指纹多样性检查、契约探针、K/M 闸门、V 系列与 A 系列报告和人工视觉量表。

失败时从最晚且最局部的阶段返工：文字问题回内容分镜，构图雷同回视觉意图或场景树，动效问题只改 `motions`，节拍问题只改分段口播与 `beats`。不得为修复布局擅自改变文章判断。

## 视觉论证字段

逐幕 `visualIntent` 除既有的关系/焦点/构图/密度/情绪外，还必须声明：

| 字段 | 含义 | 要求 |
| --- | --- | --- |
| `mode` | 受控视觉模式 | `metaphor`、`process`、`comparison`、`cycle`、`chart`、`image`、`typography` 之一 |
| `claim` | 该幕唯一核心论点 | 一句话，非空 |
| `showWithoutText` | 无正文视觉表达 | 描述移除标题与正文后仍能看见的关系或变化；不得逐字复述 `claim`，也不得写成「显示/呈现 + 论点」 |
| `primaryObject` | 承担论证的主要视觉对象 | 具体到节点或结构，而不是「画面」 |
| `motionMeaning` | 主要动效推进了什么理解 | 说不出就删掉该动效 |

`typography` 表示主要论点依赖文字成立，是唯一的文字模式。背景形状、分隔线、装饰符号、单个数值，以及只承载文字的表面都**不**使文字幕变成非文字模式。

## 论证型图形的判据

确定性脚本只承认九类**结构证据**：

- `chart`：图表承担数据关系；
- `image`：受控图片承担画面信息；
- `connector`：连接关系承担推进或因果；
- `radial`：圆周关系布局（≥2 个内容子节点）承担循环或关系；
- `flow`：阶段推进顺序（≥2 个语义对象，画出方向连接与当前阶段）；
- `cycle`：闭环阶段（≥2 个语义对象，画出轨道与当前阶段）；
- `timeline`：阶段进度（≥2 个语义对象，画出进度轴与当前阶段）；
- `gauge`：单一量级指针；
- `pictogram`：单位化量级（用受控图标表示比例）。

三个关系容器与 `radial` 一样要求**至少两个语义对象**：一根箭头加一个阶段只是加了个箭头，
不构成关系。布局原语（`stack`/`row`/`column`/`split`/`grid`/`overlay`/`group`）、
`surface`、`shape`、`icon` 与单个 `number` 都是包装或文字：把文字卡片换一层布局包装、
加两个图标、套一层 `group`，都不会让它成为论证型图形。声明了非 `typography` 模式却拿不出
上述证据的幕，严格校验会按「声明与结构矛盾」报错并定位到该幕。

「移除文字后是否仍然成立」「图形是否真的承担论证」仍由人或视觉模型在联系表上判断
（`review.py` 的 V6）；脚本只报告结构证据，不假装理解语义。

## 原语不足时禁止退化

当 `showWithoutText` 无法映射到目录原语时，**停在视觉转译阶段**并输出能力缺口，可选路径只有三条：

1. 重新构思视觉隐喻，直到能用现有原语表达；
2. 按注册表契约扩展跨作品通用原语；
3. 确属作品特例时使用合规代码场景（见 [代码场景](code-scenes.md)）。

不得把该幕改写成「标题 + 文字卡片 + 图标」后继续宣称原来的视觉模式。严格校验的结构反证会抓住这类退化。

## 全片视觉叙事预算（严格校验）

`validate.py --strict` 执行版本化预算（阈值见 `a2v/visual_narrative.py` 的 `RULE_VERSION`）：

- 文字幕数量不超过 `ceil(场景数 × 30%)`；
- 相邻两幕不得都是文字幕；
- 八幕及以上至少 3 种非文字视觉模式，少于八幕至少 2 种；
- 声明非文字模式却无结构证据的幕报错；
- 逐幕缺少上述论证字段报错。

v1/v2 分镜和缺少 v3 必填字段的分镜在普通与严格校验、预览、配音准备、评审和渲染中统一拒绝。`--strict` 另外执行全片质量门槛。

## 动画论证（A 系列）

结构证据只说明「画面里有没有论证型图形」，说不清「这些图形动起来有没有在解释论点」。
声明了分段口播的幕还要过动画论证闸门（口径与 `a2v/animation_review.py` 的
`RULE_VERSION` 一致，机检部分与 `review.py` 同源）：

- **A1 节拍覆盖**：每个口播段绑定到存在的 beat，每条 beat 至少被一段引用，同一 beat 的引用相邻；
- **A2 含义声明**：每条 beat 的 `meaning` 非空，且不是口播原文的复述、也不只是动作名；
- **A3 状态或关系变化**：非文字幕至少两条 beat，且至少一条动作真正改变对象状态或关系
  （`establish` / `highlight` 只是出现或更醒目，不算）；
- **A4 字幕同步**：有声时字幕 cue 边界与画面 beat 边界共用同一份时间轴（逐帧允许 ±1 帧取整差）；
- **A5 结尾停留**：最后一条 beat 完成后至少留 12 帧稳定阅读时间；
- **A7 单一焦点**：任一帧最多一个焦点对象；
- **A8 稳定结束**：所有入场配方在幕尾前 12 帧结束。

A6（装饰动画裁决）由人或视觉模型在 `review.md` 里写结论，缺失即「待评审」，
既不会伪造成脚本错误，也不会被当成默认合格。无声幕与无媒体时的 A4 如实记为「跳过」——**跳过不等于通过**。判据、错误措辞与人工写法见
[设计宪法](design-constitution.md)的「动画论证闸门（A1–A8）」与
[视觉评审量表](visual-review-rubric.md)。

## 正反例

两个例子都只含抽象内容，可直接粘进 `storyboard.json` 后用严格校验复核。

### 反例：文字卡片冒充图形论证

三幕都声明了图形模式，实际画面只有标题、正文、图标和承载文字的表面；严格校验会因「声明与结构矛盾」和预算超限失败。

```json
{
  "version": 3,
  "schemaVersion": 3,
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "title": "视觉转译反例",
  "visualDirection": {
    "motif": "结构关系逐步显形",
    "compositionBias": "mixed",
    "density": "balanced",
    "rhythm": "steady",
    "avoid": []
  },
  "scenes": [
    {
      "id": "machine",
      "type": "title",
      "durationInFrames": 90,
      "data": {
        "text": "人不是机器",
        "subtitle": "机器可以一直满负荷"
      },
      "visualIntent": {
        "relation": "contrast",
        "focus": "text",
        "composition": "split",
        "density": "balanced",
        "tone": "tense",
        "mode": "comparison",
        "claim": "人不是可以一直满负荷运转的机器",
        "showWithoutText": "两块并列表面一暗一亮，对比说明人与机器不同",
        "primaryObject": "两块并列的文字表面",
        "motionMeaning": "卡片依次升起，把两种状态摆在一起"
      },
      "sceneTree": {
        "id": "root",
        "type": "column",
        "children": [
          {
            "id": "machine-title",
            "type": "text",
            "contentRef": "data.text",
            "role": "headline"
          },
          {
            "id": "machine-row",
            "type": "row",
            "gap": "sm",
            "children": [
              {
                "id": "machine-card-1",
                "type": "surface",
                "children": [
                  {
                    "id": "machine-icon-1",
                    "type": "icon",
                    "icon": "check"
                  },
                  {
                    "id": "machine-card-1-text",
                    "type": "text",
                    "contentRef": "data.subtitle",
                    "role": "body"
                  }
                ]
              },
              {
                "id": "machine-card-2",
                "type": "surface",
                "state": "focus",
                "children": [
                  {
                    "id": "machine-icon-2",
                    "type": "icon",
                    "icon": "cross"
                  },
                  {
                    "id": "machine-card-2-text",
                    "type": "text",
                    "contentRef": "data.subtitle",
                    "role": "body"
                  }
                ]
              }
            ]
          }
        ]
      },
      "motions": [
        {
          "target": "machine-title",
          "recipe": "reveal",
          "durationFrames": 20,
          "phase": "change"
        }
      ],
      "renderer": {
        "kind": "tree"
      },
      "camera": {
        "shot": "wide",
        "composition": "center",
        "depth": "flat",
        "focus": "machine-title",
        "segments": [
          {
            "kind": "hold",
            "phase": "establish",
            "focus": "machine-title",
            "intensity": 0
          },
          {
            "kind": "settle",
            "phase": "settle",
            "focus": "machine-title",
            "intensity": 0
          }
        ]
      }
    },
    {
      "id": "fatigue",
      "type": "diagram",
      "durationInFrames": 90,
      "data": {
        "title": "持续疲劳导致产出下降",
        "body": "恢复不足，注意力也跟着下降"
      },
      "visualIntent": {
        "relation": "cause",
        "focus": "text",
        "composition": "full",
        "density": "balanced",
        "tone": "tense",
        "mode": "process",
        "claim": "持续疲劳通过恢复不足把产出压下去",
        "showWithoutText": "标题下面跟着一段说明，读完全部文字才能得到结论",
        "primaryObject": "标题与说明两块文字",
        "motionMeaning": "说明文字随后淡入，补上因果的解释"
      },
      "sceneTree": {
        "id": "root",
        "type": "stack",
        "children": [
          {
            "id": "fatigue-title",
            "type": "text",
            "contentRef": "data.title",
            "role": "headline"
          },
          {
            "id": "fatigue-body",
            "type": "text",
            "contentRef": "data.body",
            "role": "body"
          }
        ]
      },
      "motions": [
        {
          "target": "fatigue-title",
          "recipe": "reveal",
          "durationFrames": 20,
          "phase": "change"
        }
      ],
      "renderer": {
        "kind": "tree"
      },
      "camera": {
        "shot": "wide",
        "composition": "center",
        "depth": "flat",
        "focus": "fatigue-title",
        "segments": [
          {
            "kind": "hold",
            "phase": "establish",
            "focus": "fatigue-title",
            "intensity": 0
          },
          {
            "kind": "settle",
            "phase": "settle",
            "focus": "fatigue-title",
            "intensity": 0
          }
        ]
      },
      "transition": {
        "kind": "dissolve",
        "meaning": "按文稿顺序进入下一步论证"
      }
    },
    {
      "id": "output",
      "type": "chart",
      "durationInFrames": 90,
      "data": {
        "title": "连续三周的产出",
        "body": "一周比一周低"
      },
      "visualIntent": {
        "relation": "cause",
        "focus": "text",
        "composition": "full",
        "density": "balanced",
        "tone": "tense",
        "mode": "chart",
        "claim": "随着疲劳累积，周产出逐周下滑",
        "showWithoutText": "两行文字上下排列，下滑这件事只能从文字里读出来",
        "primaryObject": "标题与说明两块文字",
        "motionMeaning": "说明文字淡入，把下滑的结论说出来"
      },
      "sceneTree": {
        "id": "root",
        "type": "stack",
        "children": [
          {
            "id": "output-title",
            "type": "text",
            "contentRef": "data.title",
            "role": "headline"
          },
          {
            "id": "output-body",
            "type": "text",
            "contentRef": "data.body",
            "role": "body"
          }
        ]
      },
      "motions": [
        {
          "target": "output-title",
          "recipe": "reveal",
          "durationFrames": 20,
          "phase": "change"
        }
      ],
      "renderer": {
        "kind": "tree"
      },
      "camera": {
        "shot": "wide",
        "composition": "center",
        "depth": "flat",
        "focus": "output-title",
        "segments": [
          {
            "kind": "hold",
            "phase": "establish",
            "focus": "output-title",
            "intensity": 0
          },
          {
            "kind": "settle",
            "phase": "settle",
            "focus": "output-title",
            "intensity": 0
          }
        ]
      },
      "transition": {
        "kind": "dissolve",
        "meaning": "按文稿顺序进入下一步论证"
      }
    }
  ],
  "directingVersion": 1,
  "directingBrief": {
    "thesis": "视觉转译反例",
    "audienceShift": "从只看文字判断转向观察结构证据",
    "emotionalArc": [
      "提出问题",
      "揭示关系"
    ],
    "visualMotif": "结构关系逐步显形",
    "stylePack": "editorial",
    "avoid": []
  },
  "visual": {
    "theme": "dark",
    "preset": "keynote"
  }
}```

### 正例：图形承担论证

同一组论点改用连接关系与图表承担：因果链由 `connector` 串起，下滑趋势由 `chart` 的柱高差说出来，文字只留短标签。

```json
{
  "version": 3,
  "schemaVersion": 3,
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "title": "视觉转译正例",
  "visualDirection": {
    "motif": "结构关系逐步显形",
    "compositionBias": "mixed",
    "density": "balanced",
    "rhythm": "steady",
    "avoid": []
  },
  "scenes": [
    {
      "id": "machine",
      "type": "title",
      "durationInFrames": 90,
      "data": {
        "text": "人不是机器"
      },
      "visualIntent": {
        "relation": "focus",
        "focus": "text",
        "composition": "center",
        "density": "sparse",
        "tone": "tense",
        "mode": "typography",
        "claim": "人不是可以一直满负荷运转的机器",
        "showWithoutText": "整屏只有一块居中文字，四周留白把这句话单独托住",
        "primaryObject": "居中的标题文字块",
        "motionMeaning": "标题淡入，让这句判断在留白里停一下"
      },
      "sceneTree": {
        "id": "root",
        "type": "stack",
        "children": [
          {
            "id": "machine-text",
            "type": "text",
            "contentRef": "data.text",
            "role": "headline"
          }
        ]
      },
      "motions": [
        {
          "target": "machine-text",
          "recipe": "reveal",
          "durationFrames": 24,
          "phase": "change"
        }
      ],
      "renderer": {
        "kind": "tree"
      },
      "camera": {
        "shot": "wide",
        "composition": "center",
        "depth": "flat",
        "focus": "machine-text",
        "segments": [
          {
            "kind": "hold",
            "phase": "establish",
            "focus": "machine-text",
            "intensity": 0
          },
          {
            "kind": "settle",
            "phase": "settle",
            "focus": "machine-text",
            "intensity": 0
          }
        ]
      }
    },
    {
      "id": "fatigue",
      "type": "diagram",
      "durationInFrames": 120,
      "data": {
        "title": "疲劳怎么吃掉产出",
        "steps": [
          "持续加班",
          "恢复不足",
          "产出下降"
        ]
      },
      "visualIntent": {
        "relation": "cause",
        "focus": "shape",
        "composition": "full",
        "density": "balanced",
        "tone": "tense",
        "mode": "process",
        "claim": "持续疲劳通过恢复不足把产出压下去",
        "showWithoutText": "三块状态被两支箭头依次串起，箭头方向说明前一步导致后一步",
        "primaryObject": "三段因果链与两支连接箭头",
        "motionMeaning": "箭头逐段画出，把「加班—恢复不足—产出下降」的传导演一遍"
      },
      "sceneTree": {
        "id": "root",
        "type": "column",
        "gap": "lg",
        "children": [
          {
            "id": "fatigue-title",
            "type": "text",
            "contentRef": "data.title",
            "role": "title"
          },
          {
            "id": "fatigue-chain",
            "type": "row",
            "align": "center",
            "gap": "sm",
            "children": [
              {
                "id": "fatigue-step-1",
                "type": "surface",
                "children": [
                  {
                    "id": "fatigue-step-1-text",
                    "type": "text",
                    "contentRef": "data.steps[0]",
                    "role": "body"
                  }
                ]
              },
              {
                "id": "fatigue-arrow-1",
                "type": "connector",
                "direction": "ltr"
              },
              {
                "id": "fatigue-step-2",
                "type": "surface",
                "children": [
                  {
                    "id": "fatigue-step-2-text",
                    "type": "text",
                    "contentRef": "data.steps[1]",
                    "role": "body"
                  }
                ]
              },
              {
                "id": "fatigue-arrow-2",
                "type": "connector",
                "direction": "ltr"
              },
              {
                "id": "fatigue-step-3",
                "type": "surface",
                "state": "focus",
                "children": [
                  {
                    "id": "fatigue-step-3-text",
                    "type": "text",
                    "contentRef": "data.steps[2]",
                    "role": "body"
                  }
                ]
              }
            ]
          }
        ]
      },
      "motions": [
        {
          "target": "fatigue-title",
          "recipe": "reveal",
          "durationFrames": 20,
          "phase": "change"
        },
        {
          "target": "fatigue-arrow-1",
          "recipe": "draw",
          "durationFrames": 16,
          "phase": "change"
        },
        {
          "target": "fatigue-arrow-2",
          "recipe": "draw",
          "durationFrames": 16,
          "phase": "change"
        }
      ],
      "renderer": {
        "kind": "tree"
      },
      "camera": {
        "shot": "wide",
        "composition": "center",
        "depth": "flat",
        "focus": "fatigue-title",
        "segments": [
          {
            "kind": "hold",
            "phase": "establish",
            "focus": "fatigue-title",
            "intensity": 0
          },
          {
            "kind": "settle",
            "phase": "settle",
            "focus": "fatigue-title",
            "intensity": 0
          }
        ]
      },
      "transition": {
        "kind": "dissolve",
        "meaning": "按文稿顺序进入下一步论证"
      }
    },
    {
      "id": "output",
      "type": "chart",
      "durationInFrames": 120,
      "data": {
        "title": "连续三周的产出（示意）",
        "values": [
          {
            "label": "第一周",
            "value": 10
          },
          {
            "label": "第二周",
            "value": 7
          },
          {
            "label": "第三周",
            "value": 4
          }
        ]
      },
      "visualIntent": {
        "relation": "cause",
        "focus": "chart",
        "composition": "full",
        "density": "balanced",
        "tone": "tense",
        "mode": "chart",
        "claim": "随着疲劳累积，周产出逐周下滑",
        "showWithoutText": "三根柱子一周比一周矮，柱高差说明产出在持续下滑",
        "primaryObject": "三根产出柱与它们递减的高度",
        "motionMeaning": "柱子依次落下，把「一周比一周低」的下滑趋势演出来"
      },
      "sceneTree": {
        "id": "root",
        "type": "column",
        "gap": "lg",
        "children": [
          {
            "id": "output-title",
            "type": "text",
            "contentRef": "data.title",
            "role": "title"
          },
          {
            "id": "output-chart",
            "type": "chart",
            "contentRef": "data.values",
            "chart": "bar",
            "schematic": true
          }
        ]
      },
      "motions": [
        {
          "target": "output-title",
          "recipe": "reveal",
          "durationFrames": 20,
          "phase": "change"
        },
        {
          "target": "output-chart",
          "recipe": "reveal",
          "durationFrames": 30,
          "phase": "change"
        }
      ],
      "renderer": {
        "kind": "tree"
      },
      "camera": {
        "shot": "wide",
        "composition": "center",
        "depth": "flat",
        "focus": "output-title",
        "segments": [
          {
            "kind": "hold",
            "phase": "establish",
            "focus": "output-title",
            "intensity": 0
          },
          {
            "kind": "settle",
            "phase": "settle",
            "focus": "output-title",
            "intensity": 0
          }
        ]
      },
      "transition": {
        "kind": "dissolve",
        "meaning": "按文稿顺序进入下一步论证"
      }
    }
  ],
  "directingVersion": 1,
  "directingBrief": {
    "thesis": "视觉转译正例",
    "audienceShift": "从只看文字判断转向观察结构证据",
    "emotionalArc": [
      "提出问题",
      "揭示关系"
    ],
    "visualMotif": "结构关系逐步显形",
    "stylePack": "editorial",
    "avoid": []
  },
  "visual": {
    "theme": "dark",
    "preset": "keynote"
  }
}```

## 生成纪律

- 画面文案不是口播复制；无来源数值必须让数字/图表原语显示「示意」。
- 内容通过 `contentRef` 引用 `data`，布局节点不保存默认文案。
- 只用目录登记的原语、枚举属性和具名动效；不得生成代码、自由 CSS、任意坐标或外部包。
- 同一幕节点 id 唯一；修改未变节点时保留 id，保证动效和探针稳定。
- 连续页面不能只有文字不同；严格校验会把完全同构作为失败，近似复用交给人工复核。
- 原语确有跨作品基础能力缺口时才扩展注册表；不要为一篇文章增加整页组件。
- 分段口播的每一段都要绑定一条 beat，且**动作要真的改变状态或关系**；
  一条 beat 的目标原语必须都支持该动作（支持清单见
  [视觉原语目录](primitive-catalog.md)）。

## 节拍反例：中性动作堆成的「动画」

下面这一幕的字段、原语与分段都合规，但它过不了节拍质量规则：每一段口播配的都是
`establish`（出现）或 `highlight`（更醒目）。观众看到的是元素依次入场，不是一次推理。
严格校验会报：

```
[error] scenes[1].beats: 至少一个 beat 要改变对象状态或关系（当前动作：establish、highlight）；
只有 establish/highlight 的画面是依次出现的卡片，不是一次推理
```

```json
{
  "id": "cards",
  "type": "diagram",
  "renderer": "tree",
  "durationInFrames": 180,
  "narrationSegments": [
    { "id": "n1", "text": "先看第一张卡片。", "beatId": "b1" },
    { "id": "n2", "text": "再看第二张卡片。", "beatId": "b2" },
    { "id": "n3", "text": "最后把它们都强调一遍。", "beatId": "b3" }
  ],
  "beats": [
    { "id": "b1", "action": "establish", "targets": ["card-a"], "meaning": "让第一张卡片出现" },
    { "id": "b2", "action": "establish", "targets": ["card-b"], "meaning": "让第二张卡片出现" },
    { "id": "b3", "action": "highlight", "targets": ["card-c"], "meaning": "把第三张卡片提亮" }
  ],
  "data": { "title": "三张卡片", "items": ["第一项", "第二项", "第三项"] },
  "visualIntent": {
    "relation": "collection",
    "focus": "shape",
    "composition": "center",
    "density": "balanced",
    "tone": "neutral",
    "mode": "process",
    "claim": "三件事按顺序出现",
    "showWithoutText": "三张卡片排成一列依次出现，位置说明顺序",
    "primaryObject": "三张卡片表面",
    "motionMeaning": "卡片依次入场"
  },
  "sceneTree": {
    "id": "root",
    "type": "flow",
    "direction": "ttb",
    "gap": "md",
    "children": [
      { "id": "card-a", "type": "surface", "children": [{ "id": "card-a-text", "type": "text", "contentRef": "data.items[0]", "role": "body" }] },
      { "id": "card-b", "type": "surface", "children": [{ "id": "card-b-text", "type": "text", "contentRef": "data.items[1]", "role": "body" }] },
      { "id": "card-c", "type": "surface", "children": [{ "id": "card-c-text", "type": "text", "contentRef": "data.items[2]", "role": "body" }] }
    ]
  },
  "motions": [
    { "targets": ["card-a", "card-b", "card-c"], "recipe": "rise", "beatId": "b1", "stagger": { "direction": "forward", "frames": 12 }, "durationFrames": 20 }
  ]
}
```

修法只有两条：换成真正改变状态或关系的动作（`connect` 建立关系、`transform` 换形态、
`accumulate` 让量级增长……），或者承认这一幕就是文字幕、把 `mode` 改成 `typography`。
把「依次出现」当成「论证过程」，正是 A3 要拦的那一类退化。

可运行的**正例**见 [`examples/narration-beats/`](../../../../examples/narration-beats/storyboard.json)：
五幕覆盖 `flow`、`cycle`、`timeline`、`gauge`、`pictogram` 五个中层原语，
每段口播都绑定一条会改变状态或关系的 beat，严格校验与 A1–A5、A7、A8 全部通过
（A4 无声跳过、A6 待人工裁决）。

## v1/v2 分镜处理

v1/v2 分镜不能进入预览或渲染。项目不提供迁移工具；请以文章内容为依据，按 v3 结构重新编排并完成严格校验与视觉评审。
