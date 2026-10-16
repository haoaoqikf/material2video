# darts-trial-and-error 内容驱动讲解示例

原文为 `article.md`，分镜沿用 v7。目标时长 120～180 秒，以真实配音准备结果为准；1080×1920、30 fps，自动烧录字幕。

## 论点与画面对应

| 文章论点 | 场景 / 旁白 ID | 画面与组件 |
| --- | --- | --- |
| 用行动获得信息 | `darts-point` / darts-point-0 | point：试错，要带着反馈 |
| 推演与试验的作用 | `darts-compare` / darts-compare-0、darts-compare-1 | compare：准备与试验，各解决什么 |
| 记录落点并逐次修正 | `darts-demo` / darts-demo-0、darts-demo-1、darts-demo-2 | GSAP + SVG：看见偏差，再调整方向 |
| 假设、观察与调整记录 | `darts-image` / darts-image-0 | image：把反馈写成记录 |
| 一轮反馈的因果关系 | `darts-cause` / darts-cause-0、darts-cause-1、darts-cause-2 | cause：从一次尝试走到下一次 |
| 成本、变量和停止条件 | `darts-steps` / darts-steps-0、darts-steps-1、darts-steps-2 | steps：试之前，先设好边界 |

核心代码幕通过 `segmentWindows` 与 `elapsedSeconds` 绑定真实旁白，不使用固定时长的无声技术末幕；示意数据不代表实验结果。三片合计覆盖七种模板、Motion、ECharts、GSAP、Three.js、React Three Fiber 与 Drei。

原创素材由 `assets/generate.py` 生成到被忽略的 `outputs/generated/`，再经 `m2v general assets import` 导入；记录见 [媒体来源](assets/media-sources.json)，许可见 [素材许可](assets/LICENSE.md)。

## 制作

先阅读原文并执行 `m2v general input-review`，填写语义审查；查询当前音色列表并按新旁白选择、保存理由和摘要。随后运行：

```powershell
uv run m2v validate --project examples/darts-trial-and-error
uv run m2v prepare --project examples/darts-trial-and-error
uv run m2v preview --project examples/darts-trial-and-error
uv run m2v render --project examples/darts-trial-and-error
```

准备与审查记录位于本示例 `outputs/`；预演和成片位于 `videos/examples/darts-trial-and-error/outputs/`，均不入库。材料变化后重新准备与完整预演。

字段见 [分镜结构](../../.agents/skills/material2video/references/storyboard-schema.md) 与 [制作流程](../../.agents/skills/material2video/references/production-workflow.md)。
