## MODIFIED Requirements

### Requirement: 当前类型统一制作入口

系统 MUST 在既有正式类型基础上增加 `road-trip`，并通过统一 init、validate、prepare、preview、render 入口处理该类型；通用类型中文名为“通用”，以 storyboard 材料制作 v8 讲解；通用类型辅助操作 MUST 使用 `m2v general`，自驾路线采集 MUST 使用 `m2v driving-route fetch`，普通道路底图采集 MUST 使用 `m2v driving-route basemap`；地图游记采集 MUST 使用 `m2v road-trip fetch`，游记底图采集 MUST 使用 `m2v road-trip basemap`。旧 `article-narrative` 类型与 `m2v article` 命令 MUST 被拒绝。通用作品标准位置 MUST 为 `videos/general/<slug>`，自驾路线作品标准位置 MUST 为 `videos/driving-route/<slug>`，地图游记作品标准位置 MUST 为 `videos/road-trip/<slug>`。

#### Scenario: 查询与初始化类型
- **WHEN** 用户查询类型或初始化通用作品
- **THEN** 类型列表包含金融、通用、自驾路线、地图游记及既有正式类型，通用模板与目录采用 general 身份

#### Scenario: 旧入口被拒绝
- **WHEN** 用户指定 article-narrative 类型或执行 m2v article
- **THEN** 系统报告无效类型或命令，不提供兼容分发

#### Scenario: 已移除住宅类型不可使用
- **WHEN** 请求初始化 housing-timeseries，或对标记为该类型的旧作品执行校验、准备、预演、渲染或评审
- **THEN** 系统明确报未知视频类型，不创建新作品、不生成候选、不执行兼容或迁移

#### Scenario: 独立自驾路线入口
- **WHEN** 初始化 driving-route 或对其执行统一生命周期、m2v driving-route fetch 或 m2v driving-route basemap
- **THEN** 使用独立请求及路线材料，标准作品位置为 videos/driving-route/<slug>，不要求 general storyboard；底图命令只在授权与 mapTiles 落实时取图

#### Scenario: 独立地图游记入口
- **WHEN** 初始化 road-trip，或对其执行统一生命周期、m2v road-trip fetch 或 m2v road-trip basemap
- **THEN** 使用 trip.json 与每日 routes/day-XX.json，标准作品位置为 videos/road-trip/<slug>，不要求 general storyboard；取数与底图命令只在授权与 mapTiles 落实时执行
