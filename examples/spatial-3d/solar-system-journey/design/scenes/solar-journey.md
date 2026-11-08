# 场景 solar-journey

## 目标、继承与依据

本场：solar-journey。全片目标：通过空间旅程建立太阳系层次、尺度和遥远感。继承[总设计](../../DESIGN.md)的五维共同语言和采用范围。原指令及历史细节见[原记录](../previous-design.md)。本次只分层整理，不补造外部研究、动作或独立通过。

## 过程判据

离场、空间移动、抵达和停留分别有观察职责，避免短促加速替换天体。天顶附近朝向连续，独立行星分离、卫星从属；过场不能长时间无新信息。世界路径正确仍需核对屏幕尺度、相邻帧位移与实际方向。

## 对象、构图与视听机制

单场内部按行程镜头展开；离场、移动、抵达和停留具有不同职责，防止独立行星挤靠或镜头突跳。本场执行入口与时点由分镜关联，以下说明具体编排。

## 节拍与执行对应

| 事件/阶段引用 | 编排与观察任务 |
|---|---|
| 本场建立、关键变化、稳定 | 以当前场景代码求值；无命名事件不伪造事件表 |


## 具体编排依据

以下为本场保留的具体设计；准确帧窗及参数以分镜/代码为准，旧通过不升级。

| 镜头 | 原场景帧窗 [起,止) | 对象、变化与目标 | 实现引用与验收 |
|---|---|---|---|
| aerial-dive（A） | 0–360 | sun：从太阳系上方连续俯冲到太阳，无切换。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=aerial-dive]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| sun-station（B） | 360–714 | sun：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=sun-station]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| sun-to-mercury（B） | 714–924 | mercury：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=sun-to-mercury]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| mercury-station（B） | 924–1329 | mercury：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=mercury-station]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| mercury-to-venus（B） | 1329–1539 | venus：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=mercury-to-venus]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| venus-station（B） | 1539–1929 | venus：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=venus-station]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| venus-to-earth（B） | 1929–2139 | earth：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=venus-to-earth]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| earth-hero（A） | 2139–2676 | earth：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=earth-hero]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| earth-to-moon（B） | 2676–2886 | moon：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=earth-to-moon]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| moon-station（B） | 2886–3280 | moon：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=moon-station]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| moon-to-mars（B） | 3280–3490 | mars：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=moon-to-mars]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| mars-station（B） | 3490–3908 | mars：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=mars-station]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| mars-to-ceres（B） | 3908–4118 | ceres：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=mars-to-ceres]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| ceres-station（B） | 4118–4448 | ceres：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=ceres-station]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| ceres-to-jupiter（B） | 4448–4658 | jupiter：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=ceres-to-jupiter]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| jupiter-station（B） | 4658–5136 | jupiter：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=jupiter-station]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| jupiter-to-saturn（B） | 5136–5346 | saturn：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=jupiter-to-saturn]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| saturn-hero（A） | 5346–5925 | saturn：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=saturn-hero]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| saturn-to-uranus（B） | 5925–6135 | uranus：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=saturn-to-uranus]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| uranus-station（B） | 6135–6534 | uranus：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=uranus-station]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| uranus-to-neptune（B） | 6534–6744 | neptune：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=uranus-to-neptune]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| neptune-station（B） | 6744–7165 | neptune：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=neptune-station]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| neptune-to-pluto（B） | 7165–7375 | pluto：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=neptune-to-pluto]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| pluto-station（B） | 7375–7787 | pluto：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=pluto-station]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| pluto-to-kuiper（B） | 7787–7997 | kuiper：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=pluto-to-kuiper]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| kuiper-station（B） | 7997–8318 | kuiper：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=kuiper-station]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| kuiper-to-heliopause（B） | 8318–8618 | heliopause：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=kuiper-to-heliopause]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| heliopause-station（B） | 8618–9082 | heliopause：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=heliopause-station]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| heliopause-to-oort（B） | 9082–9322 | oort：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=heliopause-to-oort]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| oort-hero（A） | 9322–9894 | oort：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=oort-hero]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| oort-tail（A） | 9894–10473 | oort：收尾：继续向外，太阳成为亮点。 | [storyboard.json](../../storyboard.json) / scene=solar-journey / content.props.shots[id=oort-tail]；[journey.tsx](../../scenes/journey.tsx)；按[体验条件](../previous-design.md#核心体验与时间预算)核对主体认回、方向连续与观察时间 |

## 衔接与实现

首场建立对象和主题，不借前场解释。片尾留出结果消化窗口，保持主题和声音自然收束。正式转场取分镜值，cut允许承接观察对象，不强加非cut效果。复用既有运行时、资源和共享组件；本次未新增画面实现或依赖。

## 验证范围

当前媒体、原报告和未完成边界沿[总设计](../../DESIGN.md)；本场按上列具体关系取证。结构整理不授予实际效果通过。
