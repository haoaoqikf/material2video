# 分镜 v3 契约

## Purpose

定义唯一可执行的分镜 v3 契约，使校验、预览、评审、媒体准备与渲染对导演结构、语义节拍时间轴和失败条件保持一致。

## ADDED Requirements

### Requirement: 所有分镜执行入口仅接受完整 v3 契约
分镜校验、预览、评审、配音准备及渲染 SHALL 只接受 `version: 3` 和 `schemaVersion: 3`。输入版本缺失或小于 3 时 SHALL 在处理前失败，并明确报告“不支持 v3 之前分镜”。根对象 SHALL 要求 `directingVersion: 1`、完整 `directingBrief`、完整 `visualDirection` 及 `visual.preset: "keynote"`。系统 SHALL 不提供迁移命令、legacy 开关或运行时回退。

#### Scenario: 输入 v1 或 v2 分镜
- **WHEN** 任一分镜执行入口读取 v1/v2 或缺失版本的分镜
- **THEN** 入口给出不支持 v3 之前分镜的明确错误，并且不预览、不评审、不准备媒体、不渲染

#### Scenario: 缺少导演策略
- **WHEN** v3 分镜缺少 directingBrief、visualDirection 或 keynote preset
- **THEN** 严格 schema 校验按字段定位拒绝该输入

### Requirement: 每幕明确声明画面、意图和镜头
每幕 SHALL 显式提供 renderer、完整视觉论证字段以及非空 camera.segments。第二幕及之后 SHALL 显式提供有效 transition。camera SHALL 不接受单一 movement 回退。

#### Scenario: 缺 renderer 或镜头段
- **WHEN** v3 场景未声明 renderer 或 camera.segments
- **THEN** 校验失败并指出缺失字段，不采用默认 renderer 或默认镜头计划

#### Scenario: 缺少跨幕关系
- **WHEN** 第 2 幕及之后没有显式 transition
- **THEN** 校验失败并指出缺失的跨幕关系

### Requirement: 口播与画面共用语义 beat 时间轴
有口播的场景 SHALL 使用 `narrationSegments` 并由 `beats` 完整绑定；场景 SHALL NOT 使用字符串 `narration`。镜头段和动作 SHALL 通过 beatId 或 phase 关联由准备阶段确定的同一 beat 时间轴。场景末尾 SHALL 保留至少 12 帧稳定阅读区。motion SHALL NOT 接受 startFrame；一条 motion SHALL 绑定 phase 或 beatId；多目标 motion SHALL 使用 targets 和 stagger。

#### Scenario: 使用旧式口播或绝对帧动效
- **WHEN** 场景包含 narration 字符串、未绑定的 motion 或 startFrame
- **THEN** schema 拒绝场景，并指出应使用 narrationSegments、beats、phase/beatId 及分组错峰字段

#### Scenario: 镜头、动作和字幕使用共同时间轴
- **WHEN** 有口播的 beat 解析为确定帧区间
- **THEN** 镜头、动作和字幕的变化边界均引用该区间，并在末尾保留稳定阅读时间

### Requirement: 历史成片溯源不构成分镜兼容
系统 MAY 只读识别历史媒体清单，以报告来源无法验证或需要重渲染；该识别 SHALL NOT 把旧分镜交给导演、画面或评审运行时。

#### Scenario: 读取历史媒体溯源
- **WHEN** 旧成片对应旧格式的只读 manifest
- **THEN** 系统仅报告无法验证或需重渲染，不据此执行旧分镜
