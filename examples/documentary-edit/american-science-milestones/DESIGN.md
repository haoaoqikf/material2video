# 全片设计：american-science-milestones

## 当前流程与历史证据范围

研究固定见[RESEARCH.md](RESEARCH.md)，每个正式场景文档继续保留；日常记录可用目标、画面与注意力、实现、验证与未知四问，复杂机制沿原详细编排深化。成熟方案优先采用或改造。

本轮仅同步样品 static/motion 接口及制作指导，没有改画面或重新审美验收。下文历史通过保留其原版本和范围，不能授权新的 review v3：关键帧须按所选风格世界级水准独立盲审及对照，过程默认独立对照，成片由新代理终审。纯静态无需编码视频。


## 目标、约束与选案依据

展示美国主导或参与的科技节点，保留全球合作和贡献边界。具体原始要求、选案和历史限制保留在[分层前原记录](design/previous-design.md)，不能将作者转化扩大或缩小为新授权。当前类型、画幅、帧率和精确时间以[project](project.json)及[分镜](storyboard.json)为准。

## 当前硬约束与共同规则

面向中国普通观众，1920×1080、60fps、30秒，开场2秒、主体26秒、片尾2秒；正式预算由分镜维护。无旁白、配乐与音效。首帧登月档案建立主题，美国主导或参与不等同单国独创；名称和短贡献句优先，不以ENIAC/ARPANET等英文缩写为理解前提。档案主导，机制示意不争焦点；不增加未经证实的节点间因果。素材署名与许可保留原材料要求，手机原帧和缩略图按实际显示核对。

## 五维共同语言与贯穿对象

真实档案为主体，中文名称和贡献句组织阅读；素材原光比配墨黑、暖白及少量铜/冷青。动作服务信号、连接、尺度或生成，禁止用视觉线索制造未经证实的直接因果。无旁白、配乐与音效；转场按题材与共享视觉锚点安排。

## 结构、节奏与有效范围

场序和执行时间由分镜维护；各场详细编排如下。当前依据整理自既有设计及实现，本轮没有补造研究、重新制作或授予独立通过。历史材料只支持其原范围；新修订按[场景设计指南](../../../.agents/skills/material2video/references/scene-design.md)补足实际目标与证据。[来源](SOURCES.md)；[原验证记录](VERIFICATION.md)；

## 场景索引

| scene.id | 叙事作用 | 场景设计 |
|---|---|---|
| opening | 从电报到大模型 | [opening](design/scenes/opening.md) |
| telegraph | 摩尔斯电报 | [telegraph](design/scenes/telegraph.md) |
| telephone | 贝尔电话 | [telephone](design/scenes/telephone.md) |
| flight | 莱特兄弟、动力飞行 | [flight](design/scenes/flight.md) |
| trinity | Trinity核试验 | [trinity](design/scenes/trinity.md) |
| eniac | ENIAC计算机 | [eniac](design/scenes/eniac.md) |
| transistor | 晶体管 | [transistor](design/scenes/transistor.md) |
| moon | 阿波罗11号、登月 | [moon](design/scenes/moon.md) |
| arpanet | ARPANET、四节点网络 | [arpanet](design/scenes/arpanet.md) |
| genome | 人类基因组计划 | [genome](design/scenes/genome.md) |
| llm | 大语言模型、GPT-3 | [llm](design/scenes/llm.md) |
| closing | 知识接力 | [closing](design/scenes/closing.md) |
