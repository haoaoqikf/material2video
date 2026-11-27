# 随附示例

五部作品放在 `examples/<类型>/<作品名>/`。各自拥有 project v3 工程、分镜 v9、运行源码、依赖锁、字体登记与恢复入口。作品专属画面与参数在各自 `scenes/`。生成媒体与 `outputs/` 不入库。图文动效 `text-motion` 仍支持初始化与制作，当前不附带示例。

| 类型 | 示例 |
|---|---|
| 数据演化 `data-evolution` | [compound-after-20](data-evolution/compound-after-20/README.md)（38.7 秒，本地恢复原克隆音色）、[global-market-cap-race-portrait](data-evolution/global-market-cap-race-portrait/README.md)（107.13 秒，竖屏榜首交接） |
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

《复利 40 年》还需安装 `qwen3-tts` 可选依赖，在 `setup` 前恢复本地音色，按[该例 README](data-evolution/compound-after-20/README.md)执行。字体由各作品的 `uv run python fonts/fetch.py` 恢复，已有文件摘要不一致时拒绝覆盖。主项目入口可委托同一本地实现，例如 `uv run m2v render --project examples/principle-metaphor/luck-on-stage`。

## 深入研究与试制演练

以下是五部示例在[研究与试制](../.agents/skills/material2video/references/stage-research.md)中的操作演练。具体方法见[标杆选择与深入拆解](../.agents/skills/material2video/references/reference-video-analysis.md)。

| 场景 | 预期操作与可观察结果 |
|---|---|
| 为 `data-evolution/compound-after-20` 调整年柱生长 | 核对柱脚零线、年份错峰与读数时机，对比代表性过程，并检查第三幕终态到第四幕起态的柱体身份与位置 |
| 为 `data-evolution/global-market-cap-race-portrait` 调整榜首交接 | 核对双卡与三卡的固定公司身份、高光随实际领先变化、前十名完整及抖音白色叠层在右侧和底部的反差 |
| 为 `principle-metaphor/luck-on-stage` 改运动机制 | 用有序抽帧和适用信号核查对应完整动作与衔接窗口；静帧外观研究不授权运动、节奏或听感通过，关键未知补片段试制 |
| 为 `spatial-3d/solar-system-journey` 改空间表现 | 拆解实际参考的尺度、光向、镜头和主体层次，在正式链路验证代表画面及相机过程；准确的模型数据不自动证明美术效果 |
| 为 `documentary-edit/american-science-milestones` 重组剪辑 | 分开研究整体视觉、专项转场和信息组织；查看适用原片、核对事实/许可，参考画面不直接入片，实际入片素材继续按台账登记 |

五部示例保留研究、总设计与每场文档。使用示例重新制作时，按[现行审核策略](../.agents/skills/material2video/references/review-contract.md)执行关键帧、适用关键样片、技术 QA 与总代理整片复核。历史报告按原版本保留。


## 异步绘制最小示例

原生异步 Canvas 接口的[最小夹具](../tests/fixtures/code-scenes/async-bitmap.tsx)通过同一构建与采集入口验证 `waitForFrame` 的完成边界。调用与限制见[运行契约](../.agents/skills/material2video/references/code-scene-runtime.md#异步绘制完成边界)。
