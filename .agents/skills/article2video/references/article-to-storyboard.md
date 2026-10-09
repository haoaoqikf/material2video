# 文章生成单场景分镜

最终运行时只读取文章、v4 分镜、媒体清单和声明的本地资产。创作次序固定为：输入审查 → 核心观点与隐喻设计 → 分镜及动画编排 → 配音准备 → 实际时长检查 → 评审与渲染。工具不会替代 AI 阅读文章和理解语义。

全片使用同一个视觉世界，`stages[]` 阶段代表推理进展，不是换场：阶段之间延续同一组对象、母题与镜头语汇，只让状态、焦点和文字随论证推进而变化。

仓库固定分发 `buffer-smoothing`、`darts-trial-and-error`、`keynote-baseline` 三个示例，`examples/` 最多 3 个。后续只能修改这三个示例，不新增、删除或替换目录；测试会检查该固定集合。

开始口播重写或生成分镜之前，必须先按[输入文章审查](input-review.md)核对正文长度、观点集中性和单场景表达能力。标准正文为约150字，通过范围130～170字；最终口播同样为130～170字。文章过长、观点分散或必要推理依赖切换多个独立视觉世界时，保留原文、给出修改建议和合规候选稿后停止。候选稿须用户明确采用并重新审查后才能制作。

## 创作步骤

1. **提炼观点**：用一句话写出可讨论的核心判断、因果链和边界；删去不能服务结论的旁支，不虚构数据或例子。
2. **选择视觉隐喻**：找一个能贯穿全文的持续世界，例如飞镖、投掷者与靶；次数、命中、镜头和文字在此世界内变化。
3. **搭建 world 与关键阶段草稿**：声明全片唯一 renderer、稳定对象身份、基础数据、全局镜头和对象状态轨道；先编排开场、核心论证、高潮的完整 v4 阶段草稿和全局时间轴。复杂几何或组合动作用 code renderer；受控原语能清楚表达时优先 tree renderer。
4. **关键幕静音动态粗剪**：生成关键阶段样片，先静音播放，确认每阶段的状态起点、变化、结果、焦点/镜头推进及稳定停留。相同构图和同一视觉世界允许持续；如果只变化字幕或标签、无法从图形看出论证推进，记录必改项并返回视觉转译/动画设计，不能继续铺开全片。
5. **铺开其余 stages**：关键阶段静音动态通过后，再将其余推理阶段编排进同一世界。每阶段声明数据、完整视觉意图、口播语义段与 beat；允许推拉、焦点改变和对象状态变化。
6. **验证视觉论证**：去掉正文后，图形关系与变化仍须表达该阶段所述的因果、对照或结果。不要以文字卡片换布局冒充图形论证，也不要将历史多幕作品描述为已通过单场景评审。
7. **规划动画**：状态轨道、动作和镜头都绑定全局 beat 或阶段 phase。不要手写帧边界，不建立作品私有时间轴；beat 结束后留至少12帧稳定阅读时间。
8. **严格校验**：修复未知字段、类型、重复 id、无效绑定、轨道冲突、时长及口播长度错误，直到严格校验通过。
9. **准备媒体并复查实际时长**：配音、字幕和动作共用媒体派生的全局时间轴。实际时长须35～45秒；超限时调整文案、正常语速或有意义停顿并重新 prepare，不能截断口播或补空白。
10. **有声评审与渲染**：查看关键阶段联系表、有声样片和全片有声评审版，填写静态、动态和五项连续性结论。全片节奏必须独立达到4/5，并引用有声预演的时间码或明确阶段；低于4、缺分或缺少可定位依据均阻断正式渲染。关键幕 pending/fail 及未解决必改项继续阻断。素材或源文件变化后重新生成受影响的评审材料。

## 视觉论证与 renderer 选择

每个 `stage.visualIntent` 声明 `relation`、`focus`、`composition`、`density`、`tone`、`mode`、`claim`、`showWithoutText`、`primaryObject` 与 `motionMeaning`。这些字段描述同一个视觉世界中该阶段新增的认知；禁止通过不同完整页面条件分支制造虚假的连续性。

默认使用受控场景树，并查[视觉原语目录](primitive-catalog.md)。只有原语不能表达该世界所需的结构、状态或按帧几何时才使用作品级代码模块；模块必须符合[代码场景](code-scenes.md)的固定依赖白名单、纯函数、确定性求值和探针协议。新模块放在文章目录的 `scenes/` 下，并写 `motion-design.md` 解释对象与状态演进。

`visualIntent.mode` 的候选包括 `metaphor`、`process`、`comparison`、`cycle`、`chart`、`image`、`typography`。模式数量只作报告，不设最低配额；一个隐喻可贯穿全片。结构证据校验会检查树形声明与场景结构是否冲突，但脚本不判断语义；图形是否实际承担论证须由评审者查看画面给结论。

## 常用校验

```bash
uv run python .agents/skills/article2video/scripts/validate.py storyboard.json --strict --json
uv run python .agents/skills/article2video/scripts/prepare.py --storyboard storyboard.json
uv run python .agents/skills/article2video/scripts/validate.py storyboard.json --strict --media videos/<slug>/outputs/media/media.json
uv run python .agents/skills/article2video/scripts/review.py --storyboard storyboard.json --media videos/<slug>/outputs/media/media.json --check-determinism
uv run python .agents/skills/article2video/scripts/production.py status --storyboard storyboard.json
```

完整字段、边界和一份结构样例见[分镜脚本结构](storyboard-schema.md)；时长、输入审查、媒体、渲染及评审操作分别见[输入文章审查](input-review.md)、[媒体契约](media-contract.md)、[渲染契约](render-contract.md)和[视觉评审量表](visual-review-rubric.md)。
