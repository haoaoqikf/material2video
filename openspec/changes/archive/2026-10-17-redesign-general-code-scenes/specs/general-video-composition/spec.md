## RENAMED Requirements

- FROM: `### Requirement: 通用类型使用 v7 混合媒体讲解`
- TO: `### Requirement: 通用类型使用 v8 自由代码场景`

## MODIFIED Requirements

### Requirement: 通用类型使用 v8 自由代码场景
系统 MUST 以 general 接受 v8 storyboard.json，支持 article/topic 输入且只接受本地 code 场景；MUST 保留真实配音、烧录字幕、媒体导入留证、音效音床、完整预演自动验收及 600 秒限制。代码场景 MUST 在准备阶段录制为标准化无声片段并绑定输入摘要，预演和正式导出 MUST 复用相同片段，不在导出执行作品代码。初始化 MUST 显式生成 1920×1080、30 fps 材料及可运行本地场景。系统 MUST 拒绝旧分镜、general-plan、六种旧模板、visual.theme 和完整片段嵌入，不提供迁移工具。

#### Scenario: 初始化与制作通用作品
- **WHEN** 初始化 general 作品
- **THEN** 生成有效横屏 v8 分镜及本地代码入口，可进入统一制作链路

#### Scenario: 拒绝旧通用材料
- **WHEN** 提交 v7、旧模板、主题字段或完整作品嵌入
- **THEN** 制作前明确拒绝并要求按 v8 重新编排
