# 架构与模块职责

Material2Video 以 Python 负责材料校验、准备、音频、证据与命令编排；Web 代码场景逐帧绘制画面，Remotion 的唯一 `SceneFilm` composition 负责片段、转场和共享字幕合成。五类视频共用这一链路。视频类型决定作品归属与可用的结构化来源，不决定第二套渲染管线。

## 代码分层

| 层 | 位置 | 职责 |
|---|---|---|
| 共享契约 | `src/m2v/core/`、`type_system/` | project v2、五类目录、路径、帧率、字体、指纹与安全边界 |
| 统一制作 | `src/m2v/types/scene_film/`、`engine/`、`production/` | 分镜 v9、代码场景准备与采集、混音、预演、渲染、QA 和制作证据 |
| 结构化来源 | `src/m2v/types/financial/`、`building_construction/`、`vehicle_showcase/` | 金融行情与投资计算、建筑构件与步骤、汽车模型与镜头数据；只由统一分镜引用 |
| Web 场景 | `web/src/code-scene/`、`web/src/scene-film/`、`web/src/types/` | 共享 SDK、来源绘制组件与单一 composition；专用 Web 组件不注册独立成片 |
| 作品 | `videos/<type>/<slug>/`、`examples/<type>/<slug>/` | 分镜、源文、场景代码与素材；只有七部示例源码入库 |

## 依赖与材料边界

`src/m2v/type_system/catalog.json` 是五类名称、说明和初始化模板的单一来源；没有类别或风格注册。`registry.py` 把五类接到同一适配器。`project.json` 只接受 v2、五类 `type` 和 `materials.storyboard`。`scene_film/explainer.py` 校验 v9 分镜；`sources.py` 校验来源种类、作品内文件、场景引用并调用既有金融、建筑与汽车计算。准备结果经 `code_scenes/config.py` 注入场景，来源文件及实现共同进入指纹。旧材料、准备记录及 `m2v/style` 导入明确拒绝。

作品场景只可从自身目录、`m2v/code-scene` 和登记的依赖导入。`web/scripts/build-code-scene.mjs` 读取 `web/code-scene-dependencies.json` 校验作品直接依赖的精确安装版本和导入边界；`src/m2v/production/dependencies.py` 为证据绑定相同的本地依赖。跨作品复用的数值滚动、图表与轨道在 `web/src/code-scene/motion-components/`；各示例只保留自身需要的组件与视觉参数。基础 CSS 在 `web/src/styles/`；字体来源、摘要、许可和恢复目标在 `fonts/registry.json`，字体二进制不入库。

`engine/` 负责通用媒体、渲染、音频与 QA；`production/` 负责媒体绑定评审、状态、问题与基线；`reference/` 负责参考素材。类型来源只提供经验证的数据，不反向改变共享制作流程。纯时间采集与多进程分段渲染沿统一代码场景实现。

## 原生设计样品

`engine/design_sample.py` 复用正式场景构建、配置、受控采集与编码，输出同源网页、静帧、完整局部视频及实际输入摘要；HTML 模板作为包资源分发。`production/samples.py` 将成功采集与当前周期事件绑定，复核来源/产物摘要，基于既有 review 包和独立报告执行交付检查；不建立第二套评审格式或自动审美算法。`sample_cli.py` 只负责参数、作品写锁、操作内指纹缓存和本地服务生命周期。

网页预览仅暴露该次 bundle、受控时钟、登记媒体和字体，控制条不进入采集；来源变化后样品失效。依赖登记与加载器进入准备、样品与评审指纹。失败试制可以保留，只有交付检查通过才复制已评静帧与视频，不重新渲染。完整工作流见[网页原生样品](.agents/skills/material2video/references/design-samples.md)。

## 分层设计材料

`RESEARCH.md` 保存研究；`DESIGN.md` 保存全片目标、原始要求、采用范围、五维共同语言及索引；`design/scenes/<scene-id>.md` 保存详细编排与实际依据。分镜关联代码入口并维护正式执行参数，设计文档当前不渲染，不进入准备指纹。离线技能脚本只检查 ID、索引和链接，不判断审美或制作完成；流程与模板见[场景设计](.agents/skills/material2video/references/scene-design.md)。

## 契约与文档

- [README](README.md)：当前能力、命令和示例入口。
- [项目规划](docs/PROJECT_PLAN.md)：未来路线；不把规划写成已实现能力。
- [制作 Skill](.agents/skills/material2video/SKILL.md)：操作顺序、分镜、素材、声音和评审规则。
- [OpenSpec 规格](openspec/specs/)：可验证的已实现行为。
- [AGENTS.md](AGENTS.md)：Git、测试与协作约定。

类型清单与评审包示例由 `.agents/skills/material2video/scripts/sync_docs.py` 生成；`--check` 检测漂移。代码开发只跑受影响的 Python/Web 测试与必要的真实媒体节点，全量回归遵守 AGENTS.md 的触发规则。
