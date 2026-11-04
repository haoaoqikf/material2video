## Why

项目已有成熟图形底座，但部分风格仍重复编写曲线几何，流程图布局、数学排版和通用图标缺少统一入口，合成层转场也仅支持淡化。引入经过调研的外部能力，并保持离线、逐帧确定性与来源可追溯，可以减少作品代码并拓展讲解题材。

## What Changes

- 统一共享图表与风格曲线的 D3 几何实现，保留现有风格公开接口与视觉语义。
- 接入 ELK，提供一次性异步布局与纯时间安全的图示绘制入口。
- 接入 KaTeX，提供公式组件并登记、恢复和核验公式字体。
- 通过 SDK 按需导出 Lucide 图标，不引入整库动态图标注册表。
- 接入与现有版本一致的 @remotion/transitions，增加方向化滑动、擦除、圆形揭示等通用转场，统一 Python/Web 枚举和重叠时长。
- 同步依赖来源许可、制作契约、示例、README 与架构；验证只覆盖受影响集合及最小动态样片。

## Capabilities

### New Capabilities

- `diagram-layout`：有界、稳定的 ELK 布局与静态图示绘制。
- `math-and-icons`：离线公式排版、受控字体就绪及按需图标入口。
- `scene-transitions`：统一帧数语义的通用场景转场。

### Modified Capabilities

- `shared-motion`：共享曲线几何与风格复用边界。
- `font-pipeline`：纳入 KaTeX 公式字体并使用既有恢复机制。

## Impact

影响 Web SDK、代码场景打包器、general 校验/准备/合成、字体登记、对应文档与规范示例。不升级分镜版本，不增加其他动画引擎，不引入 Lottie、Shiki 或新的 3D 资产类型。
