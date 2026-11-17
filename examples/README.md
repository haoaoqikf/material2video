# 随附示例

五部作品放在 `examples/<类型>/<作品名>/`，均为 project v3 独立工程与分镜 v9：各自拥有运行源码、依赖锁、字体登记与恢复入口。作品专属画面与参数在各自 `scenes/`，不作为共享风格包。生成媒体与 `outputs/` 不入库。图文动效 `text-motion` 仍支持初始化与制作，当前不附带示例。

| 类型 | 示例 |
|---|---|
| 数据演化 `data-evolution` | [compound-interest](data-evolution/compound-interest/README.md)、[compound-connect](data-evolution/compound-connect/README.md) |
| 原理隐喻 `principle-metaphor` | [luck-on-stage](principle-metaphor/luck-on-stage/README.md) |
| 三维空间 `spatial-3d` | [solar-system-journey](spatial-3d/solar-system-journey/README.md)（120秒连续旅程编排） |
| 纪实素材剪辑 `documentary-edit` | [american-science-milestones](documentary-edit/american-science-milestones/README.md) |

先按各示例 README 安装依赖并恢复素材与字体，然后在作品目录直接运行：

```powershell
pnpm install --frozen-lockfile --ignore-workspace
uv sync --frozen
$env:M2V_FONT_CACHE = "<字体缓存目录>"   # 或使用 fonts/.cache / --download
pnpm run setup --download --install-browser
pnpm run validate
pnpm run build
pnpm run preview --limit-frames 30
pnpm run render
```

其他示例只在对应目录执行同样步骤。字体由各作品的 `uv run python fonts/fetch.py` 恢复；已有文件摘要不一致时拒绝覆盖。主项目入口仍可委托同一本地实现，例如 `uv run m2v render --project examples/principle-metaphor/luck-on-stage`。

## 深入研究与试制演练

以下是现有五部示例在[研究与试制](../.agents/skills/material2video/references/stage-research.md)下的操作演练，不代表本轮重新制作、补做研究或取得独立通过；历史材料保留其实际证据范围。具体方法见[标杆选择与深入拆解](../.agents/skills/material2video/references/reference-video-analysis.md)。

| 场景 | 预期操作与可观察结果 |
|---|---|
| 为 `data-evolution/compound-interest` 先给方案与图片 | 核对既有参考实际只覆盖了哪些静帧，补研究缺口；对应展示具体参考、采用转化和代表性当前画面，只报告静态覆盖，不继续生成完整视频 |
| 为 `data-evolution/compound-connect` 局部改数值 | 核对模型、布局及实际依赖，沿用仍有效的研究和视觉基线；数字变化影响对象尺度时扩大复查，不重开无关选案 |
| 为 `principle-metaphor/luck-on-stage` 改运动机制 | 用有序抽帧和适用信号核查对应完整动作与衔接窗口；静帧外观研究不授权运动、节奏或听感通过，关键未知补片段试制 |
| 为 `spatial-3d/solar-system-journey` 改空间表现 | 拆解实际参考的尺度、光向、镜头和主体层次，在正式链路验证代表画面及相机过程；准确的模型数据不自动证明美术效果 |
| 为 `documentary-edit/american-science-milestones` 重组剪辑 | 分开研究整体视觉、专项转场和信息组织；查看适用原片、核对事实/许可，参考画面不直接入片，实际入片素材继续按台账登记 |

五部示例保留研究、总设计与每场文档。使用示例重新制作时，按[现行审核策略](../.agents/skills/material2video/references/review-contract.md)执行关键帧、适用关键样片、技术 QA 与总代理整片复核。历史报告按原版本保留。


## 异步绘制最小示例

五部作品集合不变。原生异步Canvas示例见 [async-bitmap.tsx](../tests/fixtures/code-scenes/async-bitmap.tsx)，通过同一构建与采集入口验证 `waitForFrame` 的完成边界；调用与限制见[运行契约](../.agents/skills/material2video/references/code-scene-runtime.md#异步绘制完成边界)。它是接口演示与测试夹具，不是新增视频作品，也不代表复杂GPU动态已经通过。
