# 全片设计：pigeon

## 目标、约束与选案依据

让观众区分定时喂食与鸽子动作，理解巧合怎样被误认为规律。具体原始要求、选案和历史限制保留在[分层前原记录](design/previous-design.md)，不能将作者转化扩大或缩小为新授权。当前类型、画幅、帧率和精确时间以[project](project.json)及[分镜](storyboard.json)为准。

## 当前硬约束与共同规则

计时周期保持15秒，鸽子动作不触发喂食。房间内食槽与计时器保持方位；由计时器转向鸟再回计时器。食物到达后再接近/啄食，声音由现有事件关联，不能剪成转圈导致落粮。

## 五维共同语言与贯穿对象

同一房间、食槽、计时器和鸽子维持空间身份。物体隐喻与连续时间组织叙事；转圈、接近、落粮与啄食错开。计时器和喂食声按命名事件，cut按观察对象切换。

## 结构、节奏与有效范围

场序和执行时间由分镜维护；各场详细编排如下。当前依据整理自既有设计及实现，本轮没有补造研究、重新制作或授予独立通过。历史材料只支持其原范围；新修订按[场景设计指南](../../../.agents/skills/material2video/references/scene-design.md)补足实际目标与证据。

## 场景索引

| scene.id | 叙事作用 | 场景设计 |
|---|---|---|
| box | 箱子里的等待 | [box](design/scenes/box.md) |
| feeder | 食槽定时打开，与它做什么无关 | [feeder](design/scenes/feeder.md) |
| wander | 到处找吃的 | [wander](design/scenes/wander.md) |
| coincide | 巧合的一刻 | [coincide](design/scenes/coincide.md) |
| repeat | 它开始重复 | [repeat](design/scenes/repeat.md) |
| again | 斯金纳的鸽子实验 | [again](design/scenes/again.md) |
