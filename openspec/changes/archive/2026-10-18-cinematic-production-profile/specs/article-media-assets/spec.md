## ADDED Requirements

### Requirement: 电影级资产质量与许可审计

系统 MUST 提供资产质量审计，按镜头计算屏幕像素与纹理像素的比例，并检查 hero 资产的最低分辨率、normal/roughness/emissive 等辅助贴图、土星环等径向纹理的实际径向分辨率、色彩空间、alpha 与登记许可。审计结果 MUST 写入作品 `outputs/` 下的单独报告并绑定准备指纹；技术审计 MUST NOT 修改或重新编码原始素材。

cinematic 作品的 hero 资产 MUST 满足：颜色贴图 ≥ 4K（或屏幕像素/纹素比达到项目阈值）、岩质天体具备 normal map、气态行星具备可选的 flow/normal、土星环径向纹理 ≥ 4K×512、素材色彩空间与材质设置一致。hero 资产许可未知或为「未知」时 MUST 阻断；standard 资产许可未知时 MAY 保留现有「未知」记录并继续，但 MUST NOT 在片尾虚构署名。

系统 MUST 提供 `m2v assets audit --project <目录>`；命令 MUST 只读素材与导入记录，输出可定位到素材 ID 与镜头的报告，失败退出码与现有校验一致。素材、镜头或 look 变化 MUST 使审计报告过期。

#### Scenario: Hero 贴图不足
- **WHEN** cinematic 作品的地球 hero 使用 2K 颜色贴图且屏幕占比超过阈值
- **THEN** 审计报告标为不合格并阻断 cinematic 导出，指出素材 ID 与镜头

#### Scenario: 许可未知
- **WHEN** hero 纹理的许可记录为“未知”
- **THEN** cinematic 导出被阻断，要求补充来源与许可；standard 作品保留记录但不虚构署名

#### Scenario: 辅助贴图缺失
- **WHEN** 岩质 hero 天体只有颜色贴图，没有 normal map
- **THEN** 审计报告标为缺口并给出建议，不静默把颜色图当凹凸使用

#### Scenario: 标准档不增加门禁
- **WHEN** standard 作品未运行资产审计
- **THEN** 现有准备、预演与导出行为不变
