# 全片设计：american-science-milestones

## 2026-11-16 重制启动

用户确认「可以，就按你的这个方案。按照新流程制作。」保留 30 秒、十项原顺序和中文横屏观看。开场的馆藏电报纸带承接到第一项，末段的双层纸带式中文问答回应开头。全片用实物、人物或一个动作承担每段信息。拟音只跟随电键、点划与部分网络连线，核试验段静音。片尾保留晶体管照片的必要署名。

重制覆盖原片 0–30 秒的开场、各场用材与衔接、生成段、声音和片尾。开场与结尾回到研究试制，比较同内容的构图，按独立评审的实际缺口返工。设计承诺、试制观察和实际取证分别保存在场景文档、[研究](RESEARCH.md#2026-11-16-重制前研究档案短片)及[验证记录](VERIFICATION.md)。

旧片位于 `outputs/baselines/3f72b0ed4d174d0da7d75b6957f2a873/media/0000.mp4`，SHA-256 为 `1a14366e97eb904e4eca6deb126c30f1e06e113825283ea37b5de611e8df5e90`。对应准备、交付、溯源、性能及 QA 记录随基线保留。可编辑旧材料取 Git `3bd0d620`，新版评审周期为 `fe8e9e9cd68e43ec9af59533dbe859f8`。

## 当前流程与历史证据范围

研究固定见[RESEARCH.md](RESEARCH.md)，每个正式场景文档继续保留；日常记录可用目标、画面与注意力、实现、验证与未知四问，复杂机制沿原详细编排深化。成熟方案优先采用或改造。

本文保留原制作版本的设计和评审记录。新版交付按[现行审核策略](../../../.agents/skills/material2video/references/review-contract.md)执行正式关键帧、适用关键样片、技术 QA 与总代理整片复核，旧结论仅覆盖原版。


## 目标、约束与选案依据

展示美国主导或参与的科技节点，保留全球合作和贡献边界。具体原始要求、选案和历史限制保留在[分层前原记录](design/previous-design.md)，不能将作者转化扩大或缩小为新授权。当前类型、画幅、帧率和精确时间以[project](project.json)及[分镜](storyboard.json)为准。

## 本版硬约束与共同规则

面向中文观众，1920×1080、60 fps、1800 帧。正式时间与拟音事件由分镜维护。首帧建立片名与电报纸带，十项贡献按美国主导或参与的范围表述，并保留基因组计划国际合作和大模型全球研究背景。节点之间按时间与尺度衔接，因果关系只在有依据时说明。文字优先显示中文对象和短结论，必要的证据出处和示意边界放在次要位置。

## 五维共同语言与贯穿对象

档案主体优先。纸带的暖色、墨色标题和少量铜色延伸到示意画面，历史照片保留原光比。首尾用文字的传输和生成建立联系，机柜到晶体管用硬切说明尺度，16 毫米月面行动单独停留。点划和网络连线只按分镜事件变化，部分事件共用拟音起点。无旁白和配乐，设计声音不代替画面解释。

结尾采用网页原生曲面纸带。当前采集 `d3f6d68bb8d847e3a3bec7e31f96813e` 与原选案 `e72334dcb8bb47a9ba7a6355442097fb` 的关键帧和完整视频逐字节一致。按工具凭据复用独立盲审与标杆对照，另完成同源 4.5 秒的独立过程复查。采用依据是问答层级、印字和纸面贴合、卷边间隔及手机阅读窗口。纸面纹理的变化幅度仍小于实拍标杆。此基线覆盖结尾镜头，整片另从当前正式合成抽帧，核对画面、时间轴及适用音频信号。

## 结构、节奏与有效范围

各场以分镜顺序为准。需要加密取证的风险窗口包括开场与电报交界、核试验静音、机柜切晶体管、月面完整动作、四节点成网、基因序列揭示、大模型答句和片尾。正式关键帧从当前合成取证，整片以代表帧、各风险窗口有序帧、时间轴和适用信号复核。历史或试制证据限于各自覆盖范围。[来源](SOURCES.md) · [验证记录](VERIFICATION.md)

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
| llm | 大语言模型、中文生成示意 | [llm](design/scenes/llm.md) |
| closing | 必要署名 | [closing](design/scenes/closing.md) |
