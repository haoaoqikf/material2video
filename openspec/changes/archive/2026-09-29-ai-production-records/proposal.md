## Why

制作记录当前只由 CLI 生成空模板，而 Skill 没有要求 AI 助手完成导演规划和评审填写，导致重渲染工作停在模板门禁。自动评审还需要能审计使用了哪些真实画面材料，并在输入或材料变化后失效。

## What Changes

- 规定 AI 助手基于实际联系表、关键幕样片和全片有声评审版填写制作记录。
- 为静态和动态评审记录 AI 来源、会话标识与材料摘要，并将有效来源纳入渲染门禁。
- 更新模板状态、制作 Skill、参考规范和流程示例，保留旧记录读取但不让无来源的旧通过结论满足新门禁。

## Capabilities

### New Capabilities

<!-- None -->

### Modified Capabilities

- `video-production-workflow`: 支持可审计的 AI 制作记录评审，并明确所需视觉材料及通过门禁。

## Impact

- 影响 `scripts/a2v/production.py`、`scripts/production.py`、制作记录模板与相关测试。
- 更新 article2video Skill、视觉评审量表、制作流程示例和 `video-production-workflow` 规格。
- 不新增模型 API、依赖或密钥配置。
