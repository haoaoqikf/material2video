# doc-archive-style Specification

## Purpose
把《从电报到大模型》的档案纪录片外观转成仓库内可安装、可验证的风格包，使通用作品能复用同一套深色档案框、暖白信息层、信号/波形/节点叠加与章节文字版式，而不是每次手工复刻；同时保留原作品的题材、素材与内容边界作为该风格的规范示例。

## Requirements

### Requirement: 档案纪录片风格包可用

仓库 SHALL 提供 `styles/doc-archive/`，清单 SHALL 声明 `types: ["general"]`、`frames: [{"width":1920,"height":1080}]` 与 `requires.narration = "none"`，并提供非空 `GUIDE.md` 与 `tokens.json`。作品通过 `project.json` 的 `style.id: "doc-archive"` 选择后，`m2v validate` 与 `m2v prepare` SHALL 记录其 id、version 与内容指纹；包内容变化 SHALL 使旧准备失效。包 SHALL NOT 登记 `assets`，SHALL 使用宿主已注册字体。

#### Scenario: 选择风格并准备

- **WHEN** 一个无旁白的 general 横屏作品声明 `style.id: "doc-archive"` 并执行 `prepare`
- **THEN** 准备产物记录风格身份与指纹，`m2v status` 显示所选风格与准备有效性

#### Scenario: 不兼容选择

- **WHEN** 非 general 作品、竖屏作品、有旁白作品或未知风格 id 选择该包
- **THEN** 校验明确失败并指出类型、画幅或旁白不匹配，不回退到无风格

### Requirement: 色板、版式与文字角色

`tokens.json` SHALL 提供档案深色底、暖白正文、铜色强调与冷青信息线，并说明各颜色只承担一个语义；SHALL 提供主体区、信息区、字幕安全区之外的标签区与章节文字的字号阶。字幕安全区 SHALL 只由场景上下文 `subtitleSafeArea` 提供，tokens SHALL NOT 复制一份几何。作品文字 SHALL 以对象名称、短贡献句与必要边界为主，风格包 SHALL NOT 规定题材文案。

#### Scenario: 场景读取参数

- **WHEN** 场景导入 `m2v/style` 的 `tokens`
- **THEN** 可用 tokens 取得颜色、分区与字号，且对象只读

#### Scenario: 未登记场景色

- **WHEN** 场景请求未登记的语义色或分区名
- **THEN** 组件明确抛错，不静默回退到默认色

### Requirement: 可复用组件

风格包 SHALL 提供档案媒体框、章节文字、信号线、波形、节点图、闪光环、序列连接与片尾署名块等可复用组件。组件 SHALL 使用受控帧号与固定种子，SHALL NOT 使用挂钟、`Math.random`、CSS 动画或组件计时器；媒体与字体就绪前 SHALL NOT 开始绘制。组件 SHALL NOT 自动修改作品画面，必须由作品显式导入。组件 SHALL 只接收媒体、文字、进度、强调色等 props，SHALL NOT 内置作品 slug、年份、机构名或章节数据。

#### Scenario: 确定性绘制

- **WHEN** 同一作品帧被两次独立录制
- **THEN** 同一帧画面一致，不因运行时刻或随机数变化

#### Scenario: 包内无题材内容

- **WHEN** 检查 `styles/doc-archive/` 的源码与 tokens
- **THEN** 不出现三个示例以外的作品 slug、十项里程碑文案、档案媒体 ID 或片尾署名文本

### Requirement: 风格示例作品（视频专属，不属于包）

仓库 SHALL 在 `styles/examples/doc-archive/american-science-milestones/` 提供规范示例，声明 `style.id: "doc-archive"`。该作品 SHALL 保持 12 幕、约 30 秒、60 fps、全程无旁白/配乐/音效、十项内容的顺序与贡献边界、素材按 ID 取用、片尾仅一次署名，以及观众可见文案不含内部路径。示例 SHALL 通过 v8 校验与 `prepare`，生成媒体 SHALL NOT 入库。题材数据、档案素材、分镜与逐场编排属于作品，SHALL NOT 进入风格包。

#### Scenario: 示例可校验

- **WHEN** 对 `styles/examples/doc-archive/american-science-milestones/` 运行 `m2v validate` 与 `prepare`
- **THEN** 校验通过，实际时长约 30 秒，无旁白与音轨，十项内容顺序与贡献边界不变

#### Scenario: 示例不被当作风格包

- **WHEN** 运行 `m2v styles` 或 `m2v styles --json`
- **THEN** `styles/examples/doc-archive/american-science-milestones` 不出现在风格清单中，也不能按风格 id 加载

### Requirement: 科学里程碑示例必须保持内容与审美契约（视频专属）

`american-science-milestones` 示例 MUST 位于 `styles/examples/doc-archive/american-science-milestones/`，保留现有十项内容、顺序及贡献边界，使用统一标准、1920×1080、60 fps、约 30 秒；开场 2 秒、十项主体 26 秒、片尾署名 2 秒。中文名称与贡献说明 MUST 为主信息；陌生英文缩写仅在首次出现时作为辅助识别，不得成为理解前提。MUST 全程无旁白、配乐、音效及素材原声，交付无音轨或全程数字静音。MUST 面向手机横屏播放完成字号、主体占比及遮挡风险复核，并针对前两秒复核主题建立、视觉钩子及手机尺寸下的辨识情况；不得声称测得真实平台跳出率。MUST 在全片及所有观众可见文字中禁止仓库内部文件名、路径和材料查阅提示；署名和版权说明仅以一份简短片尾内容出现，满足所用素材许可的作者、来源、许可和改动标识要求，详细来源记录仍留在作品材料中。MUST 保留素材留证及生成媒体不入库要求。该要求约束示例作品，不属于风格包。

作品 MUST 以档案纪录方向组织视觉承接，历史影像与实物优先，原理动画明确标注示意；MUST NOT 暗示未经证实的直接历史因果。四张基准 MUST 覆盖开场、登月、晶体管普通信息镜头及片尾。各项 MUST 围绕一个主要视觉变化组织，减轻年份、英文装饰与说明的竞争，MUST NOT 以照片缓慢缩放作为全片主要动画手段。

大语言模型镜头 MUST 以中文为主、明确标注为示意的 ChatGPT 交互呈现具体产品实例，并使用未经改动的官方图标及 `ChatGPT / OpenAI` 名称；画面 MUST NOT 暗示 OpenAI 为作品背书，或将大语言模型研究与发展归功于单一机构。该镜头 MUST 为 4.5 秒。片尾署名 MUST 为 2 秒，仅出现一次，去除重复小标题，手机横屏尺寸下必要的署名文字 MUST 清晰可读。完整来源和许可记录 MUST 保存在作品材料中，ChatGPT 商标素材 MUST 有官方来源记录且不得误称为开放许可。

重制 MUST 保留同时间码、同显示尺寸的新旧对照，说明视觉重心、信息层级、叙事变化与一致性的具体改进。最终全片帧序列、交界与风险加密检查、素材审计及静音检查 MUST 绑定新候选准备指纹和最终文件摘要，不得沿用旧版通过结论。共享流程与实际重制 MUST 均完成并关闭必改项后，才可标记整体变更完成。

助手 MUST 完成开场、登月、晶体管普通信息镜头及片尾四张基准复核；登月镜头已精制但晶体管普通镜头缺少正式文案或手机尺寸检查时，四张基准仍未完成。若新旧对照及全片帧序列显示各段仍以照片缩放和文字替换主导，助手 MUST 重构主体变化与镜头承接并在新版本复查，MUST NOT 以更新设计稿代替重制。仅更新共享指导而没有经过完整复核的新成片时，实际重制任务 MUST 保持未完成。

#### Scenario: 重制保持硬约束

- **WHEN** 生成并验收新版本科学里程碑示例
- **THEN** 片长约 30 秒、约 1800 帧，画幅与帧率正确，十项次序及贡献边界不变，全程无声；中文优先且缩写非理解前提；手机横屏与前两秒开场检查完成，观众可见文案无内部引用，且只有一份满足许可要求的简短片尾署名

#### Scenario: 大语言模型以具体产品建立识别

- **WHEN** 观众观看 4.5 秒的大语言模型段落
- **THEN** 可辨认中文 ChatGPT 示意交互及原样官方图标，理解其为全球研究积累中的具体产品实例，且不会被画面引导为 OpenAI 背书或单一创造

#### Scenario: 片尾署名压缩后仍可读

- **WHEN** 观众在横屏手机尺寸观看 2 秒片尾
- **THEN** 不出现重复小标题，只出现一份片尾署名，必要作者、许可、改动及本片许可信息清晰可读，详细出处不要求观众查阅内部文件

#### Scenario: 只优化重点镜头

- **WHEN** 登月镜头已精制但晶体管普通镜头缺少正式文案与手机尺寸检查
- **THEN** 四张基准尚未完成，助手补齐普通镜头复核后再标记该阶段完成

#### Scenario: 新版本仍主要靠照片缩放

- **WHEN** 新旧对照及全片帧序列显示各段仍以照片缩放和文字替换主导
- **THEN** 助手登记表现问题，重构主体变化与镜头承接并在新版本复查，不能以更新设计稿代替重制

#### Scenario: 仅完成流程文档

- **WHEN** 共享指导已更新但没有经过完整复核的新成片
- **THEN** 实际重制任务保持未完成，不归档整体变更

#### Scenario: 开场首两秒未建立主题

- **WHEN** 前两秒的画面无法迅速让目标观众辨认主题，或没有可辨认主体/有意义动作
- **THEN** 作为审美问题重构开场并复核；不使用虚构的平台跳出率或分数作为验收
