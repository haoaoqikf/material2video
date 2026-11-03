## MODIFIED Requirements

### Requirement: 显式迁移

系统 MUST 校验并完整备份旧作品后迁移；当前 `migrate --from` 只支持金融旧材料契约，与路径迁移 `relocate` 分开，拒绝重复迁移覆盖、未知材料与不支持的旧材料版本。保留历史成片，旧准备和评审不能授权新正式导出。旧制作脚本 MUST 下线。

#### Scenario: 迁移旧作品

- **WHEN** 用户迁移当前金融旧材料作品
- **THEN** 备份原作品并创建类型描述，要求重新准备、预演及评审

### Requirement: 初始化材料立即可用

`m2v init` 为已登记类型生成的材料文件 MUST 是该类型自身契约接受的形式，MUST NOT 出现材料内容被外层文件键或其它包装层级包裹的结构偏差。初始化得到的作品在补齐占位内容之前，校验结果 MUST NOT 包含由结构包裹引起的错误。

#### Scenario: 初始化产物的顶层结构

- **WHEN** 对任一已登记类型执行 `m2v init`
- **THEN** 每个生成的材料文件顶层结构与该类型契约一致，不出现被文件名键包裹的内容（general 的 `storyboard.json` 顶层即 v8 分镜字段）

#### Scenario: 初始化后校验不报结构错误

- **WHEN** 对 `m2v init` 得到的作品执行该类型的材料校验
- **THEN** 校验结果不包含结构包裹导致的错误（general 不再报出「不支持 v8 之前分镜」），只可能报出占位内容待填写的问题

## REMOVED Requirements

### Requirement: 逐作品路径迁移

**Reason**: 与 `article-workspace` 的同名要求重复，且工作区根、内容根与归属推导属于 `article-workspace` 的职责；两份规格各自维护会漂移。

**Migration**: 行为不变。逐作品路径迁移、备份、冲突保留与重试规则以 `article-workspace` 为准；统一入口仍保留 `relocate` 命令。
