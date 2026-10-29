# 架构与模块职责

Material2Video 通过 Python 命令行准备和校验作品，使用 Remotion 完成渲染。业务类型彼此独立，共用路径、素材、构建和交付基础设施。

## 模块边界

- `src/m2v/core/`：作品与工作区契约、路径、资产、指纹、安全策略和公共错误。它不包含具体视频类型的业务流程。
- `src/m2v/types/`：类型目录、注册表和金融、通用、住宅类型适配器。新类型从目录发现，再由适配器实现校验、准备、预演、渲染及可选评审。
- `src/m2v/types/general/code_scenes/config.py`：代码场景入口校验、录制配置与确定性打包；`capture.py`：逐帧采集、片段缓存与编码验收；`worker.py`：pure-time 分块采集子进程入口。录制配置只在作品 opt-in 时注入全局时间轴与纯模式，未声明时保持既有形状。`src/m2v/engine/remotion/segments.py` 负责 `--jobs` 的分帧区间渲染、逐段验收与无损拼接，不改变单进程路径。
- `src/m2v/types/general/sound_synthesis.py`、`sound_library.py`、`soundtrack.py`：分别负责常见音效目录及确定性拟音、双来源音效登记与离线复核、分镜声音编排；共享 `engine/audio.py` 只处理音频信号与立体声混音，不决定音效选型或许可。
- `src/m2v/core/styles.py`：解释 `styles/<id>/style.json`，负责风格发现、作品兼容校验和内容指纹；不依赖类型实现。general 打包器只消费已校验入口，风格不修改业务流程。
- `src/m2v/engine/`：Remotion 构建、渲染会话、音视频、字幕、缓存、质量检查和输出验收；不应依赖类型私有业务规则。
- `src/m2v/production/`：制作合同、证据依赖、追加式状态、独立评审包及基线保留；制作编排可调用类型采集器，core 不反向依赖该层，渲染不读取制作门作为导出条件。
- `src/m2v/reference/`：外部参考素材获取、页面详情解析、媒体摘要核验与用户授权的音轨提取。
- `src/m2v/cli.py` 与 `src/m2v/commands.py`：统一命令入口及通用命令编排；类型专属命令由类型模块提供。
- `web/src/`：Remotion 合成、通用代码场景运行时、共享动效原语、字体与画幅契约。作品场景代码保存在作品内容目录，不放进共享运行时。`web/src/code-scene/painter/` 是可选的二维 Canvas 绘制层：供需要辉光质感、高密度粒子与线条生长的场景使用，与 R3F 的 `Canvas` 区分，并输出同源的 DOM 量测代理与状态探针，使 Canvas 内容可被检查点量测。生产链路的确定性源码闸门不覆盖该目录，由测试对整目录执行同一检查。

## 契约与文档

- `src/m2v/types/catalog.json` 是类型清单与初始化模板信息的来源；README 和 Skill 中标记的类型清单由同步脚本生成。
- 新增视频类型只在两处落地：先在 `src/m2v/types/catalog.json` 登记类型、材料入口、初始化模板与文案，再实现该类型的适配器。共享入口不按类型名硬编码分发，类型清单由目录生成。类型目录或制作门/审核策略修改后运行 `python .agents/skills/material2video/scripts/sync_docs.py` 重新生成，`--check` 只验证、不写入。
- `web/src/frames.json` 与 `web/src/video-config.json` 分别是画幅/字幕几何和帧率的跨语言来源；Python 经 `core/frames.py`、`core/video_config.py` 读取，制作合同与类型校验复用同一入口。
- `core/source_imports.py` 是字面量引用提取和本地路径解析的公共接口；构建输入与制作证据分别决定遍历范围、摘要和保守绑定策略。
- `production/workflow.py` 定义门、阶段、范围、检查处理器及顺序依赖，`production/policy.py` 定义风险与审核策略；状态计算、CLI、自动检查和文档生成消费这些定义。`production/media_evidence.py` 只核验动态核心过程片段能否解码、视频流时长是否覆盖检查窗，不判断内容，供报告导入与状态查询共用。
- `.agents/skills/material2video/scripts/sync_docs.py` 生成类型清单及检查点文档中的门表、风险表和审核人数表；用 `--check` 验证漂移，生成区不手工维护。同目录的 `guidance_docs.py` 校验阅读路由（`references/guidance-routes.json`）的目标、锚点、触发条件与字符预算，由 `sync_docs.py --check` 一并执行。
- 制作操作顺序只在 [production-workflow.md](.agents/skills/material2video/references/production-workflow.md) 维护，其中「阶段阅读入口」指向四份短阶段指南；日常制作先读当前阶段指南，完整规则仍以本页为准。合同与证据结构在 [checkpoint-gates.md](.agents/skills/material2video/references/checkpoint-gates.md)，评审隔离与执行在 [subagent-review.md](.agents/skills/material2video/references/subagent-review.md)，视觉判断在 [visual-review-rubric.md](.agents/skills/material2video/references/visual-review-rubric.md)，载体选择在 [visual-material-selection.md](.agents/skills/material2video/references/visual-material-selection.md)。其他入口通过链接引用。
- `openspec/specs/` 描述已实现行为，`openspec/changes/` 保存尚在进行的变更。命令和用户流程说明由 README 与 Skill 分别承担入口和操作手册职责。
- `videos/`、`refs/` 及 `styles/<id>/examples/<slug>/` 下的示例媒体是内容或派生产物，不属于共享代码模块；风格包只提供表现层，示例子树不进入包指纹，共享清单和组件不得引用示例；嵌套示例仍按独立作品执行导入边界。具体入库约束见 [AGENTS.md](AGENTS.md)。

## 依赖方向

general 的 `scene_events.py` 维护幕内事件校验和音效定位规则；prepare 解析实际时间后，将事件帧表交给场景配置，将同一份音效起点交给混音并输出事件清单。Web SDK 只查询注入的幕内帧，不反向采集事件或改写音轨。

类型适配器依赖共享 core 与 engine；共享层不反向导入类型实现。Web 渲染层只读取准备阶段提供的契约与输入，不承担 Python 侧材料校验或类型选择。

新增或拆分模块时，优先保持这一依赖方向，并让每项规则只有一个权威来源。
