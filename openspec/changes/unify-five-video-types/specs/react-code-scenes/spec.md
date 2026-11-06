## ADDED Requirements

### Requirement: 五类共用场景与结构化来源
五类 MUST 经相同的本地代码场景打包与逐帧采集链路进入单一成片 composition；场景 SDK MUST 按 ID 暴露已准备的结构化来源，并保留已导入媒体、帧驱动动效和安全边界。风格包导入 MUST 被拒绝。

#### Scenario: 结构化来源进入场景
- **WHEN** 数据演化或三维空间场景读取有效来源 ID
- **THEN** 收到已校验且与准备指纹绑定的结果

#### Scenario: 已删除风格导入
- **WHEN** 场景导入 `m2v/style` 或其子路径
- **THEN** 打包明确失败，不回退为未选风格
