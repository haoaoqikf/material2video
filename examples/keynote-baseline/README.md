# keynote-baseline 内容驱动讲解示例

原文为 `article.md`，分镜沿用 v7。目标时长 120～180 秒，以真实配音准备结果为准；1080×1920、30 fps，自动烧录字幕。

## 论点与画面对应

| 文章论点 | 场景 / 旁白 ID | 画面与组件 |
| --- | --- | --- |
| 反复比较的成本 | `choice-point` / choice-point-0 | point：少一点比较，多一点方向 |
| 排名与按需筛选 | `choice-compare` / choice-compare-0、choice-compare-1 | compare：反复排名，还是按需筛选 |
| 底线、偏好与截止点 | `choice-steps` / choice-steps-0、choice-steps-1、choice-steps-2 | steps：把需要变成筛选标准 |
| 预算与时间逐层筛选 | `choice-world` / choice-world-0、choice-world-1、choice-world-2 | Three.js + React Three Fiber + Drei：分叉的路线，怎样逐步收敛 |
| 复述筛选到行动 | `choice-video` / choice-video-0 | video：从比较走向行动 |
| 重大决定保留充分比较 | `choice-boundary` / choice-boundary-0 | point：并非所有选择都该只剩一个 |
| 行动与调整空间 | `choice-close` / choice-close-0 | point：让标准帮助你向前 |

核心代码幕通过 `segmentWindows` 与 `elapsedSeconds` 绑定真实旁白，不使用固定时长的无声技术末幕；示意数据不代表实验结果。三片合计覆盖七种模板、Motion、ECharts、GSAP、Three.js、React Three Fiber 与 Drei。

原创素材由 `assets/generate.py` 生成到被忽略的 `outputs/generated/`，再经 `m2v general assets import` 导入；记录见 [媒体来源](assets/media-sources.json)，许可见 [素材许可](assets/LICENSE.md)。

## 制作

先阅读原文并执行 `m2v general input-review`，填写语义审查；查询当前音色列表并按新旁白选择、保存理由和摘要。随后运行：

```powershell
uv run m2v validate --project examples/keynote-baseline
uv run m2v prepare --project examples/keynote-baseline
uv run m2v preview --project examples/keynote-baseline
uv run m2v render --project examples/keynote-baseline
```

准备与审查记录位于本示例 `outputs/`；预演和成片位于 `videos/examples/keynote-baseline/outputs/`，均不入库。材料变化后重新准备与完整预演。

字段见 [分镜结构](../../.agents/skills/material2video/references/storyboard-schema.md) 与 [制作流程](../../.agents/skills/material2video/references/production-workflow.md)。
