# buffer-smoothing 内容驱动讲解示例

原文为 `article.md`，分镜为 v8 全画布代码场景。目标时长 120～180 秒，以真实配音准备结果为准；
**1920×1080 横屏**、60 fps，自动烧录字幕。视觉设计依据见 [DESIGN.md](DESIGN.md)。

## 论点与画面对应

| 文章论点 | 场景 / 旁白 ID | 画面与组件 |
| --- | --- | --- |
| 平均相同，瞬间也会不同 | `buffer-point` / buffer-point-0 | 脉冲柱 + 平均虚线（SVG） |
| 直接交接与中间暂存 | `buffer-compare` / buffer-compare-0、buffer-compare-1 | 两条通道与流动点（SVG） |
| 先存再补的机制 | `buffer-water` / buffer-water-0、buffer-water-1 | 水箱剖面与水位（Motion） |
| 流量差由积压承接 | `buffer-flow` / buffer-flow-0、buffer-flow-1 | 输入 / 输出 / 积压（ECharts） |
| 容量上限与持续过载 | `buffer-capacity` / buffer-capacity-0、buffer-capacity-1、buffer-capacity-2 | 溢出水位与更大的水箱轮廓 |
| 设计时的三个问题 | `buffer-questions` / buffer-questions-0、buffer-questions-1、buffer-questions-2 | 三张问题卡片（Motion） |

水箱水位与溢出完全由 `buffer-water-*`、`buffer-capacity-*` 的真实旁白时间窗驱动，不用固定时长的
无声技术末幕。三片合计覆盖 Motion、ECharts、GSAP、Three.js、React Three Fiber 与 Drei。

`buffer-flow` 的示意数据按守恒关系算出（每段最多输出 4、初始存量 8），输入与积压的差额守恒，
图上标注「示意数据」。音床是原创 CC0 素材 `assets/bed.wav`，另有一次内置 `ding-dong` 音效，
许可见 [素材许可](assets/LICENSE.md)。

## 制作

先阅读原文并执行 `m2v general input-review`，填写语义审查；查询当前音色列表并按新旁白选择、
保存理由和摘要。随后运行：

```powershell
uv run m2v validate --project examples/buffer-smoothing
uv run m2v prepare --project examples/buffer-smoothing
uv run m2v preview --project examples/buffer-smoothing
uv run m2v render --project examples/buffer-smoothing
```

准备与审查记录位于本示例 `outputs/`；预演和成片位于 `videos/examples/buffer-smoothing/outputs/`，
均不入库。材料、代码、画幅或登记素材变化后重新准备与完整预演。

字段见 [分镜结构](../../.agents/skills/material2video/references/storyboard-schema.md) 与
[制作流程](../../.agents/skills/material2video/references/production-workflow.md)。
