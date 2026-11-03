# 《接》v4 制作设计：10 场、10 种说明方式

## Context

v3 的问题是“同一种说明方式换了 13 个对象”：每页都是一个物件 + 一个动作 + 一个数字，观众仍要靠字幕理解；全局金色光点场 + 光晕 + 5% 推近是没有来源的环境动效，也让结尾的金色贬值。参考片的强项是**用不同方式证明同一个量**：数字滚动、点阵普查、单次失败、命名/规则、计数器账本、曲线、柱状、硬切对比、尺度阶梯、日计数时间跳切、公式、粒子收账。

v4 保留 60 秒、无旁白、唯一硬切（帧 1230 / 41.0 秒）、结尾收束与 dark-proof 风格；把 13 个页面组件减到 **10 个**，给每种说明方式足够时间。统一口径：**10 个页面组件 = 10 个 DESIGN shots**；storyboard 仍是 1 个 code scene。

## 参考拆解与借鉴分层

- 参考作品：抖音 `7692873023291963558`，作者「🇹.🇴.🇲」，标题《重复》，62.03 秒。完整拆解见 `openspec/changes/archive/2026-11-02-add-dark-proof-style-and-sample/reference-analysis.md`；证据与差值见 `outputs/style-reference.md`。
- 采用的底层机制：一个问题用多种说明方式反复证明；先让观众形成旧判断，再用同一对象公开新信息；全片至多一次硬切；结尾回到开场对象完成收账；数字必须有可见来源。
- 借鉴分层：L1 视觉语言为主（近黑舞台、巨型数字、可数总体、单一暖金焦点、双语字幕），L2 节奏结构为次（尺度递进、公式晚到、一次硬切、结尾收束），L3 情绪调性为次（克制、连续思考、不靠环境粒子）。三层之外不继承参考片的题材或符号。
- 不借清单：参考片的标题、伯努利实验题材、1% 成功率设定、水滴/石头角色、天数计数器、红叉点阵、具体色值、100% 粒子形状与“一日一钱，千日千钱”等文案；不借 62 秒 / 11 拍节奏。
- 视觉与运动方法：[视觉创意导演方法](../../../../.agents/skills/material2video/references/visual-creative-direction.md)、[参考风格契约](../../../../.agents/skills/material2video/references/reference-style.md)。

## 一句话命题

> **复利不是钱的事，是把上一次的结果，接回下一次的起点。**

## 10 场

| 场 | 帧/时间 | 说明方式 | 对象与动作 | 读数 | Punchline |
|---|---|---|---|---|---|
| S1 | 0–180 / 0–6s | 物理因果 | 层压木块剖面，凿子切入，深度尺，金色木花 | 切深 0→8 mm | 凹槽 + 木花 |
| S2 | 180–420 / 6–14s | 时间跳切/累积 | 单个滴头 + 同一块石板 + 日计数；第一滴金色；裂纹累积 | 100 滴；第 1→100 天（99 个间隔，示意） | 第 100 天的裂纹 + 第一滴金色 |
| S3 | 420–600 / 14–20s | 数字滚动 | 同一木块 100 刀；里程表 1→100；第 37 刀滑刀；第 100 刀金色；磨刀背景 | 刀数 100；缺口 100 | 计数器 100 + 100 个缺口 + 亮刃 |
| S4 | 600–750 / 20–25s | 定义回环 | 大字“复利”；产出→投入实体回环；三条件作为回环上的三个标记 | 1 次再投入 | 字 + 回环 + 三个标记 |
| S5 | 750–900 / 25–30s | 数学空间 | 二叉分叉树；每层枝数翻倍 | 1→64×，6 层 | 64 个叶节点 |
| S6 | 900–1080 / 30–36s | 尺度 + 数据 | 透明纸 42 折；纸堆/月球；随后接曲线数据图 | 42 折；439,804.65 km；2^n | 越过月球 + 前平后陡的曲线 |
| S7 | 1080–1230 / 36–41s | 对照实验 | 同一批纸：线性堆 vs 翻倍堆；同 42 步 | 4.2 mm vs 439,804.65 km | 两堆并排；**唯一硬切 41.0s** |
| S8 | 1230–1410 / 41–47s | 网络数据 | 同一 100 节点环；先 45 条内部线，再加入 945 条 | 45 / 945 / 21× / 4,950 | 同一张网变密 |
| S9 | 1410–1560 / 47–52s | 传说/尺度 | 8×8 棋盘；一粒逐格翻倍；组缩放拉远 | 64 格；2^63 | 第 64 格堆成山 |
| S10 | 1560–1800 / 52–60s | 时间回路 + 总和 | 第一节点 99 线；4,950 条线收拢成“接”；片名 | 99 / 4,950 | 99 根线 → 接 |

唯一硬切：帧 1230（41.0 秒），两堆纸 → 网络/21×；硬切只给单环，不放粒子。全片只保留结尾一次整屏收束。

## 说明方式与共同规则

- **一页一种说明方式**：物理、时间、数字、定义、数学、尺度/数据、对照、网络、传说、总和；相邻页不重复。
- **一页一个主运动**：同一时刻只允许一个主运动；数字滚动/残影只服务数字变化，不叠加环境层。
- **数字必须有来源**：水滴/缺口/折层/线/谷粒；数字是主角（S3）或读数（其余），单位/标签固定，字幕晚于数字落定。
- **一屏一个金色焦点**：金色只服务状态变化，不做环境装饰；删除全局 `MoteField`、光晕与全片推近。
- **转场**：页面在边界前 4 帧淡出、边界后 8 帧淡入；单一金色交接物（木花/水滴/金片/谷粒/环）只在边界前后出现，不是粒子场。唯一硬切 1230。
- **镜头**：S1/S3/S4/S5/S7 锁死；S6 尺度/旋转；S9 拉远；S10 轻推。页面镜头在边界回到中性，交接物在屏幕坐标绘制。
- **文字**：一个数字 + 一个“量的是什么”的标签 + 一句字幕；删掉与字幕重复的页面小字；字幕 ≤30 汉字；方法注脚保留小字。
- **无旁白**；字幕只落 `subtitleSafeArea`；关键数字/中文主讲按手机横屏复核。

## 数学与口径

| 关系 | 数值 |
|---|---:|
| 纸厚 0.1 mm × 2^42 | 439,804.65 km |
| 地月平均距离 | 384,400 km |
| 棋盘第 64 格 | 2^63 粒 |
| 棋盘全盘 | 2^64−1 粒 |
| 100 概念总连接 | C(100,2) = 4,950 |
| 前 10 个内部连接 | 45 |
| 后 10 个接入前 90 个新增 | 945 |
| 945 / 45 | 21× |
| 线性 42 步 × 0.1 mm | 4.2 mm |

水滴/日计数为示意：1 滴/天，第 1 滴到第 100 滴为 99 个间隔；不是物理测量。凿子切深为示意，不声称与次数成精确比例。

## 已知限制

- 42 折是数学模型，不是物理演示；棋盘是传说。
- 水滴/日计数为时间压缩示意；第 1 滴/第 100 天用金色强调。
- 结尾“接”由 4,950 条弦随计数画出；先收字形再落片名，避免双字重影。
- 方法注脚按大屏设计；手机横屏不要求可辨。
- 全片无旁白；字幕只使用 `subtitleSafeArea`。

## 机器合同（v4）

```m2v-checkpoints
{
  "version": 2,
  "cycleId": "compound-connect-v4-2026-11-03",
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "reviewPlan": {
    "basis": "10 场对应 10 种说明方式；41.0 秒硬切与结尾收束是两个核心事件；水滴/数字页是本次新增的说明方式。",
    "risks": [
      {
        "id": "core-cut-finale",
        "kind": "core-event",
        "scope": {"checkpointIds": ["cp-piles", "cp-final"]},
        "reason": "唯一硬切与结尾收束承担论点转折和收束，静帧不能替代完整窗口",
        "requiredEvidence": ["outputs/lookdev/transition-cut.png", "outputs/lookdev/finale-strip.png"]
      },
      {
        "id": "modes-legibility",
        "kind": "static-expression",
        "scope": {"checkpointIds": ["cp-first", "cp-drop", "cp-paper", "cp-board"]},
        "reason": "10 种说明方式必须在无字幕时仍能读出动作、读数与结果，不能只凭字幕解释",
        "requiredEvidence": ["outputs/lookdev/still-000132.png", "outputs/lookdev/still-000372.png", "outputs/lookdev/still-001040.png", "outputs/lookdev/still-001542.png"]
      }
    ]
  },
  "scenes": [
    {
      "id": "compound-connect",
      "durationFrames": 1800,
      "shots": [
        {"id": "S1", "window": [0, 180], "tier": "B"},
        {"id": "S2", "window": [180, 420], "tier": "A"},
        {"id": "S3", "window": [420, 600], "tier": "A"},
        {"id": "S4", "window": [600, 750], "tier": "B"},
        {"id": "S5", "window": [750, 900], "tier": "B"},
        {"id": "S6", "window": [900, 1080], "tier": "A"},
        {"id": "S7", "window": [1080, 1230], "tier": "A"},
        {"id": "S8", "window": [1230, 1410], "tier": "A"},
        {"id": "S9", "window": [1410, 1560], "tier": "A"},
        {"id": "S10", "window": [1560, 1800], "tier": "A"}
      ],
      "checkpoints": [
        {
          "id": "cp-first",
          "shotId": "S1",
          "frame": 132,
          "window": [20, 170],
          "expected": [],
          "textPlan": [{"role": "screen-subtitle", "text": "第一刀，只有 8 毫米。", "window": [10, 170]}],
          "claims": [{"id": "depth", "value": 8, "unit": "mm", "basis": "第一刀切深，示意", "role": "screen-subtitle"}],
          "forbidden": ["refs/", "投资", "收益"],
          "measurement": {"subtitleRoles": ["screen-subtitle"], "maxTextCharacters": 60}
        },
        {
          "id": "cp-drop",
          "shotId": "S2",
          "frame": 372,
          "window": [196, 412],
          "expected": [],
          "textPlan": [{"role": "screen-subtitle", "text": "同一滴水，同一块石头，第 100 天。", "window": [196, 412]}],
          "claims": [
            {"id": "drops", "value": 100, "unit": "drops", "basis": "1 滴/天，示意", "role": "screen-subtitle"},
            {"id": "days", "value": 100, "unit": "days", "basis": "1 滴/天，示意", "role": "screen-subtitle"},
            {"id": "intervals", "value": 99, "unit": "intervals", "basis": "第 1 滴到第 100 滴"}
          ],
          "forbidden": ["refs/", "投资", "收益"],
          "measurement": {"subtitleRoles": ["screen-subtitle"], "maxTextCharacters": 60}
        },
        {
          "id": "cp-cuts",
          "shotId": "S3",
          "frame": 552,
          "window": [436, 592],
          "expected": [],
          "textPlan": [{"role": "screen-subtitle", "text": "100 刀，一把凿子；第 37 刀滑了。", "window": [436, 592]}],
          "claims": [
            {"id": "cuts", "value": 100, "unit": "cuts", "basis": "1→100", "role": "screen-subtitle"},
            {"id": "slip", "value": 37, "unit": "cuts", "basis": "第 37 刀滑刀", "role": "screen-subtitle"}
          ],
          "forbidden": ["refs/", "投资", "收益"],
          "measurement": {"subtitleRoles": ["screen-subtitle"], "maxTextCharacters": 60}
        },
        {
          "id": "cp-paper",
          "shotId": "S6",
          "frame": 1040,
          "window": [916, 1072],
          "expected": [],
          "textPlan": [{"role": "screen-subtitle", "text": "42 折，厚度会超过地月距离。", "window": [916, 1072]}],
          "claims": [
            {"id": "folds", "value": 42, "unit": "folds", "basis": "0.1 mm × 2^42", "role": "screen-subtitle"},
            {"id": "paper-height", "value": 439804.65, "unit": "km", "basis": "0.1 mm × 2^42"},
            {"id": "moon", "value": 384400, "unit": "km", "basis": "地月平均距离"}
          ],
          "forbidden": ["refs/", "投资", "收益"],
          "measurement": {"subtitleRoles": ["screen-subtitle"], "maxTextCharacters": 60}
        },
        {
          "id": "cp-piles",
          "shotId": "S7",
          "frame": 1218,
          "window": [1096, 1222],
          "expected": [],
          "textPlan": [{"role": "screen-subtitle", "text": "42 步：4.2 毫米 对 439,804.65 公里。", "window": [1096, 1222]}],
          "claims": [
            {"id": "steps", "value": 42, "unit": "steps", "basis": "同 42 步", "role": "screen-subtitle"},
            {"id": "linear", "value": 4.2, "unit": "mm", "basis": "42 × 0.1 mm", "role": "screen-subtitle"},
            {"id": "compound", "value": 439804.65, "unit": "km", "basis": "0.1 mm × 2^42", "role": "screen-subtitle"}
          ],
          "forbidden": ["refs/", "投资", "收益"],
          "measurement": {"subtitleRoles": ["screen-subtitle"], "maxTextCharacters": 60}
        },
        {
          "id": "cp-network",
          "shotId": "S8",
          "frame": 1392,
          "window": [1246, 1402],
          "expected": [],
          "textPlan": [
            {"role": "screen-subtitle", "text": "前10内部45，最后10新增945。", "window": [1292, 1348]},
            {"role": "screen-subtitle", "text": "21 倍，共 4,950。", "window": [1350, 1402]}
          ],
          "claims": [
            {"id": "first-ten", "value": 45, "unit": "links", "basis": "C(10,2)"},
            {"id": "last-ten", "value": 945, "unit": "links", "basis": "10×90+45"},
            {"id": "ratio", "value": 21, "unit": "x", "basis": "945/45"},
            {"id": "total", "value": 4950, "unit": "links", "basis": "C(100,2)"}
          ],
          "forbidden": ["refs/", "投资", "收益"],
          "measurement": {"subtitleRoles": ["screen-subtitle"], "maxTextCharacters": 60}
        },
        {
          "id": "cp-board",
          "shotId": "S9",
          "frame": 1542,
          "window": [1426, 1552],
          "expected": [],
          "textPlan": [{"role": "screen-subtitle", "text": "棋盘第 64 格，2 的 63 次方粒。", "window": [1426, 1552]}],
          "claims": [
            {"id": "squares", "value": 64, "unit": "squares", "basis": "8×8", "role": "screen-subtitle"},
            {"id": "exponent", "value": 63, "unit": "exponent", "basis": "2^63", "role": "screen-subtitle"},
            {"id": "whole-board", "value": 18446744073709551615, "unit": "grains", "basis": "2^64−1"}
          ],
          "forbidden": ["refs/", "投资", "收益"],
          "measurement": {"subtitleRoles": ["screen-subtitle"], "maxTextCharacters": 60}
        },
        {
          "id": "cp-final",
          "shotId": "S10",
          "frame": 1776,
          "window": [1576, 1798],
          "expected": [],
          "textPlan": [{"role": "screen-subtitle", "text": "让下一次，接上一次。", "window": [1576, 1798]}],
          "claims": [
            {"id": "links", "value": 4950, "unit": "links", "basis": "C(100,2)"},
            {"id": "first-node", "value": 99, "unit": "links", "basis": "第一节点连接其余 99 个"}
          ],
          "forbidden": ["refs/", "投资", "收益"],
          "measurement": {"subtitleRoles": ["screen-subtitle"], "maxTextCharacters": 60}
        }
      ]
    }
  ]
}
```
