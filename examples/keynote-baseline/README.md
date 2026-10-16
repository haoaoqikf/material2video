# keynote-baseline 内容驱动讲解示例

原文为 `article.md`，分镜为 v8 全画布代码场景。目标时长 120～180 秒，以真实配音准备结果为准；
**1920×1080 横屏**、30 fps，自动烧录字幕。视觉设计依据见 [DESIGN.md](DESIGN.md)。

## 论点与画面对应

| 文章论点 | 场景 / 旁白 ID | 画面与组件 |
| --- | --- | --- |
| 选项多不等于自由 | `choice-point` / choice-point-0 | 十张方案卡与注意力跳动 |
| 反复排名与按需筛选 | `choice-compare` / choice-compare-0、choice-compare-1 | 两张对照面板 |
| 把需要变成筛选标准 | `choice-criteria` / choice-criteria-0、choice-criteria-1、choice-criteria-2 | 底线 / 权重 / 截止点三列 |
| 分叉路线逐步收敛 | `choice-world` / choice-world-0、choice-world-1、choice-world-2 | 三维路径（Three.js / R3F / Drei） |
| 从比较走向行动 | `choice-action` / choice-action-0 | 已导入片段（`useMediaAsset`） |
| 并非所有选择都该只剩一个 | `choice-boundary` / choice-boundary-0 | 三类情形对照 |
| 让标准帮助你向前 | `choice-close` / choice-close-0 | 三个自问与两个收束项 |

三维路径按 `choice-world-*` 的真实旁白时间窗收敛（全部候选 → 排除两条 → 选出主选、保留备选），
片段播放头跟着 `choice-action-0` 的旁白时钟走，不用固定时长的无声技术末幕。三片合计覆盖
Motion、ECharts、GSAP、Three.js、React Three Fiber 与 Drei。

引用片段是原创 CC0 素材 `keynote-clip`（竖屏 1080×1920，20 秒，见 [素材许可](assets/LICENSE.md)），
在代码里用 `useMediaAsset('keynote-clip')` 按 ID 取用；它是横屏画布里的竖版演示区，裁切方式由
作品代码决定。素材原声不进入母版，成片没有音床，声音全部来自统一音轨的旁白。

## 制作

先阅读原文并执行 `m2v general input-review`，填写语义审查；查询当前音色列表并按新旁白选择、
保存理由和摘要。随后运行：

```powershell
uv run m2v validate --project examples/keynote-baseline
uv run m2v prepare --project examples/keynote-baseline
uv run m2v preview --project examples/keynote-baseline
uv run m2v render --project examples/keynote-baseline
```

准备与审查记录位于本示例 `outputs/`；预演和成片位于 `videos/examples/keynote-baseline/outputs/`，
均不入库。材料、代码、画幅或登记素材变化后重新准备与完整预演。

字段见 [分镜结构](../../.agents/skills/material2video/references/storyboard-schema.md) 与
[制作流程](../../.agents/skills/material2video/references/production-workflow.md)。
