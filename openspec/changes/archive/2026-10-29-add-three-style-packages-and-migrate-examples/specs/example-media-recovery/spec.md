## MODIFIED Requirements

### Requirement: 固定素材恢复

风格示例 MUST 提供按配方下载或生成全部登记媒体的入口，校验 SHA-256 和媒体尺寸、视频时长，不改写来源登记和预期摘要。恢复入口与配方 SHALL 位于 `styles/examples/<style-id>/<slug>/assets/`。

#### Scenario: 空目录恢复
- **WHEN** 用户在没有媒体的风格示例运行恢复入口
- **THEN** 所有素材按既定处理恢复并通过登记信息校验。

#### Scenario: 缓存与失败
- **WHEN** 已有文件正确或任意待恢复项失败
- **THEN** 正确文件跳过，失败明确报错且不覆盖已有素材，不自动换源或接受新摘要。

### Requirement: 版本控制边界

仓库 MUST 保留公共字体及许可，并忽略风格示例媒体；解除跟踪前 MUST 验证完整恢复，改写历史前 MUST 创建可验证备份。风格示例媒体 SHALL 只位于 `styles/examples/*/*/assets/media/`、`styles/examples/*/*/assets/sound/` 等被忽略目录，恢复配方、分镜与场景源码 SHALL 保留在版本控制中。

#### Scenario: 历史同步
- **WHEN** 完成恢复验收并清理历史
- **THEN** 风格示例媒体不再出现在清理后的历史中，字体保留，远端 main 只在旧提交匹配时更新，本地媒体保持可用。
