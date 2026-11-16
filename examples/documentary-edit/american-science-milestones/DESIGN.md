# 全片设计：american-science-milestones

## 2026-11-16 重制启动：待确认方案

用户要求按新流程升级，时长基本不变，十项科技成就不变，先看方案。建议保留 30 秒和十项原顺序，继续面向中文横屏观看；主题为《从电报到大模型》，同时保留“美国主导或参与”的事实边界。开场用电报原件和拟音，登月档案留在正文；结尾用一段中文生成示意回应开头。全片档案优先，以实物、人物或一个动作承担每段信息；无旁白，声音只强调少数动作，核试验段留白。片尾留足适用署名所需阅读时间。

重制范围覆盖原片 0–30 秒：开场、各场用材与衔接、生成段、声音和片尾。由于开场承诺及最终回报均变，回到研究与创意试制，先比较大模型段载体，再验证电报到电话、登月以及片尾的关键窗口。研究依据与待验证问题见[重制前研究](RESEARCH.md#2026-11-16-重制前研究档案短片)。本次仅记录策划，正式设计、场景及参数随试制结果更新。

旧片比较材料为本地 `outputs/video.mp4`，SHA-256 为 `1a14366e97eb904e4eca6deb126c30f1e06e113825283ea37b5de611e8df5e90`，与本地交付及溯源记录一致。本轮未覆盖旧片、未新建正式基线；确认方向后，在修改材料前保护旧片及对应记录。

## 当前流程与历史证据范围

研究固定见[RESEARCH.md](RESEARCH.md)，每个正式场景文档继续保留；日常记录可用目标、画面与注意力、实现、验证与未知四问，复杂机制沿原详细编排深化。成熟方案优先采用或改造。

本文保留原制作版本的设计和评审记录。新版交付按[现行审核策略](../../../.agents/skills/material2video/references/review-contract.md)执行正式关键帧、适用关键样片、技术 QA 与总代理整片复核，旧结论仅覆盖原版。


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
