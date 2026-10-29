## MODIFIED Requirements

### Requirement: 空注册目录与风格查询

系统 SHALL 从仓库 styles 的直接子目录发现风格包，提供 `m2v styles` 文本及 JSON 查询，校验清单、入口和资产来源许可。仓库 SHALL 登记 `vibe-fable`、`vibe-night`、`doc-archive`、`count-ledger` 与 `deep-journey` 五个正式风格包；未注册任何风格时 SHALL 返回空目录，未选风格作品 SHALL 保持可用。规范示例 SHALL 位于 `styles/<style-id>/examples/<slug>/`，不参与风格发现；不再维护 `styles/examples/` 或旧路径别名，其余直接子目录 SHALL 为有效风格包。

#### Scenario: 已登记风格
- **WHEN** 运行 `m2v styles` 或 `m2v styles --json`
- **THEN** 返回五个正式风格包的 id、version、description、types 与 frames，清单、入口或资产许可非法时明确失败

#### Scenario: 保留目录不被发现
- **WHEN** 各风格的 examples 子目录包含作品及其输出
- **THEN** 风格查询仅返回直接子目录的风格，不把示例当作独立风格，直接加载 examples 明确失败

#### Scenario: 空目录
- **WHEN** 仓库未注册任何风格包
- **THEN** 文本显示暂无已注册风格，JSON 返回空数组，未选风格作品保持可用
### Requirement: 显式表现接入
general 场景 SHALL 能读取风格参数并显式导入登记组件和资产；导入 SHALL 限于所选包、SDK 和既有批准依赖。风格 SHALL 不自动换肤或改变业务计算、制作门和评审职责。

#### Scenario: 包边界
- **WHEN** 场景导入其他风格或包外文件
- **THEN** 构建失败，包括符号链接越界


#### Scenario: 示例与共享实现双向隔离
- **WHEN** 位于风格内的示例以相对路径导入共享实现、兄弟作品，或共享组件导入 examples 子树
- **THEN** 构建失败；示例只允许自身作品内相对导入，使用共享风格必须经过登记入口；清单不得把 examples 下的指导、参数、组件或资产登记为共享入口

#### Scenario: 嵌套作品自有资产
- **WHEN** 风格内的示例相对导入自己作品内的合法素材
- **THEN** 按作品边界处理，不误用共享风格资产登记规则，符号链接不能绕过边界
### Requirement: 准备与缓存绑定
系统 SHALL 记录所选风格的 ID、版本和内容指纹；共享包内容变化 SHALL 使准备和对应场景缓存失效，状态 SHALL 展示风格及准备有效性。

#### Scenario: 风格变化
- **WHEN** 指导、参数、组件或资产变化
- **THEN** 旧准备要求重新 prepare，场景缓存依赖变化

#### Scenario: 示例不改变风格指纹
- **WHEN** 新增、修改或删除直属 examples 子树中的示例源码、恢复媒体或输出文件
- **THEN** 风格指纹保持不变且不读取示例子树；示例自己的依赖变化仍使自身准备失效，共享指导、参数、组件与资产变化仍使风格依赖失效
