## Purpose

建立面向多种专用及通用视频的作品与制作契约，使用户通过统一入口准备、预演、评审和导出，并能够显式迁移已有作品且复核内容与渲染依据。

## ADDED Requirements

### Requirement: 统一作品及制作入口
系统 MUST 支持 project.json v1 和 a2v types/init/validate/prepare/preview/review-template/review/status/render/migrate；作品相对材料以作品根解析，类型材料独立。退出码 MUST 区分成功0、执行或门禁失败1、材料或参数错误2。

#### Scenario: 材料归属与未知类型
- **WHEN** 在不同工作目录操作作品或传入未知类型/版本
- **THEN** 已知作品归属稳定，未知类型或版本在渲染前失败

### Requirement: 准备及评审版本绑定
系统 MUST 在准备后记录输入、资产、源码与准备指纹。render MUST 只读当前准备产物，缺少或过期时要求重新 prepare。正式导出 MUST 要求绑定完整预演及证据来源的当前评审，并执行类型门禁；未填写评审 MUST 保持 pending。

具有专用评审要求的视频类型 MUST 可通过注册接口生成类型评审模板；统一 `review-template` MUST 同时创建通用评审记录和类型专用评审材料，统一 `review` 与正式 `render` MUST 同时验证两者。

#### Scenario: 材料变化
- **WHEN** 准备或评审后修改数据、源码、字体、声音或预演
- **THEN** 对应记录失效，正式导出阻断

#### Scenario: 类型专用评审
- **WHEN** 金融或文章作品使用统一评审入口
- **THEN** 模板包含类型专用评审，评审或导出在任一所需门禁缺失、待审或过期时失败

### Requirement: 共用渲染及可靠输出
系统 MUST 使用完整缓存键且命中不跳门禁，元数据核验与渲染使用同一浏览器会话；临时成片通过帧数、尺寸、帧率、音轨验收及输入复核后才替换目标。所有类型 MUST 输出溯源与性能记录。

#### Scenario: 元数据不符或输出失败
- **WHEN** composition 元数据不符或渲染期间材料变化
- **THEN** 阻断或丢弃临时产物，不覆盖原有效成片

### Requirement: 显式迁移
系统 MUST 校验并完整备份旧作品后迁移，拒绝重复迁移覆盖、未知材料、文章v1-v3；保留历史成片，旧准备和评审不能授权新正式导出。旧制作脚本 MUST 下线。

#### Scenario: 迁移旧作品
- **WHEN** 用户迁移文章v4或当前金融作品
- **THEN** 备份原作品并创建类型描述，要求重新准备、预演及评审
