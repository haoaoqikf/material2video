# 《样本》制作设计

## Context

参考片《重复》的观看驱动力不来自黑底金色本身，而来自一套可迁移的论证语法：一个巨型数字、一个可数总体、一条连续论证、全片只在论点转折处硬切一次、最后用公式收口。本示例把这套语法转成 58 秒的“样本 vs 总体”讲解，并作为 `dark-proof` 风格包的规范示例。

用户已确认：新增独立风格包与规范示例；示例选题《样本》；1920×1080 横屏、无旁白。参考片只用于拆解、并排基准与风格指标，画面、音轨、字幕与文案不进入成片。

相关方法：[视觉创意方向](../../../../.agents/skills/material2video/references/visual-creative-direction.md)、[参考风格契约](../../../../.agents/skills/material2video/references/reference-style.md)、[独立子代理评审](../../../../.agents/skills/material2video/references/subagent-review.md)、[运动设计](../../../../.agents/skills/motion-design/SKILL.md)。

## Goals / Non-Goals

**Goals:** 用同一条“样本 vs 总体”母题完成钩子、证据、转折、文化锚点、数学收口与回扣；让 3/1000、33 点摆动、约 18 倍、四倍关系与均值回归都能在画面或文案中核对；全片只保留一次硬切；手机横屏能读清关键中文与数字。

**Non-Goals:** 不新增视频类型、CLI 命令或 v8 字段；不重制参考片；不把示例数字说成真实人群、产品或考试的统计结论；不提供医疗、投资或法律建议；不在本示例内实现竖屏版、旁白版或长片版。

## 视觉母题

全片只问一件事：**你看到的是样本，还是总体？**

- 3 个金点 = 3 条评价；
- 1000 个点 = 总体；
- 点阵上的线 = 人从样本画出的趋势；
- 盲人摸象的三个取样窗 = 局部为真、整体不全；
- 结尾回到 1000 点中的 3 个金点 = 同一画面、不同理解。

## 八拍时间表（30 fps，1740 帧，58 秒）

| 时间 | 帧 | 画面 | 文案/结论 | 作用 |
|---|---:|---|---|---|
| 0.0–6.0 | 0–180 | 巨型“3”落定，拉出 1000 点阵，3 个金点 | 3 条评价，能定义一个人吗？ | 钩子；先给数字，再给比例 |
| 6.0–13.0 | 180–390 | 3 个评价圆片逐个翻红/翻白，均值 100→67→33→67 | 样本越小，结论越跳。 | 让一条评价产生 33 点摆动 |
| 13.0–20.0 | 390–600 | n=3/10/100/1000 四列点云与金色误差条 | 样本越大，均值越稳。 | 用同一分布展示样本量 |
| 20.0–28.0 | 600–840 | **全片唯一硬切**：3 点连成手绘线；1000 点浮现，线溶解 | 三个点，也能连成一条线。／但线，是人画上去的。 | 论点转折；线失去权威 |
| 28.0–35.0 | 840–1050 | 极端观测第二次靠近均值；上下两组箭头 | 第一次的极端，第二次多半靠近平均。／不是退步，是回归。 | 引入均值回归 |
| 35.0–43.0 | 1050–1290 | 手绘大象轮廓 + 三个取样窗；窗内是同一轮廓的真实局部放大，随后拉回全象 | 盲人摸象：局部是真的，整体不是。 | 文化锚点；小样本不是假，是不全 |
| 43.0–51.0 | 1290–1530 | SE = σ/√n 曲线；n=3→1000 标记“≈18×”；n×4 箭头 | 从 3 到 1000，标准误约小 18 倍。／误差减半，样本要翻四倍。 | 数学收口；给可执行规则 |
| 51.0–58.0 | 1530–1740 | 回到 1000 点阵与 3 个金点；片名《样本》 | 样本越小，故事越大。／先把样本做大，再下结论。 | 回扣开场；不设 CTA |

转场：除 20.0 秒硬切外，其余六处由持续锚点交接：1000 点阵（`FieldAnchor`）与 3 个金点（`GoldAnchor`）跨拍保留，金点从圆片顶移到样本点、趋势点、取样窗与标准误标记；局部内容旧层 14 帧快速退出、新层晚 2 帧进入，整段 16 帧，旧层 8 帧内降到 0.15 以下。600 帧硬切不插入溶解，只播一个低亮度冲击环。

## 微拍与四个整屏冲击

八段论证骨架不变；每段内部按 1–2 秒加入可见微事件，目标明显变化 ≥3 次/10 秒、主内容停留 ≤1.5 秒。

| 拍 | 微拍帧（节选） | 可见事件 |
|---|---|---|
| S1 0–180 | 8、30、62、90、126、150、168 | “3”落定、点阵点燃、金点脉冲、比例计数、金点启程 |
| S2 180–390 | 205、235、265、285、315、335、365 | 三次翻转与小爆散、计数器残影、关键词脉冲、金点移动 |
| S3 390–600 | 410、440、470、500、565、590 | 四列落点 tick、误差条收缩、n=1000 呼吸、切前 build |
| S4 600–840 | 626、660、700、738、760、800 | 线加速生长、点阵浮现、**738–818 整屏 shatter**、余波 |
| S5 840–1050 | 860、890、926、960、990、1020 | 两次观测落点、箭头、回归线、括号、金点移动 |
| S6 1050–1290 | 1070、1110、1130、1150、1194、1230、1260 | 大象快速生长、三窗依次打开、**1194–1260 整屏 reveal** |
| S7 1290–1530 | 1298、1340、1370、1400、1440、1480、1510 | 曲线生长、标记、18× 计数、**1440–1494 整屏 formula**、回场 |
| S8 1530–1740 | 1550、1580、1610、1650、1690、1720 | 片名落定、**1580–1730 整屏 finale**、粒子收拢、最终脉冲 |

四个整屏冲击分别绑定线、全象、公式与片名；硬切 600 帧仍只播单环，不放粒子。整屏冲击期间点阵压暗到 20%–35%，让粒子成为唯一焦点；字幕安全区下方做 alpha 淡出，粒子不遮挡字幕。

## 唯一硬切

- 时间：20.0 秒，帧 600。
- 切前：n=3/10/100/1000 四列点云，证据在增加。
- 切后：近乎空场，只有 3 个金点；随后手绘线长出，1000 点浮现，线溶解。
- 论证作用：让观众感到“证据其实没有增加，只是人画了一条线”，判断被重置。
- 核对方式：`uv run m2v lookdev --project styles/dark-proof/examples/sample --motion 19.5 20.5`。

## 数学口径

| 关系 | 本示例的取值 | 画面落点 |
|---|---|---|
| 3 / 1000 | 0.3% | 开场点阵与结尾回扣 |
| 3 条评价的均值 | 100 → 66.7 → 33.3 → 66.7 | 6–13 秒计数与三个评价圆片 |
| 单条评价的摆动 | 约 33 个百分点 | “一条评价 = 33 点摆动” |
| 样本量 n=3/10/100/1000 | 标准误 14.43 / 7.91 / 2.50 / 0.79（σ=25） | 13–20 秒四列误差条 |
| 3 → 1000 的误差比 | √(1000/3) ≈ 18.26，显示“≈18×” | 43–51 秒曲线与竖括号 |
| 误差减半 | 样本量 ×4 | “n × 4 → 误差 ÷ 2” |
| 均值回归 | 极端观测第二次更靠近总体均值 | 28–35 秒上下两组箭头 |
| 局部与整体 | 局部样本为真，整体结论不成立 | 35–43 秒盲人摸象 |

方法说明以小字置于画面右下角：“数学演示：假设观测随机、独立、同分布。”示例数字不指向真实人群、产品或考试；均值回归与标准误只在该假设下解释。

## 参考拆解（摘要）

参考片 1920×1080、30 fps、62.03 秒；整体响度 −14.1 LUFS、真峰值 −1.3 dBFS、LRA 3.1 LU；`scene>0.25` 的硬切只有 40.47 秒一处。画面主体约占画高 25%–55%，内容像素仅占全帧 2%–12%，底色接近 `#0C0C0E`；米白、金、朱红承担固定语义。

采用规则：01 一个视觉主角、03 可数对象承载比例、05 数字变化有可见来源、07 至多一次硬切、08 先旧判断再公开、11 结尾回到开场对象、12 声音前轻中抬尾收、13 三级文字、14 主体占比与空场率。核心是 03、07、08、11。

不借：参考片的标题、伯努利实验题材、1% 成功率、水滴/石头、天数计数器、具体色值、100% 粒子形状与文案。

### 八项指标

| 指标 | 参考值 | 《样本》目标值 | 实际 | 差值 | 例外说明 |
|---|---|---|---|---|---|
| 主体尺度 | 主体占画高 25%–55%；点阵约 50%，图表约 35% | 巨型数字 20%–30%；点阵 35%–50%；图表 30%–45%；中文标题 6%–7% | 待渲染回填 | 待渲染回填 | 点阵在手机上作纹理，关键 3 点放大 |
| 空场率 | 非背景内容 2%–12% | 普通帧 ≤10%；四个整屏冲击帧允许到 25%，其余帧 3%–6% | 待渲染回填 | 待渲染回填 | 冲击帧是事件光，不是常驻背景 |
| 线宽 | 手绘 8–12 px；图表轴线 5 px；曲线 4–5 px | 手绘 8–12 px；图表 4–5 px；点径 4–6 px | 待渲染回填 | 待渲染回填 | 1000 点阵点径 3.2–4 px |
| 光源 | 无方向性主光；暖色高亮 0.3%–1.6%，数据页约 6.6% | 无方向性主光；普通帧 0.3%–4%，四个冲击帧 5%–12%，数据页 ≤7% | 待渲染回填 | 待渲染回填 | 整屏冲击只在事件帧；金色仍只落在样本、揭示与结论 |
| 背景质感 | 近纯色 `#0C0C0E`；平坦区局部标准差 <0.2 | 近纯色 `#0A0B0D`；平坦区局部标准差 <1 | 待渲染回填 | 待渲染回填 | 允许静态径向暗角 |
| 机位与运动 | 固定机位；元素级运动；无持续推拉 | 元素级运动 + 全片缓慢单向推近 ≤8%；唯一硬切在 20.0 秒 | 待渲染回填 | 待渲染回填 | 不往返、不摇移；字幕不缩放 |
| 剪辑节奏 | 11 拍 / 62 秒；唯一硬切 40.47 秒 | 8 拍 / 58 秒；唯一硬切 20.0 秒；段内 12–16 个微拍；4 个整屏冲击 | 待渲染回填 | 待渲染回填 | 拍长与微拍密度按论证需要 |
| 文字 | 三级；中文 63–72 px，英文 22–30 px，巨型数字 218–320 px | 三级；中文 60–72 px，英文 22–28 px，巨型数字 220–420 px；字幕在安全区内 | 待渲染回填 | 待渲染回填 | 巨型数字在冲击帧可到 420 px |

实际列与差值在渲染后回填到 `outputs/style-reference.md`，本文件只记录设计目标。

## 运动计划

| 段落 | 运动 | 缓动 |
|---|---|---|
| 0–6 秒 | “3”淡入并缩放落定；点阵揭示，3 个金点先亮 | `easeOutCubic` / `easeInOutSine` |
| 6–13 秒 | 评价圆片翻色，均值计数；每次翻转 18 帧 | `easeInOutSine` |
| 13–20 秒 | 四列点云依次揭示；误差条从长到短 | `easeInOutSine` |
| 20 秒 | 整帧硬切；3 点立即出现 | 无缓动 |
| 20–28 秒 | 手绘线生长约 40 帧；1000 点浮现；738–818 帧整屏粒子 shatter | `easeInOutSine` / `easeOutCubic` |
| 28–35 秒 | 第一次观测、第二次观测与箭头依次出现 | `easeOutCubic` / `easeInOutSine` |
| 35–43 秒 | 大象轮廓约 112 帧分批生长（耳/身体、腿、卷鼻、象牙与眼），取样窗出现后让位给全象 | `easeInOutSine` |
| 43–51 秒 | 曲线生长约 60 帧；标记与 18× 括号随后出现；1440–1494 帧整屏 formula | `easeInOutSine` / `easeOutCubic` |
| 51–58 秒 | 点阵与片名落定；1580–1730 帧整屏 finale；1690/1720 微脉冲收束 | `easeOutCubic` / `easeInOutSine` |

## 光效与字幕

- 局部光轨服务轨迹：开场“3”的横移、手绘趋势线、回归箭头、标准误曲线与金点交接；头部光晕 + 锥形尾迹 + 少量尾尘，不做环境闪烁。
- 四个整屏冲击：线溶解（shatter，738–818）、全象揭示（reveal，1194–1260）、公式收口（formula，1440–1494）、结尾回扣（finale，1580–1730）。每个冲击包含 shell / ember / bokeh / dust 四层粒子、两到三圈扩散环与短闪光；粒子从被解释的对象中心发出。
- 硬切 600 帧只给单环，不放粒子；整屏冲击期间点阵压暗，底部字幕安全区做 alpha 淡出。
- 环境微尘 180 个、低速漂移；金点与字幕关键词按 112 BPM 做 ≤3% 脉冲；视觉层全片缓慢单向推近 8%，字幕与方法说明不缩放。
- 屏幕字幕中文逐字错峰展开（未轮到的字全透明）、英文延迟进入；13 条窗口分别使用 `rise/settle/wipe` 进场与 `drift/dissolve/mask` 出场，关键词金色高亮。
- 逐字 span 不改变文本、换行、字号与 `subtitleSafeArea`；外层容器保留 `data-m2v-role="screen-subtitle"` 供量测。

## 声音

- 58 秒原创程序化配乐，112 BPM（约 108 拍）：0–6 秒轻入与 riser；6–20 秒低频脉冲 + 反拍；20.0 秒硬切留白 0.4 秒；20–28 秒半速；28–51 秒脉冲回归、和声垫与 8 分 hat build；51–58 秒全脉冲、finale 与收束。
- 配乐元素为 55/82.5 Hz 低频 kick、短噪声 tick、滤波 hat、minor pad、三音动机、riser 与 impact；全部由 `synthesize.py` 确定性生成，无第三方采样。
- 事件音：三次均值摆动、硬切、线起笔、线溶解/整屏 shatter、均值回归、盲人摸象、公式、公式冲击与结尾；全部引用分镜 `eventId`。
- 母版目标：约 −14 LUFS / ≤ −1 dBTP。示例无旁白。

## 已知限制

- “盲人摸象”轮廓以 Lucide Lab `elephant` 图标（ISC）为几何基底，象牙为作品补充；它只承担“局部与整体”的论证，不追求动物解剖准确。三个取样窗共用同一轮廓，是真实局部放大，不是另画的纹理。
- 1000 点阵在手机上作为纹理可辨，3 个金点靠放大与 `3 / 1000` 文字共同定位。
- 均值回归与标准误是假设性数学演示，不是对真实人群或产品的统计结论。
- 整屏冲击使用 Canvas 2D 粒子层，1920×1080、2 倍采集时约 1300–3000 粒子；性能不足时按 tokens 降粒子数或改用 three.js Points 回退。
- 全片缓慢推近 8%，标题与图表按推近后的位置核对不裁切；字幕与方法说明不缩放。
- 示例未实现竖屏版、旁白版或长片版。

## 机器合同

```m2v-checkpoints
{
  "version": 2,
  "cycleId": "dark-proof-sample-2026-11-03",
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "reviewPlan": {
    "basis": "本示例采用参考片的论证语法（近黑舞台、单主角、三级文字、至多一次硬切、声音前轻中抬尾收），关键采用项尚未单独冷审；20.0 秒硬切与六处溶解依赖完整窗口观察。",
    "risks": [
      {
        "id": "static-family",
        "kind": "static-expression",
        "scope": {
          "checkpointIds": [
            "cp-opening",
            "cp-formula",
            "cp-final"
          ]
        },
        "reason": "参考风格的关键采用项需要并排盲看，不能只凭注册与QA通过",
        "requiredEvidence": [
          "outputs/style-reference/compare-opening.jpg",
          "outputs/style-reference/compare-middle.jpg",
          "outputs/style-reference/compare-closing.jpg"
        ]
      },
      {
        "id": "motion-cut",
        "kind": "structure-timing",
        "scope": {
          "checkpointIds": [
            "cp-cut"
          ]
        },
        "reason": "唯一硬切与相邻溶解的时机需要帧序列观察",
        "requiredEvidence": [
          "outputs/style-reference/motion-19.5-21.5.mp4",
          "19.5–21.5 秒连续帧"
        ]
      },
      {
        "id": "core-cut",
        "kind": "core-event",
        "scope": {
          "checkpointIds": [
            "cp-cut"
          ]
        },
        "reason": "20.0 秒硬切承担论点转折，静帧不能替代完整窗口",
        "requiredEvidence": [
          "19.5–21.5 秒连续帧与独立观察"
        ]
      }
    ]
  },
  "scenes": [
    {
      "id": "sample",
      "durationFrames": 1740,
      "shots": [
        {
          "id": "S1",
          "tier": "B",
          "window": [
            0,
            180
          ]
        },
        {
          "id": "S2",
          "tier": "B",
          "window": [
            180,
            390
          ]
        },
        {
          "id": "S3",
          "tier": "B",
          "window": [
            390,
            600
          ]
        },
        {
          "id": "S4",
          "tier": "A",
          "window": [
            600,
            840
          ],
          "core": true,
          "timeStructure": {
            "establish": {
              "window": [
                600,
                626
              ],
              "audience": "按八拍时间表理解本段论证",
              "visible": "本段主体、数字与屏幕字幕",
              "attention": "状态变化与论证转折",
              "toleranceFrames": 2,
              "failure": "变化无法观察或文字提前泄露"
            },
            "change": {
              "window": [
                626,
                700
              ],
              "audience": "按八拍时间表理解本段论证",
              "visible": "本段主体、数字与屏幕字幕",
              "attention": "状态变化与论证转折",
              "toleranceFrames": 2,
              "failure": "变化无法观察或文字提前泄露"
            },
            "reveal": {
              "window": [
                700,
                760
              ],
              "audience": "按八拍时间表理解本段论证",
              "visible": "本段主体、数字与屏幕字幕",
              "attention": "状态变化与论证转折",
              "toleranceFrames": 2,
              "failure": "变化无法观察或文字提前泄露"
            },
            "result": {
              "window": [
                760,
                802
              ],
              "audience": "按八拍时间表理解本段论证",
              "visible": "本段主体、数字与屏幕字幕",
              "attention": "状态变化与论证转折",
              "toleranceFrames": 2,
              "failure": "变化无法观察或文字提前泄露"
            },
            "hold": {
              "window": [
                802,
                840
              ],
              "audience": "按八拍时间表理解本段论证",
              "visible": "本段主体、数字与屏幕字幕",
              "attention": "状态变化与论证转折",
              "toleranceFrames": 2,
              "failure": "变化无法观察或文字提前泄露"
            },
            "pause": {
              "window": null,
              "notApplicableReason": "连续论证不额外插入停顿",
              "alternative": "段落结果段承担消化时间",
              "audience": "按八拍时间表理解本段论证",
              "visible": "本段主体、数字与屏幕字幕",
              "attention": "状态变化与论证转折",
              "toleranceFrames": 2,
              "failure": "变化无法观察或文字提前泄露"
            }
          }
        },
        {
          "id": "S5",
          "tier": "A",
          "window": [
            840,
            1050
          ],
          "timeStructure": {
            "establish": {
              "window": [
                840,
                884
              ],
              "audience": "按八拍时间表理解本段论证",
              "visible": "本段主体、数字与屏幕字幕",
              "attention": "状态变化与论证转折",
              "toleranceFrames": 2,
              "failure": "变化无法观察或文字提前泄露"
            },
            "change": {
              "window": [
                884,
                938
              ],
              "audience": "按八拍时间表理解本段论证",
              "visible": "本段主体、数字与屏幕字幕",
              "attention": "状态变化与论证转折",
              "toleranceFrames": 2,
              "failure": "变化无法观察或文字提前泄露"
            },
            "reveal": {
              "window": [
                938,
                990
              ],
              "audience": "按八拍时间表理解本段论证",
              "visible": "本段主体、数字与屏幕字幕",
              "attention": "状态变化与论证转折",
              "toleranceFrames": 2,
              "failure": "变化无法观察或文字提前泄露"
            },
            "result": {
              "window": [
                990,
                1028
              ],
              "audience": "按八拍时间表理解本段论证",
              "visible": "本段主体、数字与屏幕字幕",
              "attention": "状态变化与论证转折",
              "toleranceFrames": 2,
              "failure": "变化无法观察或文字提前泄露"
            },
            "hold": {
              "window": [
                1028,
                1050
              ],
              "audience": "按八拍时间表理解本段论证",
              "visible": "本段主体、数字与屏幕字幕",
              "attention": "状态变化与论证转折",
              "toleranceFrames": 2,
              "failure": "变化无法观察或文字提前泄露"
            },
            "pause": {
              "window": null,
              "notApplicableReason": "连续论证不额外插入停顿",
              "alternative": "段落结果段承担消化时间",
              "audience": "按八拍时间表理解本段论证",
              "visible": "本段主体、数字与屏幕字幕",
              "attention": "状态变化与论证转折",
              "toleranceFrames": 2,
              "failure": "变化无法观察或文字提前泄露"
            }
          }
        },
        {
          "id": "S6",
          "tier": "B",
          "window": [
            1050,
            1290
          ]
        },
        {
          "id": "S7",
          "tier": "B",
          "window": [
            1290,
            1530
          ]
        },
        {
          "id": "S8",
          "tier": "B",
          "window": [
            1530,
            1740
          ]
        }
      ],
      "checkpoints": [
        {
          "id": "cp-opening",
          "shotId": "S1",
          "frame": 150,
          "window": [
            120,
            176
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "3 条评价，能定义一个人吗？\nThree reviews cannot define a person.",
              "window": [
                120,
                176
              ]
            }
          ],
          "claims": [
            {
              "id": "sample-ratio",
              "value": 0.3,
              "unit": "%",
              "basis": "3 / 1000"
            }
          ],
          "forbidden": [
            "refs/",
            "推荐",
            "购买"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "maxTextCharacters": 60
          },
          "manualEvidence": [
            "代表帧与并排图"
          ]
        },
        {
          "id": "cp-swing",
          "shotId": "S2",
          "frame": 300,
          "window": [
            260,
            360
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "样本越小，结论越跳。\nSmall samples swing hard.",
              "window": [
                260,
                360
              ]
            }
          ],
          "claims": [
            {
              "id": "swing-points",
              "value": 33,
              "unit": "points",
              "basis": "one review flip in three reviews"
            }
          ],
          "forbidden": [
            "refs/",
            "推荐",
            "购买"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "maxTextCharacters": 60
          },
          "manualEvidence": [
            "代表帧与并排图"
          ]
        },
        {
          "id": "cp-columns",
          "shotId": "S3",
          "frame": 540,
          "window": [
            480,
            594
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "样本越大，均值越稳。\nBigger samples stay steadier.",
              "window": [
                480,
                594
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "refs/",
            "推荐",
            "购买"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "maxTextCharacters": 60
          },
          "manualEvidence": [
            "代表帧与并排图"
          ]
        },
        {
          "id": "cp-cut",
          "shotId": "S4",
          "frame": 660,
          "window": [
            606,
            714
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "三个点，也能连成一条线。\nThree dots make one trend line.",
              "window": [
                606,
                714
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "refs/",
            "推荐",
            "购买"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "maxTextCharacters": 60
          },
          "manualEvidence": [
            "代表帧与并排图"
          ]
        },
        {
          "id": "cp-line-gone",
          "shotId": "S4",
          "frame": 800,
          "window": [
            726,
            834
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "但线，是人画上去的。\nBut the line is drawn by hand.",
              "window": [
                726,
                834
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "refs/",
            "推荐",
            "购买"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "maxTextCharacters": 60
          },
          "manualEvidence": [
            "代表帧与并排图"
          ]
        },
        {
          "id": "cp-regression",
          "shotId": "S5",
          "frame": 960,
          "window": [
            936,
            1044
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "不是退步，是回归。\nNot decline — regression.",
              "window": [
                936,
                1044
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "refs/",
            "推荐",
            "购买"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "maxTextCharacters": 60
          },
          "manualEvidence": [
            "代表帧与并排图"
          ]
        },
        {
          "id": "cp-anchor",
          "shotId": "S6",
          "frame": 1200,
          "window": [
            1194,
            1284
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "全象不等于三块局部。\nThe whole is not three parts.",
              "window": [
                1194,
                1284
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "refs/",
            "推荐",
            "购买"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "maxTextCharacters": 60
          },
          "manualEvidence": [
            "代表帧与并排图"
          ]
        },
        {
          "id": "cp-formula",
          "shotId": "S7",
          "frame": 1455,
          "window": [
            1416,
            1524
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "误差减半，样本要翻四倍。\nHalf the error needs four times the sample.",
              "window": [
                1416,
                1524
              ]
            }
          ],
          "claims": [
            {
              "id": "error-ratio",
              "value": 18,
              "unit": "x",
              "basis": "sqrt(1000/3)=18.26"
            },
            {
              "id": "four-times",
              "value": 4,
              "unit": "x",
              "basis": "sqrt(4n)"
            }
          ],
          "forbidden": [
            "refs/",
            "推荐",
            "购买"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "maxTextCharacters": 60
          },
          "manualEvidence": [
            "代表帧与并排图"
          ]
        },
        {
          "id": "cp-return",
          "shotId": "S8",
          "frame": 1620,
          "window": [
            1600,
            1650
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "样本越小，故事越大。\nSmall sample tells a big story.",
              "window": [
                1600,
                1650
              ]
            }
          ],
          "claims": [
            {
              "id": "closing-ratio",
              "value": 0.3,
              "unit": "%",
              "basis": "3 / 1000"
            }
          ],
          "forbidden": [
            "refs/",
            "推荐",
            "购买"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "maxTextCharacters": 60
          },
          "manualEvidence": [
            "代表帧与并排图"
          ]
        },
        {
          "id": "cp-final",
          "shotId": "S8",
          "frame": 1700,
          "window": [
            1656,
            1734
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "先把样本做大，再下结论。\nGrow the sample then conclude.",
              "window": [
                1656,
                1734
              ]
            }
          ],
          "claims": [
            {
              "id": "closing-ratio",
              "value": 0.3,
              "unit": "%",
              "basis": "3 / 1000"
            }
          ],
          "forbidden": [
            "refs/",
            "推荐",
            "购买"
          ],
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "maxTextCharacters": 60
          },
          "manualEvidence": [
            "代表帧与并排图"
          ]
        }
      ]
    }
  ]
}
```
