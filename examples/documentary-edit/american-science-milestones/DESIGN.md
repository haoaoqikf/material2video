# 视觉设计：从电报到大模型

本轮合并设计记录和执行引用，未重新渲染或补造独立评审；历史观察只作原版本依据。来源与许可继续按 [SOURCES.md](SOURCES.md) 及既有登记执行。

## 全片原则

### 核心体验与传播语境

面向中国普通观众，默认抖音横屏手机播放。画面1920×1080、60 fps、总长30秒（1800帧），无旁白、无配乐、无音效。目标是在短时观看中展示美国主导或参与的十项科学与技术高光，中文读者能迅速看懂各项名称与贡献，同时保留全球累积、合作和贡献边界。

前两秒作为降低观众流失的审美考虑：首帧即见登月档案中的人物/舱体和地表，叠加“美国科学高光时刻”，副标题说明“美国主导或参与的十项科技节点”。开场不用空镜或抽象铺垫；后续十项兑现这一主题。无真实平台数据时不推算或记录实际2秒跳出率。

时间预算：开场2秒；主体26秒，十项依题材需要分配为2、2、3、2、2.5、2.5、3、2.5、2、4.5秒；片尾署名2秒。总计30秒。先删重复信息并重组镜头，不用加速旧片替代重制。中文名称和一句贡献优先；ENIAC与ARPANET仅在首次出现时作小字辅助。

核心感受是看见信号、计算与知识能力不断扩展；历史档案、实物和人物是主要视觉主体，机制示意只解释具体关系。审美禁区：幻灯片式固定模板、冗长标题铺垫、英文缩写成为理解前提、炫光遮档案、将美国参与夸大为单国独创、暗示里程碑之间未经证实的直接因果。

手机复核按852×393 CSS像素屏幕，画面等比显示699×393，同时检查1920×1080原帧和160×90缩略图；未取得平台UI官方遮挡数据，只报告图面可读性，不声称平台实测。

### 视觉方向

| 维度 | 档案纪录片（采用） | 科技展厅（放弃） |
|---|---|---|
| 构图 | 历史主体先占画面，再以简图解释 | 每项套用统一标题框和展示台 |
| 信息 | 大号中文名称、短贡献句；英文缩写仅作首次小字辅助 | 中英并列、长说明常驻 |
| 动作 | 动作展现信号传播、设备尺度、节点连接或数据生成 | 卡片轮换、标题滑入和通用扫描 |
| 色彩材质 | 保留档案原光比，墨黑、暖白与少量铜色/冷青连接 | 全片统一蓝色发光数字空间 |
| 选择理由 | 档案差异本身提供可信度和视觉变化，主题通过内容而非口号铺陈 | 视觉统一但会压平材料差异，且易复现PPT逐页观感 |




主体总计1560帧；开场120帧；片尾120帧。每一项只保留一个主动作与一条贡献信息。两秒项使用一眼可辨的实物或档案和短句，不塞进原理说明。顺序和贡献边界与旧版一致，视觉线索不表达直接因果。

### 四张基准

| 基准 | 判断 | 本版检查时间 |
|---|---|---|
| 开场 | 第0帧即可辨登月主体与片题；前两秒主题明确，不依赖英文 | 00:00–00:02 |
| 核心：登月 | 档案运动是主体；中文名称和一句意义不遮脸/动作 | 00:16–00:19 |
| 普通信息：晶体管 | 实物先识别，结构示意不争夺主体 | 00:13.5–00:16 |
| 大语言模型 | 产品示意具体易辨，不遮蔽“全球研究积累”边界；图标原样、示意标识清楚 | 00:25–00:28 |
| 片尾 | 只保留一份极简署名；手机尺寸下可读，许可描述完整 | 00:28–00:30 |

复核源帧1920×1080、横屏手机699×393和160×90缩略图。检查完整观众可见文案与档案自带文字。署名两行保留晶体管/阿帕网素材名称、作者、各自许可、裁切/调色改动和本片CC BY-SA 4.0。ChatGPT 官方图标只作为示意交互界面的产品识别，使用边界记录在作品材料中。详细出处与许可记录保留在[SOURCES.md](SOURCES.md)。

### 声音与交付约束

全片无旁白、配乐、音效与素材原声。技术链路若写入静音音轨，数字峰值为0；如无音轨则符合本作品要求。不得在观众可见文字中出现内部文件名、仓库路径或材料查阅提示。片尾署名集中一处，2秒内需可读。

### 画幅、配色、构图与声音

- **画幅：** 1920×1080 横屏、60 fps；以横屏手机 699×393 显示尺寸检查字号、主体占比和播放器边缘风险。
- **配色：** 保留各历史素材的原生色调，以墨黑、暖白和少量铜色/冷青信息线统一全片；不以高亮装饰覆盖素材。
- **构图：** 档案主体占据主要画面区域，短中文信息稳定落在左下安全位置；需要解释关系时才加入脉冲、波形、节点或序列等图形，避免每项套同一张文字卡。
- **声音：** 无旁白、配乐、音效及素材原声；静音轨峰值为0。

最终帧序列至少每0.5秒覆盖；镜头交界前后0.5秒以0.1秒加密，前两秒和主要视觉峰值额外复核。记录版本指纹与SHA、开场前两秒判断依据、手机显示尺寸、阅读/信息推进、静音和来源审计。片尾两秒与LLM镜头均需额外检查。仅在实际取得平台发布数据时才用于之后的开场复盘；未取得时不报告跳出率。

### 后续设计与评审应用（2026-10-23，非重制记录）

本节仅示范后续采用[分层精修](../../../.agents/skills/material2video/references/production-workflow.md#分层精修)和[诊断适用性](../../../.agents/skills/material2video/references/visual-review-rubric.md#诊断测试与适用性)的方式；未新增试制、候选比较或成片复核，不改写既有交付结论。

- 设计重点：以档案的真实质感及信号、计算、知识能力的扩展组织体验；三案可比较档案并列、尺度揭示、文字关系编排，不能只换色。核心段落与辅助段落的强弱在后续制作时间线上确定。
- 评审重点：无声是本片契约，按无声目标检查；档案静止与中文名称是有效载体候选，不因静止或去文字后信息损失直接否决。仍须检验30秒内的阅读、史实边界和必要署名。
- 返工取舍：比较删短／重排是否损失档案观察与历史跨度感；不能用缓慢推镜替代内容推进。

### 视觉事件设计示范（后续制作指导）

按[设计记录](../../../.agents/skills/material2video/references/stage-plan.md#设计记录)补充后续制作思路。本节未试制、未重渲染，不改写已有成片验收结论；不代表当前视频已经实现下列事件。后续明确启动重制时，逐场表「可见事件」栏链接本节，并先验证完整窗口粗样。

#### 电报：从电键到远端文字

| 部分 | 画面状态 | 观众认识 |
|---|---|---|
| 初始状态 | 已留证的电报实物或档案主体，发送与接收两端分离 | 识别通信装置与空间距离 |
| 变化 | 解释层将按键编码为脉冲，沿连接到达远端 | 看见信号传递，不只看电键照片 |
| 预期 | 不适用：直接因果；用发送到接收的顺序替代悬念 | 观察两端如何关联，无需被误导 |
| 揭示 | 不设独立反转，接收端出现对应文字 | 理解电信号能够传送文字 |
| 结果 | 保留两端对应关系与对象名称 | 形成“文字跨越距离”的认识；不是技术间直接继承的历史断言 |

镜头的信息职责：先强调真实装置，再公开解释层的远端对应关系；代码示意不得伪装成历史实录。完整窗口覆盖发送、传输与接收，沿用699×393手机基准；若遮去贡献结论后仅剩档案与装饰脉冲，仍看不到两端对应，则需重做事件。许可、档案出处与示意边界继续遵守原契约。

### 视觉力量设计适用性（后续制作指导）

本节按[设计记录](../../../.agents/skills/material2video/references/stage-plan.md#设计记录)记录后续制作指导，未新增试制、未重渲染，不改写当前成片、旧评审或交付结论。下列方向是待比较候选，不预定采用；明确启动重制后才按同一事件三机制、代表画面与完整粗样验证。

- 档案与实物承担真实性，力量来自主体尺度、材料之间的构图关系和细节显现；不得为了冲击把示意代码当真实历史证据。
- 若明确某个核心事件由图形主导，围绕同一事件比较不同视觉机制；普通档案观察、静态文字对照与克制段落不强制反转或3D。
- 依作品手机基准观察主体、层级与图文职责。灰度诊断只分析明暗，不能因历史材料或必要颜色编码在灰度下丢失语义就判失败；保留事实与必要阅读时间，无声不变。

## 逐场设计表

以下是唯一逐场执行与验收索引。共享规则全片声明，具体窗口与行为以本行及其可编辑来源为准；修订后须实际复查，表格不代表当前已通过。

| 时间 | 内容 | 名称与贡献 | 画面推进 | 实现与检查 |
|---|---|---|---|---|
| 0–2秒 | 开场 | 美国科学高光；美国主导或参与的十项科技节点 | 首帧直接给登月档案，标题不渐入；开场钩子与全片内容一致 | [film.tsx](scenes/film.tsx) / chapter.id=opening；opening-cp，核对中文贡献、档案对应与事实边界 |
| 2–4秒 | 摩尔斯电报 | 电信号让文字跨越城市 | 电键动作接一条传播脉冲 | [film.tsx](scenes/film.tsx) / chapter.id=telegraph；telegraph-cp，核对中文贡献、档案对应与事实边界 |
| 4–6秒 | 贝尔电话 | 语音开始沿电线远行 | 实物接波形，不另做标题卡 | [film.tsx](scenes/film.tsx) / chapter.id=telephone；telephone-cp，核对中文贡献、档案对应与事实边界 |
| 6–9秒 | 动力飞行 | 可控动力飞行开启航空时代 | 档案全幅显出飞机与人物尺度 | [film.tsx](scenes/film.tsx) / chapter.id=flight；flight-cp，核对中文贡献、档案对应与事实边界 |
| 9–11秒 | 三位一体核试验 | 核时代开启，也留下深重代价 | 克制呈现历史影像，不做庆典爆炸效果 | [film.tsx](scenes/film.tsx) / chapter.id=trinity；trinity-cp，核对中文贡献、档案对应与事实边界 |
| 11–13.5秒 | 埃尼阿克计算机（ENIAC） | 早期通用电子计算的重要实践 | 机柜和人物形成尺度，缩写为辅助层 | [film.tsx](scenes/film.tsx) / chapter.id=eniac；eniac-cp，核对中文贡献、档案对应与事实边界 |
| 13.5–16秒 | 晶体管 | 固态器件推动设备小型化 | 实物细节接结构示意 | [film.tsx](scenes/film.tsx) / chapter.id=transistor；transistor-cp，核对中文贡献、档案对应与事实边界 |
| 16–19秒 | 阿波罗11号登月 | 人类首次登月 | NASA档案连续动作成为视觉峰值 | [film.tsx](scenes/film.tsx) / chapter.id=moon；moon-cp，核对中文贡献、档案对应与事实边界 |
| 19–21.5秒 | 阿帕网（ARPANET） | 互联网的重要早期先驱 | 节点逐一连接，缩写为辅助层 | [film.tsx](scenes/film.tsx) / chapter.id=arpanet；arpanet-cp，核对中文贡献、档案对应与事实边界 |
| 21.5–23.5秒 | 人类基因组计划 | 国际合作，美国机构参与主导 | 历史工作场景接序列示意 | [film.tsx](scenes/film.tsx) / chapter.id=genome；genome-cp，核对中文贡献、档案对应与事实边界 |
| 23.5–28秒 | 大语言模型 | 全球积累推动语言生成走向大众 | 左侧贡献边界文案，右侧中文 ChatGPT 示意对话；回答逐字显现，图标原样小尺寸显示并标出 ChatGPT / OpenAI | [film.tsx](scenes/film.tsx) / chapter.id=llm；llm-cp，核对中文贡献、档案对应与事实边界 |
| 28–30秒 | 片尾署名 | 一份简短署名与作品许可 | 两行大字、无重复标题；完整来源留在作品材料 | [film.tsx](scenes/film.tsx) / chapter.id=closing；closing-cp，核对中文贡献、档案对应与事实边界 |

## 必要附件：制作合同

保留原周期合同和已记录的风险范围，不把文档整理当作重新制作或验收。

### 检查点合同（v2）

本块是当前 v2 设计合同，用于后续修订、场景检查与状态查询。历史评审不授权新版本；普通镜头以默认检查点覆盖，不补造逐镜头细表。

```m2v-checkpoints
{
  "version": 2,
  "cycleId": "american-science-milestones-2026-10-27",
  "fps": 60,
  "width": 1920,
  "height": 1080,
  "reviewPlan": {
    "basis": "历史示例的当前 v2 记录：无声档案蒙太奇已交付，历史评审与已知限制保留在作品记录中，不通过本合同补造或授权新版本。",
    "risks": []
  },
  "retrospective": true,
  "scenes": [
    {
      "id": "opening",
      "durationFrames": 120,
      "shots": [
        {
          "id": "opening-shot",
          "tier": "B",
          "window": [
            0,
            120
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "opening-cp",
          "shotId": "opening-shot",
          "frame": 60,
          "window": [
            45,
            75
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": []
        }
      ]
    },
    {
      "id": "telegraph",
      "durationFrames": 120,
      "shots": [
        {
          "id": "telegraph-shot",
          "tier": "B",
          "window": [
            0,
            120
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "telegraph-cp",
          "shotId": "telegraph-shot",
          "frame": 60,
          "window": [
            45,
            75
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": []
        }
      ]
    },
    {
      "id": "telephone",
      "durationFrames": 120,
      "shots": [
        {
          "id": "telephone-shot",
          "tier": "B",
          "window": [
            0,
            120
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "telephone-cp",
          "shotId": "telephone-shot",
          "frame": 60,
          "window": [
            45,
            75
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": []
        }
      ]
    },
    {
      "id": "flight",
      "durationFrames": 180,
      "shots": [
        {
          "id": "flight-shot",
          "tier": "B",
          "window": [
            0,
            180
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "flight-cp",
          "shotId": "flight-shot",
          "frame": 90,
          "window": [
            75,
            105
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": []
        }
      ]
    },
    {
      "id": "trinity",
      "durationFrames": 120,
      "shots": [
        {
          "id": "trinity-shot",
          "tier": "B",
          "window": [
            0,
            120
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "trinity-cp",
          "shotId": "trinity-shot",
          "frame": 60,
          "window": [
            45,
            75
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": []
        }
      ]
    },
    {
      "id": "eniac",
      "durationFrames": 150,
      "shots": [
        {
          "id": "eniac-shot",
          "tier": "B",
          "window": [
            0,
            150
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "eniac-cp",
          "shotId": "eniac-shot",
          "frame": 75,
          "window": [
            60,
            90
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": []
        }
      ]
    },
    {
      "id": "transistor",
      "durationFrames": 150,
      "shots": [
        {
          "id": "transistor-shot",
          "tier": "B",
          "window": [
            0,
            150
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "transistor-cp",
          "shotId": "transistor-shot",
          "frame": 75,
          "window": [
            60,
            90
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": []
        }
      ]
    },
    {
      "id": "moon",
      "durationFrames": 180,
      "shots": [
        {
          "id": "moon-shot",
          "tier": "B",
          "window": [
            0,
            180
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "moon-cp",
          "shotId": "moon-shot",
          "frame": 90,
          "window": [
            75,
            105
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": []
        }
      ]
    },
    {
      "id": "arpanet",
      "durationFrames": 150,
      "shots": [
        {
          "id": "arpanet-shot",
          "tier": "B",
          "window": [
            0,
            150
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "arpanet-cp",
          "shotId": "arpanet-shot",
          "frame": 75,
          "window": [
            60,
            90
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": []
        }
      ]
    },
    {
      "id": "genome",
      "durationFrames": 120,
      "shots": [
        {
          "id": "genome-shot",
          "tier": "B",
          "window": [
            0,
            120
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "genome-cp",
          "shotId": "genome-shot",
          "frame": 60,
          "window": [
            45,
            75
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": []
        }
      ]
    },
    {
      "id": "llm",
      "durationFrames": 270,
      "shots": [
        {
          "id": "llm-shot",
          "tier": "B",
          "window": [
            0,
            270
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "llm-cp",
          "shotId": "llm-shot",
          "frame": 135,
          "window": [
            120,
            150
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": []
        }
      ]
    },
    {
      "id": "closing",
      "durationFrames": 120,
      "shots": [
        {
          "id": "closing-shot",
          "tier": "B",
          "window": [
            0,
            120
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "closing-cp",
          "shotId": "closing-shot",
          "frame": 60,
          "window": [
            45,
            75
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": []
        }
      ]
    }
  ]
}
```
