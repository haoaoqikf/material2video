## MODIFIED Requirements

### Requirement: 统一作品及制作入口

系统 MUST 支持统一的 types/init/validate/prepare/preview/review-template/review/status/render/migrate/relocate 入口。`m2v init` MUST 将作品初始化到 `videos/<type>/<slug>/`；生命周期命令仍接收作品目录。作品相对材料以作品根解析，类型材料独立。退出码 MUST 区分成功0、执行或门禁失败1、材料或参数错误2。仓库示例产物 MUST 位于 `videos/examples/<slug>/outputs/`，不得写入版本化的示例源目录。路径迁移子命令 MUST 与 `--from` 材料格式迁移区分。

#### Scenario: 材料归属与未知类型
- **WHEN** 在不同工作目录操作作品或传入未知类型/版本
- **THEN** 已知作品归属稳定，未知类型或版本在渲染前失败

#### Scenario: 按类型初始化作品
- **WHEN** 在工作区根对某个已登记类型执行 `m2v init --type general --project <slug>`
- **THEN** 作品和初始化材料创建在 `videos/general/<slug>/`

#### Scenario: 迁移统一契约作品路径
- **WHEN** 用户对 `videos/<slug>/` 下的作品执行路径迁移
- **THEN** 作品移动至 `videos/<project.type>/<slug>/`，完整备份旧目录，并保留其全部产物

#### Scenario: 仓库自带示例走统一入口
- **WHEN** 用统一入口对仓库 `examples/<slug>/` 下的示例作品执行 prepare、preview 或 render
- **THEN** 产物位于 `videos/examples/<slug>/outputs/` 且与作品类型分层目录规则兼容

#### Scenario: 既有示例运行产物
- **WHEN** 对 `examples/<slug>/` 中的示例作品执行生命周期命令
- **THEN** 产物位于 `videos/examples/<slug>/outputs/` 且与作品类型分层目录规则兼容
