# motion-design Specification

## Purpose

把上游 `motion-design` 作为项目级运动设计知识来源：固定上游版本，保留原文，用视频适配层把毫秒时长、UI 交互章节和动画库建议转译为帧驱动语境的时长、缓动、编排与采集模式边界。它提供设计方法与观察清单，不新增门禁、评分或审核轮次。

## Requirements

### Requirement: 运动知识必须以项目级 skill 提供

项目 SHALL 在 `.agents/skills/motion-design/` 提供运动设计 skill，固定上游仓库与提交，并在仓库内保存 MIT 许可证与 `UPSTREAM.md`。上游正文 SHALL 原样保留、不翻译；项目差异 SHALL 记录在 `UPSTREAM.md`。

`SKILL.md` frontmatter 的 `description` SHALL 指向镜头运动、转场、入场退场和帧驱动动效；文件顶部 SHALL 指向中文 `ADAPTATION.md`。`ADAPTATION.md` SHALL 把上游的毫秒时长、UI 交互章节和动画库建议转译为视频语境。

#### Scenario: 上游内容可追溯
- **WHEN** 维护者检查运动 skill
- **THEN** 能从 `UPSTREAM.md` 找到上游仓库、固定提交、访问日期、许可证和本地改动清单

#### Scenario: UI 交互动效不误用
- **WHEN** 制作助手读取运动 skill
- **THEN** 能从 `ADAPTATION.md` 识别 hover、press、tap、`prefers-reduced-motion` 和布局抖动等不适用的 UI 规则

### Requirement: 时长与缓动必须按帧驱动语境转译

运动 skill 的毫秒时长表 SHALL 只作为起点；制作助手 MUST 按作品实际帧率换算为帧，并按镜头、对象尺度和叙事节拍重新确定。`ADAPTATION.md` SHALL 给出视频节拍参考：微反馈、标准动作、镜头动作、观察停留和持续环境运动各自的秒/帧量级，MUST NOT 写成所有作品通用的固定阈值。

缓动 SHALL 使用共享命名曲线，方向遵循入场减速、离场加速、画面内平滑和匀速跟踪例外。空间运动 MUST NOT 缺省使用线性；`linear` 仅允许显式用于匀速跟踪、进度或旋转，并 SHALL 在场景或设计中说明用途。

#### Scenario: 毫秒表换算
- **WHEN** 制作助手为 30 fps 或 60 fps 作品设计一个入场动作
- **THEN** 先把起点时长换算为帧，再按对象尺度和镜头节拍调整，不直接照搬 UI 毫秒值

#### Scenario: 匀速跟踪
- **WHEN** 镜头需要恒定速度跟随移动主体
- **THEN** 可以显式使用 `linear`，并在设计或场景中说明这是匀速跟踪例外

### Requirement: 运动编排默认不是硬门禁

运动 skill 的三支柱、运动人格、迪士尼原则、错峰和 1/3 规则 SHALL 作为设计与观察默认。`ADAPTATION.md` MUST 明确：

- 三层运动（primary/secondary/ambient）是诊断，不是每镜必备；环境层只在承担表达时使用；
- 1/3 规则、错峰预算和上游危险等级 MUST NOT 变成自动审美门禁或新审核轮次；
- 风格包的运动人格映射只作方案起点，作品仍按实际表达调整。

#### Scenario: 静止镜头
- **WHEN** 一个镜头按表达需要保持静止
- **THEN** 不因缺少次级或环境运动判为失败，也不强行添加装饰动效

#### Scenario: 错峰超预算
- **WHEN** 一次多元素入场总错峰超过上游参考预算
- **THEN** 助手记录实际节拍与表达需要并决定是否调整，不以机器阈值否决

### Requirement: 采集模式决定可用实现

`sequential` 采集 SHALL 允许在受控时钟下使用 Motion、GSAP、CSS 动画和 R3F 逐帧回调；`pure-time` 与 `--jobs` 并行渲染 MUST 只接受由帧号、`elapsedSeconds`、`globalSeconds`、`props` 和事件帧推导的纯函数。运动 skill 的动画库建议 MUST NOT 覆盖这一边界。

#### Scenario: 纯时间场景
- **WHEN** 作品声明 `capture.mode: "pure-time"`
- **THEN** 场景不得导入 `useFrame`、CSS 动画或依赖动画库回调的实现，动效只由帧函数求值

#### Scenario: 顺序采集
- **WHEN** 作品保持默认 `sequential` 采集
- **THEN** 可以在受控时钟下使用现有动画库，但仍须通过确定性源码闸门与成片验收

### Requirement: 项目指导不得复述运动设计知识

项目文档 MUST NOT 维护与 `motion-design` 重复的通用运动理论、时长表、缓动表、编排配方或质量检查清单。项目文档 SHALL 只记录：

- 帧驱动、纯时间采集、并行渲染、相机与场景 API 等技术边界；
- 本项目的镜头行为、转场契约与叙事节奏要求；
- 证据、问题分级、审核与完成条件。

通用运动判断 SHALL 链接到本 skill 及其 `ADAPTATION.md`。项目文档可以记录作品采用的运动人格、签名动作和时长起点，但 MUST NOT 把 skill 的方法改写成另一套项目规则。

#### Scenario: 项目文档需要运动判断
- **WHEN** 流程、阶段或评审文档需要描述启动、移动、减速、停留、缓动或编排
- **THEN** 使用链接与项目验收条件，不复制 skill 的通用理论

#### Scenario: 记录作品运动计划
- **WHEN** 作品在 `DESIGN.md` 记录运动计划
- **THEN** 记录人格、签名动作、层选择与时长/缓动起点，并保留项目帧驱动边界
