## Context

动机见 [proposal.md](proposal.md)。当前 `frames.spec()` 生成完整字幕样式，general prepare 将其同时传入 `props.subtitle` 与 `inputs.subtitle`。合成层直接读取传入样式，布局量测的边界却单独从画幅清单解析。作品描述本身已参与 `materialFingerprint`，因此无需另建配置指纹或迁移层。

## Goals / Non-Goals

**Goals:** 在保持其他作品现有画面不变的前提下，让单个 general 作品通过一个严格校验的字号字段改善字幕可读性，并使准备、画面和量测一致。

**Non-Goals:** 不开放安全区、颜色、行高和字幕开关；不改变其他类型；不引入动态适配字号或自动缩字；不手工改准备产物。

## Decisions

1. 使用底层窄函数校验作品的 `output.subtitle`，由作品加载和 general 直接校验/准备路径复用。禁止空对象、未知子字段、布尔、浮点、null 及范围外值，避免直接调用适配器绕过边界。其他类型即使声明 null 也拒绝。
2. 在现有 `frames.spec()` 结果上只覆盖经校验的 `fontSize`，保持画幅清单为默认样式真源。复用当前 `SubtitleStyle` 和 composition，不新增组件或依赖；已有实现满足确定性与许可要求，无需外部替代方案。
3. prepare 只解析一次样式，继续把同一结果写入 `props.subtitle` 与 `inputs.subtitle`。布局量测从准备样式注入安全区与期望字号，并校验实际 DOM 字号；预演、正式输出与 QA 沿用 prepared，不重新推断。保留 `measure_script` 的默认调用能力供现有直接调用者使用。
4. 配置变化沿用整个 project 的准备指纹绑定；现有实现摘要变化也使旧 prepared 一次失效。不提供迁移，重新 prepare。

## Risks / Trade-offs

- 字号增大可能造成换行或超出固定安全区 → 保留实际浏览器溢出量测，作者调整文本；不自动修改安全区。
- 未声明的作品必须保持 40px → 两画幅默认测试和现有清单测试保护。
- 静态前端测试无法证明真实布局 → 以定向浏览器节点验证 52px 的计算样式、布局及字号不符拒绝。

## Migration Plan

先实施配置和量测链路，运行定向验证，再让作品设置 `fontSize: 52` 并重新准备。无需变更项目 schemaVersion；旧作品可省略该字段保持原行为。
