# buffer-smoothing 内容驱动讲解示例

原文为 `article.md`，分镜沿用 v7。目标时长 120～180 秒，以真实配音准备结果为准；1080×1920、30 fps，自动烧录字幕。

## 论点与画面对应

| 文章论点 | 场景 / 旁白 ID | 画面与组件 |
| --- | --- | --- |
| 短期节奏不一致 | `buffer-point` / buffer-point-0 | point：缓冲，让快慢衔接 |
| 直接交接与暂存 | `buffer-compare` / buffer-compare-0、buffer-compare-1 | compare：直接交接，还是中间暂存 |
| 先存再补的机制 | `buffer-water` / buffer-water-0、buffer-water-1 | Motion + SVG：水箱怎样吸收短期波动 |
| 流量差由积压承接 | `buffer-chart` / buffer-chart-0、buffer-chart-1 | ECharts / Chart：流量与积压，要一起看 |
| 等待与持续过载 | `buffer-cause` / buffer-cause-0、buffer-cause-1、buffer-cause-2 | cause：容量有上限，等待有代价 |
| 设计时的三个问题 | `buffer-steps` / buffer-steps-0、buffer-steps-1、buffer-steps-2 | steps：设计缓冲，先问三个问题 |

核心代码幕通过 `segmentWindows` 与 `elapsedSeconds` 绑定真实旁白，不使用固定时长的无声技术末幕；示意数据不代表实验结果。三片合计覆盖七种模板、Motion、ECharts、GSAP、Three.js、React Three Fiber 与 Drei。

水箱用 Motion 入场和录制时钟驱动水位；图表以初始存量 8、每段最大输出 4 计算输出与积压，保持守恒关系。保留原创 CC0 音床 `assets/bed.wav` 与内置 `ding-dong` 音效，许可见 [素材许可](assets/LICENSE.md)。

## 制作

先阅读原文并执行 `m2v general input-review`，填写语义审查；查询当前音色列表并按新旁白选择、保存理由和摘要。随后运行：

```powershell
uv run m2v validate --project examples/buffer-smoothing
uv run m2v prepare --project examples/buffer-smoothing
uv run m2v preview --project examples/buffer-smoothing
uv run m2v render --project examples/buffer-smoothing
```

准备与审查记录位于本示例 `outputs/`；预演和成片位于 `videos/examples/buffer-smoothing/outputs/`，均不入库。材料变化后重新准备与完整预演。

字段见 [分镜结构](../../.agents/skills/material2video/references/storyboard-schema.md) 与 [制作流程](../../.agents/skills/material2video/references/production-workflow.md)。
