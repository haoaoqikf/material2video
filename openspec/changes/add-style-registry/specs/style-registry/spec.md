## Purpose

提供独立于视频业务类型的可选风格包机制，使作品能够明确选择表现规范、复用参数组件与资源，并在依赖变化时重新准备，避免无效选择、越界加载和旧缓存误用。

## ADDED Requirements

### Requirement: 空注册目录与风格查询
系统 SHALL 从仓库 styles 发现风格包，提供 m2v styles 文本及 JSON 查询，校验清单、入口和资产来源许可；首期 SHALL 不包含正式风格。

#### Scenario: 空目录
- **WHEN** 尚未注册风格包
- **THEN** 文本显示暂无已注册风格，JSON 返回空数组，未选风格作品保持可用

### Requirement: 可选作品绑定
作品 SHALL 通过 style.id 选择单一风格；无效声明、未知风格、不支持的类型或实际画幅 SHALL 明确失败，禁止静默回退。

#### Scenario: 不支持的组合
- **WHEN** 作品选择未知风格或不支持的类型画幅
- **THEN** 校验和准备明确失败并指出原因

### Requirement: 显式表现接入
general 场景 SHALL 能读取风格参数并显式导入登记组件和资产；导入 SHALL 限于所选包、SDK 和既有批准依赖。风格 SHALL 不自动换肤或改变业务计算、制作门和评审职责。

#### Scenario: 包边界
- **WHEN** 场景导入其他风格或包外文件
- **THEN** 构建失败，包括符号链接越界

### Requirement: 准备与缓存绑定
系统 SHALL 记录所选风格的 ID、版本和内容指纹；包内容变化 SHALL 使准备和对应场景缓存失效，状态 SHALL 展示风格及准备有效性。

#### Scenario: 风格变化
- **WHEN** 指导、参数、组件或资产变化
- **THEN** 旧准备要求重新 prepare，场景缓存依赖变化
