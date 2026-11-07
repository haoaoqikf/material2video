# 随附示例

七部作品按五类放在 `examples/<类型>/<作品名>/`，均使用 project v2 与分镜 v9。作品专属画面与参数在各自 `scenes/`，不作为共享风格包。生成媒体与 `outputs/` 不入库。

| 类型 | 示例 |
|---|---|
| 图文动效 `text-motion` | [fold](text-motion/fold/README.md) |
| 数据演化 `data-evolution` | [compound-interest](data-evolution/compound-interest/README.md)、[compound-connect](data-evolution/compound-connect/README.md) |
| 原理隐喻 `principle-metaphor` | [pigeon](principle-metaphor/pigeon/README.md)、[luck-on-stage](principle-metaphor/luck-on-stage/README.md) |
| 三维空间 `spatial-3d` | [solar-system-journey](spatial-3d/solar-system-journey/README.md) |
| 纪实素材剪辑 `documentary-edit` | [american-science-milestones](documentary-edit/american-science-milestones/README.md) |

先按各示例 `assets/recipe.json` 和 README 恢复素材，再运行：

```powershell
uv run m2v validate --project examples/text-motion/fold
uv run m2v prepare --project examples/text-motion/fold
uv run m2v preview --project examples/text-motion/fold --limit-frames 30
```

其他示例将路径替换成上表目录。字体统一由 `uv run python fonts/fetch.py` 恢复；已有文件摘要不一致时恢复命令会拒绝覆盖。

## 深入研究与试制演练

以下是现有七部示例在[研究与试制](../.agents/skills/material2video/references/stage-research.md)下的操作演练，不代表本轮重新制作、补做研究或取得独立通过；历史材料保留其实际证据范围。具体方法见[标杆选择与深入拆解](../.agents/skills/material2video/references/reference-video-analysis.md)。

| 场景 | 预期操作与可观察结果 |
|---|---|
| 为 `text-motion/fold` 重设计文字与形体 | 选择可查看的整体视觉及排版参考，拆解比例、留白与文字/形体关系，先试制最能代表目标的画面；换字体或深底本身不证明目标成立 |
| 为 `data-evolution/compound-interest` 先给方案与图片 | 核对既有参考实际只覆盖了哪些静帧，补研究缺口；对应展示具体参考、采用转化和代表性当前画面，只报告静态覆盖，不继续生成完整视频 |
| 为 `data-evolution/compound-connect` 局部改数值 | 核对模型、布局及实际依赖，沿用仍有效的研究和视觉基线；数字变化影响对象尺度时扩大复查，不重开无关选案 |
| 为 `principle-metaphor/pigeon` 探索原创表达 | 从相关及跨题材作品研究主体形象、空间和适用材质光影，记录观察/解释/应用；用真实主体和内容试制，不把“原创”当作跳过研究的理由 |
| 为 `principle-metaphor/luck-on-stage` 改运动机制 | 实际查看对应完整动作与衔接窗口；静帧外观研究不授权运动、节奏或听感通过，关键未知补片段试制 |
| 为 `spatial-3d/solar-system-journey` 改空间表现 | 拆解实际参考的尺度、光向、镜头和主体层次，在正式链路验证代表画面及相机过程；准确的模型数据不自动证明美术效果 |
| 为 `documentary-edit/american-science-milestones` 重组剪辑 | 分开研究整体视觉、专项转场和信息组织；查看适用原片、核对事实/许可，参考画面不直接入片，实际入片素材继续按台账登记 |

上述选定视觉目标的适用评审，先盲看当前媒体，再在同轮对照提供实际参考及中性采用特征。缺参考时保留目标未验证，技术/可读性通过不代替目标兑现。目标与当前效果有差距时，按研究不足、实现偏差或参考不适合分别补查、修复或重选。


## 异步绘制最小示例

七部作品集合不变。原生异步Canvas示例见 [async-bitmap.tsx](../tests/fixtures/code-scenes/async-bitmap.tsx)，通过同一构建与采集入口验证 `waitForFrame` 的完成边界；调用与限制见[运行契约](../.agents/skills/material2video/references/code-scene-runtime.md#异步绘制完成边界)。它是接口演示与测试夹具，不是新增视频作品，也不代表复杂GPU动态已经通过。
