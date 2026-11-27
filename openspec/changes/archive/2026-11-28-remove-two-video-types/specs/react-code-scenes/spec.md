## ADDED Requirements

### Requirement: 三类共用场景与结构化来源

本要求只约束作品实际采用的本地实现和默认工程模板。主项目 MUST NOT 提供强制运行时SDK；构建器 MUST 从作品自身安装和锁文件解析依赖，MUST NOT 读取主项目源码或全局依赖登记。参考未被采用时 MUST NOT 成为构建或指纹输入。

三类 MUST 经各作品自己的本地代码场景打包与逐帧采集链路进入单一成片 composition；场景 作品本地模块 MUST 按 ID 暴露已准备的结构化来源，并保留已导入媒体、帧驱动动效和安全边界。风格包导入 MUST 被拒绝。

#### Scenario: 结构化来源进入场景
- **WHEN** 数据演化或三维空间场景读取有效来源 ID
- **THEN** 收到已校验且与准备指纹绑定的结果

#### Scenario: 已删除风格导入
- **WHEN** 场景导入 `m2v/style` 或其子路径
- **THEN** 打包明确失败，不回退为未选风格

## REMOVED Requirements

### Requirement: 五类共用场景与结构化来源

**Reason**: 公开能力范围收缩到三个类型。
**Migration**: 适用 三类共用场景与结构化来源。
