## ADDED Requirements

### Requirement: 白名单视觉库具有专用确定性规则
系统 SHALL 为代码场景允许使用的 ECharts、Dagre 与 Lucide 维护可机检的确定性规则：ECharts 的内置动画 SHALL 关闭，Dagre 的输入顺序与布局配置 SHALL 稳定，Lucide SHALL 仅作为静态 SVG 表达；这些库 SHALL NOT 获得网络、挂钟或独立时间轴能力。

#### Scenario: ECharts 开启内置动画
- **WHEN** 代码场景的 ECharts 配置启用内置动画
- **THEN** 适配检查失败并提示改为由当前帧计算图表状态

#### Scenario: Dagre 输入稳定
- **WHEN** 相同节点、边和固定配置以稳定顺序进入 Dagre
- **THEN** 重复布局产生相同几何结果

#### Scenario: Lucide 静态使用
- **WHEN** 代码场景使用 Lucide 图标并由 Remotion 帧值控制其外层可视属性
- **THEN** 图标作为确定性 SVG 参与渲染，不启动独立动画

## MODIFIED Requirements

### Requirement: 接入依赖随仓库锁定
前端依赖 SHALL 由锁文件锁定并入库，SHALL NOT 只依赖浮动的版本范围。共享工程 SHALL 维护代码场景可导入包的精确白名单，作品 SHALL NOT 提供自己的依赖清单或触发包安装。本次白名单 SHALL 包含 React、React DOM、Remotion、Tailwind、ECharts、Dagre 与 Lucide；新增任何其他包 SHALL 作为独立行为变更评审，而不是由作品按需引入。

渲染期 SHALL NOT 需要网络：字体、素材、作品源码和允许依赖 SHALL 在渲染前本地可用。系统 SHALL 在参考文档中记录所用第三方库的许可证与升级触发条件，使许可义务在越界之前可见。

#### Scenario: 依赖未锁定
- **WHEN** 前端工程没有锁文件，锁文件落后于清单，或白名单包版本未被锁定
- **THEN** 机检失败

#### Scenario: 作品声明额外依赖
- **WHEN** 作品目录包含自己的依赖清单或源码导入白名单之外的包
- **THEN** 校验失败且系统不会执行包安装

#### Scenario: 渲染时断网
- **WHEN** 共享依赖已安装且作品源码、字体与资产均在本地，渲染时无网络
- **THEN** 渲染正常完成

#### Scenario: 许可证越界条件可见
- **WHEN** 查阅前端工程的说明文档
- **THEN** 能找到 ECharts、Dagre、Lucide 及其他共享第三方库的许可证类型与升级注意事项
