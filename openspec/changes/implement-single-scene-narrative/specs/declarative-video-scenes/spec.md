## Purpose

以全片唯一画面根及全局对象契约驱动 tree/code 两种单一 renderer 路径。

## MODIFIED Requirements

### Requirement: 视觉声明校验
系统 SHALL 在预览、评审或导出前校验全片唯一 renderer、v4 版本、对象引用、状态轨道与时间绑定。tree SHALL 拒绝未登记原语、属性、动效、容量超限及代码注入；code SHALL 校验模块、白名单、安全、确定性和最低探针。错误 SHALL 定位到字段或源码。

#### Scenario: 树中注入代码
- **WHEN** 受控声明包含 HTML、CSS 或执行表达式
- **THEN** 校验失败，自由代码只能通过显式全片代码模块提供

#### Scenario: 无效对象
- **WHEN** 轨道引用未知全局节点
- **THEN** 校验失败并指出轨道目标

#### Scenario: 旧分镜
- **WHEN** version/schemaVersion 不是 4
- **THEN** 拒绝执行，不启动旧组件

#### Scenario: 未注册组件
- **WHEN** 场景树节点类型不在原语目录中
- **THEN** 校验失败并指出该节点的类型字段

#### Scenario: 不受支持的视觉值
- **WHEN** 场景树属性、布局值、主题或动效超出目录声明范围
- **THEN** 校验失败并指出具体字段，预览与导出均不开始

#### Scenario: 场景树注入代码
- **WHEN** 场景树字段包含 HTML、CSS、JavaScript、表达式或包引用
- **THEN** 校验失败；自由代码只能通过显式代码场景模块提供

#### Scenario: 代码场景违反执行边界
- **WHEN** 作品级模块导入非白名单依赖或使用被禁止的执行能力
- **THEN** 校验失败并指出源码位置，预览与导出均不开始

#### Scenario: v3 之前分镜进入入口
- **WHEN** 分镜不是 version/schemaVersion 4
- **THEN** 校验失败并提示按 v4 契约重新编排，不启动旧默认组件或迁移路径

### Requirement: 共享画面路径与预设必填
系统 SHALL 提供全片 tree 和全片 code 两条路径，共用 composition、时间轴、契约页和输出归属规则，一个作品 SHALL NOT 混用两条路径。分镜内容与顺序是单一真源，媒体仅派生实际时间。Keynote 预设必填。tree 声明字号档时 SHALL 按实测宽度取档并记录证据；未声明时不取档。code 使用共享令牌但不被树布局引擎改写。

#### Scenario: 持续树
- **WHEN** world.renderer 为 tree
- **THEN** 全片持续渲染同一棵树，阶段只更新受控状态

#### Scenario: 持续模块
- **WHEN** world.renderer 为 code
- **THEN** 共享 composition 全片承载同一模块，不按阶段重挂载

#### Scenario: 重复取档
- **WHEN** 相同内容及帧重复取档
- **THEN** 第二次不产生额外样式或内容写入

#### Scenario: 未声明预设
- **WHEN** visual.preset 缺失或未知
- **THEN** 校验失败，不回退默认预设

#### Scenario: 仅有文章和分镜的新视频
- **WHEN** 规范视频目录中存在有效新版分镜且所有幕选择场景树
- **THEN** 系统使用共享场景树 composition 完成预览或导出，输出归属该视频目录

#### Scenario: 包含作品代码场景的新视频
- **WHEN** 有效新版分镜引用通过校验的作品级场景模块
- **THEN** 共享 composition 在全片挂载同一模块，预览、评审和导出使用同一实现

#### Scenario: 重复取同一帧
- **WHEN** 共享 composition 以相同分镜、媒体清单、作品源码和帧号重复绘制
- **THEN** 场景状态、节点几何和可见画面保持在确定性门槛内一致

#### Scenario: 预设生效时取档
- **WHEN** 分镜启用了设计语言预设，且场景树文字原语声明了字号档上限
- **THEN** 共享 composition 按实测宽度取档，并把档位与是否实测记录在该节点上

#### Scenario: 未声明字号档上限时不取档
- **WHEN** 预设生效，但该文字原语没有声明字号档上限
- **THEN** 共享 composition 不执行取档，节点字号和行高使用默认令牌，也不写入取档属性

#### Scenario: 同一帧重复取档不产生写入
- **WHEN** 同一场景树节点在同一文案下被连续取档两次
- **THEN** 第二次不产生任何节点样式或内容改动

### Requirement: 图表缺测值保留类别位置
图表数据 SHALL 允许 `value: null` 表示该类别当前没有已提供的数值。共享渲染器 SHALL 保留该类别的固定横向位置与标签，但不为缺测项绘制柱、点或数值；折线 SHALL 连接已有数值点，缺测类别 SHALL NOT 挤压或重排后续类别。Python 校验器与浏览器渲染 SHALL 对该表示保持一致。

#### Scenario: 只展示有依据的序列端点
- **WHEN** 分镜提供第 1 周与第 4 周数值，而第 2、3 周为 `null`
- **THEN** 图表保留四个周标签，只绘制两个端点与二者之间的趋势线，不虚构中间值
