## MODIFIED Requirements

### Requirement: 统一作品及制作入口
系统 MUST 支持 project.json v1 和 m2v types/init/validate/prepare/preview/review-template/review/status/render/migrate；作品相对材料以作品根解析，类型材料独立。退出码 MUST 区分成功0、执行或门禁失败1、材料或参数错误2。

#### Scenario: 材料归属与未知类型
- **WHEN** 在不同工作目录操作作品或传入未知类型/版本
- **THEN** 已知作品归属稳定，未知类型或版本在渲染前失败

#### Scenario: 仓库自带示例走统一入口
- **WHEN** 用统一入口对仓库 `examples/<slug>/` 下的示例作品执行 prepare、preview 或 render
- **THEN** 媒体、预演与成片写入 `videos/examples/<slug>/outputs/`，
  不写进受版本控制的 `examples/<slug>/` 目录
