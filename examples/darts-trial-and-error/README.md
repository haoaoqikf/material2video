# darts-trial-and-error 内容驱动讲解示例

原文为 `article.md`，分镜为 v8 全画布代码场景。目标时长 120～180 秒，以真实配音准备结果为准；
**1080×1920 竖屏**、60 fps，自动烧录字幕。视觉设计依据见 [DESIGN.md](DESIGN.md)。

## 论点与画面对应

| 文章论点 | 场景 / 旁白 ID | 画面与组件 |
| --- | --- | --- |
| 缺少反馈时准备不产生信息 | `darts-point` / darts-point-0 | 靶面与未出手的箭（SVG） |
| 推演与试验各解决什么 | `darts-compare` / darts-compare-0、darts-compare-1 | 两块对照牌 |
| 看见偏差，再调整方向 | `darts-demo` / darts-demo-0、darts-demo-1、darts-demo-2 | 三次落点飞入（GSAP） |
| 把反馈写成记录 | `darts-record` / darts-record-0 | 已导入示意表（`useMediaAsset`） |
| 从一次尝试走到下一次 | `darts-chain` / darts-chain-0、darts-chain-1、darts-chain-2 | 反馈链三个环节 |
| 试之前先设好边界 | `darts-bounds` / darts-bounds-0、darts-bounds-1、darts-bounds-2 | 三条边界与依赖项 |

三次落点都由 `darts-demo-*` 的真实旁白时间窗触发，GSAP 负责飞入；不用固定时长的无声技术末幕。
三片合计覆盖 Motion、ECharts、GSAP、Three.js、React Three Fiber 与 Drei。

示意表是已导入素材 `darts-feedback`（CC0，见 [素材许可](assets/LICENSE.md)），在代码里用
`useMediaAsset('darts-feedback')` 按 ID 取用，地址与实测尺寸来自导入留证。靶面落点、记录表
均为示意，不代表真实测量；这一片没有音床，成片声音全部来自统一音轨的旁白。

## 制作

先阅读原文并执行 `m2v general input-review`，填写语义审查；查询当前音色列表并按新旁白选择、
保存理由和摘要。随后运行：

```powershell
uv run m2v validate --project examples/darts-trial-and-error
uv run m2v prepare --project examples/darts-trial-and-error
uv run m2v preview --project examples/darts-trial-and-error
uv run m2v render --project examples/darts-trial-and-error
```

准备与审查记录位于本示例 `outputs/`；预演和成片位于 `videos/examples/darts-trial-and-error/outputs/`，
均不入库。材料、代码、画幅或登记素材变化后重新准备与完整预演。

字段见 [分镜结构](../../.agents/skills/material2video/references/storyboard-schema.md) 与
[制作流程](../../.agents/skills/material2video/references/production-workflow.md)。

录制采用共享受控时钟按 60 fps 顺序逐帧采集，等待本帧动画及绘制完成再截图；机器负载只影响制作耗时。修改源码后需重新 prepare 与完整 preview，旧实时录制缓存不复用。
