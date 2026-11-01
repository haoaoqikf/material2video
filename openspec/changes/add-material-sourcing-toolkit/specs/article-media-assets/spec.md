## MODIFIED Requirements

### Requirement: 电影级资产质量与许可审计

系统 MUST 对全部登记媒体检查文件、原生尺寸、色彩空间、alpha与许可，许可未知 MUST 阻断准备与审计。报告 MUST 绑定准备指纹并明确清晰度仅记录原生尺寸、实际屏幕用途尚需人工复核，不声称自动计算屏幕纹素比。二维、程序化和三维 MUST 按实际用途检查，不强制固定4K或normal/roughness/emissive齐全度。审计 MUST 不改动原素材，入口为 m2v assets audit；素材、镜头或look变化使旧报告失效。`m2v assets report` 与 `m2v assets contact-sheet` MAY 作为制作期台账与候选检查入口，但 MUST NOT 替代审计或 prepare 的许可、摘要与一致性阻断，也不得写入审计报告或准备指纹。

#### Scenario: Hero 贴图不足
- **WHEN** 重点镜头使用低于4K的已登记素材
- **THEN** 记录原生尺寸和实际用途复核提示，不仅凭尺寸阻断；若画面实查模糊则返工

#### Scenario: 许可未知
- **WHEN** 任意登记素材许可未知，包括非重点镜头素材
- **THEN** 准备与审计失败并指出素材ID，不通过旧普通档绕过

#### Scenario: 辅助贴图缺失
- **WHEN** 二维、程序化或三维素材没有辅助贴图
- **THEN** 不因贴图配额拒绝，按实际表现需要决定是否补充

#### Scenario: 标准档不增加门禁
- **WHEN** general 未显式运行素材审计命令
- **THEN** prepare仍检查全部登记媒体许可，不能绕过；人工审美记录不增加CLI门禁

#### Scenario: 台账工具不替代审计
- **WHEN** 只运行了 `m2v assets report` 或 `m2v assets contact-sheet`
- **THEN** 不产生 `outputs/asset-audit.json`，不改变准备指纹，也不能据此声称许可审计或 prepare 已通过
