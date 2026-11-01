## MODIFIED Requirements

### Requirement: 多日地图游记类型与材料

系统 MUST 登记 `road-trip` 类型，通过统一 init、validate、prepare、preview、render 入口处理作品，首版 MUST 使用 1080×1920 竖屏、30 fps、约 180 秒，其他类型行为保持不变。`road-trip` MUST 属于 `route-journey` 类别，作品标准位置 MUST 为 `videos/route-journey/road-trip/<slug>/`。作品 MUST 只有一份 `trip.json` 编排材料；每日路线 MUST 放在 `routes/day-XX.json`，由 `trip.json` 的 `days[].route` 引用，MUST NOT 进入作品材料清单。材料 MUST 包含起终点、天数、每日目的地与 via、旁白、卡片、音效、事实来源与来源使用依据；MUST NOT 接受手填的总里程、每日时长或起终点坐标，这些 MUST 从路线材料派生。带数值的事实 MUST 同时登记来源标识，没有来源的事实 MUST NOT 进入画面或旁白。旧版本材料 MUST 被明确拒绝，不提供兼容分支。

#### Scenario: 初始化并处理游记作品
- **WHEN** 用户初始化 `road-trip` 作品
- **THEN** 系统写出 `trip.json` 模板，作品标准位置为 `videos/route-journey/road-trip/<slug>`，无需伪装成 general 或 driving-route

#### Scenario: 显式平铺路径被拒绝
- **WHEN** 用户指定 `videos/road-trip/<slug>` 初始化或定位 `road-trip` 作品
- **THEN** 系统拒绝该非规范位置并给出 `videos/route-journey/road-trip/<slug>`；已有作品可用 `m2v relocate` 迁移

#### Scenario: 手填派生字段
- **WHEN** `trip.json` 声明总里程、每日时长或起终点坐标
- **THEN** 校验失败并指出该字段必须由每日路线派生

#### Scenario: 无来源事实
- **WHEN** 卡片事实带 `value` 但缺少 `sourceId`
- **THEN** 校验失败并指出具体事实

#### Scenario: 不支持的材料版本
- **WHEN** `trip.json` 或任一日 `route.json` 的 `schemaVersion` 不受支持
- **THEN** 系统在准备前明确拒绝并指出版本
