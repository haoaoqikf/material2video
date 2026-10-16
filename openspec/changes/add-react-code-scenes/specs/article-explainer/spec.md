## RENAMED Requirements
- FROM: `v6 混合媒体分镜`
- TO: `v7 混合媒体分镜`

## MODIFIED Requirements

### Requirement: v7 混合媒体分镜
系统 MUST 只接受 version/schemaVersion 为 7 的通用分镜，固定 1080×1920、30 fps。每幕 MUST 声明唯一 ID、六种原有模板或 code 模板、独立屏幕内容及旁白分段；code、图片和视频 MAY 无旁白。原有展示绑定、原文审查、主题关键词、真实语音时间与完整预演门禁 MUST 保留。code MUST 声明 content.title、content.entry 和可选 JSON 对象 content.props。旧分镜及准备 MUST 拒绝，不自动迁移。

#### Scenario: 旧分镜
- **WHEN** 输入 v6 或更早分镜
- **THEN** 明确要求重新编排 v7

#### Scenario: 代码模板
- **WHEN** 输入有效 code 幕
- **THEN** 以本地录制片段参与现有转场、字幕及音轨合成

### Requirement: 讲解评审及版本绑定
系统 MUST 对原文输入保留输入人工语义审查及当前指纹的完整有声预演，MUST NOT 以人工画面评审阻断导出；人工画面评审 SHALL 为可选工具；评审检查信息清晰、布局、图文关系、同步与阅读停留。源文、分镜、素材、导入记录、代码场景源码或资源、音轨或渲染实现变化 MUST 使旧准备或评审失效。正式输出 MUST 验收后替换并保存溯源。系统 MUST 拒绝旧通用类型的完整片段嵌入。

#### Scenario: 输入未评审
- **WHEN** 当前源文没有通过人工语义审查
- **THEN** 准备拒绝并要求完成审查

#### Scenario: 材料变化
- **WHEN** 当前素材内容或导入记录在准备后改变
- **THEN** 旧准备和评审不能用于正式制作

#### Scenario: 完整嵌入
- **WHEN** 用户尝试引用完整作品作为通用场景
- **THEN** 系统拒绝旧片段嵌入材料，要求以 v7 模板重新编排

#### Scenario: 自动预演门禁
- **WHEN** 完整预演缺失、限帧、指纹过期、文件摘要或完整帧数不匹配
- **THEN** 正式导出被拒绝，不覆盖先前有效成片
