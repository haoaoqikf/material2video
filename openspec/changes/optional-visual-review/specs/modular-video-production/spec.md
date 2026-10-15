## MODIFIED Requirements

### Requirement: 准备及评审版本绑定
系统 MUST 在准备后记录输入、资产、源码与准备指纹。render MUST 只读当前准备产物，缺少或过期时要求重新 prepare。正式导出 MUST 验证当前完整预演的准备指纹、文件摘要、完整帧数及媒体技术参数，并执行类型自动门禁；MUST NOT 要求人工画面评审。人工评审工具 SHALL 保留为可选工具，status MUST 标识 required=false，未填写时标识 optional；主动 review 时 MUST 验证当前结论、完整非空依据及预演绑定。

具有专用评审要求的视频类型 MUST 可通过注册接口生成类型评审模板；统一 `review-template` MUST 同时创建通用评审记录和类型专用评审材料，主动执行统一 `review` MUST 验证两者；正式 `render` MUST 只验证自动门禁。

#### Scenario: 材料变化
- **WHEN** 准备或评审后修改数据、源码、字体、声音或预演
- **THEN** 对应记录失效，正式导出阻断

#### Scenario: 类型专用评审
- **WHEN** 金融或文章作品使用统一评审入口
- **THEN** 有人工评审工具的类型可按需生成模板，主动评审在依据缺失或过期时失败，正式导出不受人工记录影响；金融继续只做自动验收


#### Scenario: 自动预演门禁
- **WHEN** 完整预演缺失、限帧、指纹过期、文件摘要或完整帧数不匹配
- **THEN** 正式导出被拒绝，不覆盖先前有效成片
