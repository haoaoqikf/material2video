## Why

项目已定位为“一个观点，一个场景，一段动态叙事”，但现有 v3 仍按独立幕组织 renderer、镜头与转场，视觉模式数量和同构布局检查也可能误伤持续隐喻。需要将持续视觉世界、全局状态推进和连续性验收落实为唯一制作方式。

## What Changes

- **BREAKING**：分镜升级为 v4，以 stages[] 替代 scenes[]；所有执行入口拒绝 v1–v3，无兼容开关或自动迁移。
- 全片只声明一个持续场景与一个 renderer，保留场景树和代码双轨，统一全局对象、状态、beat 与镜头时间轴。
- **BREAKING**：媒体清单升级为 version 4，阶段实际时长驱动动作、字幕、镜头与声音边界；旧清单需要重新 prepare。
- 创作流程改为核心观点、核心隐喻、持续对象与关系、状态演进、叙事阶段及动作编排。
- 调整视觉预算和复用检查，新增连续性动态评审及正式渲染门禁。
- 新增飞镖标杆，逐一改编现有八个示例，同步 Skill 参考文档、校验器及当前状态说明。

## Capabilities

### New Capabilities

- `single-scene-narrative`：全片持续视觉世界、全局对象状态轨道、双轨 renderer、连续性验收及标杆。

### Modified Capabilities

- `storyboard-v3-contract`：将原有入口契约替换为 v4，全片画面与阶段职责分离。
- `declarative-video-scenes`：画面模式和场景树提升到全片级。
- `code-driven-scenes`：作品模块接收全片时间轴和全局状态，移除幕级切换与连续性接口。
- `semantic-motion-timeline`：阶段口播解析为全局 beat 时间轴，跨阶段状态直接求值。
- `cinematic-directing`：全片镜头替代逐幕镜头和跨幕视觉转场。
- `article-to-storyboard`：生成持续场景，改写拆幕规则和视觉模式数量预算。
- `visual-direction-pipeline`：视觉策略、视觉意图和复用检查适配持续世界。
- `storyboard-aesthetic-review`：加入连续性评审及阻断条件。
- `video-production-workflow`：制作记录与材料指纹纳入连续性评审。

## Impact

影响 Python 校验、媒体准备、预览、评审、制作记录与渲染编排，以及 web schema、composition、场景树、代码模块接口、对象状态、镜头和契约探针。公共分镜与媒体格式均有破坏性变化。

保留现有依赖栈、原语注册表、安全隔离、画布与主题、字幕与混音、输出路径及溯源能力。仓库外作品不自动改写；旧输入给出重新编排或 prepare 的明确诊断。实施时更新上述主规格与相关引用，历史归档记录不改写。本提案不包括模型服务、自动选曲或平台发布。
