# 架构与模块职责

Material2Video 提供制作指导、工程生成和可选制作管理。v3 作品拥有自己的 Python 准备／音频／采集实现和 Web 场景，Remotion 的本地 `SceneFilm` composition 合成片段、转场和字幕。五类共用生成基础，类型决定默认目录与制作指南，不强制额外组件或依赖。

## 代码分层

| 层 | 位置 | 职责 |
|---|---|---|
| 管理契约 | `src/m2v/core/`、`type_system/` | project v3、五类目录、实际输入／媒体复核与安全边界 |
| 工程生成与委托 | `src/m2v/standalone/` | 创建时复制完整模板；以作品环境执行本地协议，收回取消或超时的进程树 |
| 独立基础模板 | `templates/standalone/` | 本地运行源码、精确依赖及锁、字体恢复、逐帧宿主和成片合成；生成后不再读取模板 |
| 制作管理 | `src/m2v/types/scene_film/`、`engine/`、`production/` | 分镜 v9 校验、作品本地执行协议、lookdev／时间线委托、QA、评审、问题与制作证据 |
| 结构化来源 | `src/m2v/types/financial/`、`building_construction/`、`vehicle_showcase/` | 金融行情与投资计算、建筑构件与步骤、汽车模型与镜头数据；只由统一分镜引用 |
| Web 参考源码 | `web/src/code-scene/`、`web/src/scene-film/`、`web/src/types/` | 可选组件的采用参考与仓库测试夹具；不是作品运行时，也没有公开 SDK 入口 |
| 作品 | `videos/<type>/<slug>/`、`examples/<type>/<slug>/` | 分镜、源文、场景代码与素材；只有五部示例源码入库 |

## 依赖与材料边界

`src/m2v/type_system/catalog.json` 是五类名称、说明和初始化分镜的单一来源；没有类别或风格注册。`registry.py` 把五类接到本地委托适配器。`project.json` 只接受 v3、五类 `type` 和 `materials.storyboard`；`runtime` 是接入 m2v 的可选本地命令数组，作品直接运行无需该管理协议。准备记录绑定作品本地源码、依赖锁、字体、媒体和实际构建输入；主项目包或参考组件的更新不进入作品媒体身份。旧执行契约明确拒绝。

新工程场景只从作品自身目录与本地声明的精确第三方依赖导入；本地构建器拒绝 `m2v/*`、越界链接、父工程依赖兜底和机器绝对路径。模板的本地字体登记与恢复随工程生成，字体二进制不入库。`src/m2v/production/dependencies.py` 只绑定作品可达源码、资源和本地控制实现；动态引用保守扩大作品内范围，目录联接不能扩大到作品外。存量 `web/` 组件保留为可复制采用的参考源码和测试夹具；其公开 SDK 总入口、全局依赖登记与仓库场景构建映射已移除，作品构建器拒绝 `m2v/*`。旧 Python 准备／渲染模块只作为模板提取依据和测试对象，不再被任何生产命令调用。

`engine/` 负责通用媒体、QA 和本地工具委托；`production/` 负责媒体绑定评审、状态、问题与基线；`reference/` 负责参考素材。类型来源只提供经验证的数据，不反向改变共享制作流程。纯时间采集与多进程分段渲染在作品本地运行时执行；主项目的 lookdev 与时间线通过本地协议读取本地产物。

## 原生设计样品

`engine/design_sample.py` 委托作品本地sample并独立复核包的位置、来源、实际参数、媒体及技术信号；源码可达性、project／props初始摘要、字体与登记媒体由工具在执行前后重新核对。实际构建、受控采集、编码和HTML播放器属于作品的本地运行时，主项目不再分发另一份样品播放器。`production/samples.py` 将成功采集与当前周期事件绑定，基于既有 review 包和独立报告执行交付检查；不建立第二套评审格式或自动审美算法。`sample_cli.py` 只负责参数、作品写锁、操作内指纹缓存和本地服务生命周期。

网页预览仅暴露该次bundle、受控时钟、本作品登记媒体和字体，控制条不进入采集；来源、可达集合或执行配置变化后样品失效。作品本地依赖锁与加载器进入样品输入。内部样品沿用高色度精度的yuv444p片段；正式成片仍执行yuv420p交付格式检查，二者都完整解码并核对帧数、画幅、帧率及时间。失败试制可以保留，只有交付检查通过才复制已评静帧与视频，不重新渲染。完整工作流见[网页原生样品](.agents/skills/material2video/references/design-samples.md)。

## 分层设计材料

`RESEARCH.md` 保存研究；`DESIGN.md` 保存全片目标、原始要求、采用范围、五维共同语言及索引；`design/scenes/<scene-id>.md` 保存详细编排与实际依据。分镜关联代码入口并维护正式执行参数，设计文档当前不渲染，不进入准备指纹。离线技能脚本只检查 ID、索引和链接，不判断审美或制作完成；流程与模板见[场景设计](.agents/skills/material2video/references/scene-design.md)。

## 契约与文档

- [README](README.md)：当前能力、命令和示例入口。
- [项目规划](docs/PROJECT_PLAN.md)：未来路线；不把规划写成已实现能力。
- [制作 Skill](.agents/skills/material2video/SKILL.md)：操作顺序、分镜、素材、声音和评审规则。
- [OpenSpec 规格](openspec/specs/)：可验证的已实现行为。
- [AGENTS.md](AGENTS.md)：Git、测试与协作约定。

类型清单与评审包示例由 `.agents/skills/material2video/scripts/sync_docs.py` 生成；`--check` 检测漂移。代码开发只跑受影响的 Python/Web 测试与必要的真实媒体节点，全量回归遵守 AGENTS.md 的触发规则。
