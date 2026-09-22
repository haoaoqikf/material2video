## ADDED Requirements

### Requirement: 中层视觉原语表达常见论证关系
原语目录 SHALL 登记 `flow`、`cycle`、`timeline`、`gauge`、`pictogram`，并为每种原语声明受控属性、容量、内容引用和支持的语义动作。它们 SHALL 由共享解释器渲染，不要求作品专属代码。

#### Scenario: 流程与循环
- **WHEN** 场景树用 flow 表达顺序或因果，或用 cycle 表达闭环过程
- **THEN** 画面显示确定性的对象、方向连接和当前阶段，而不是仅把标签排列成行或圆周

#### Scenario: 受控图标
- **WHEN** pictogram 引用 Lucide 白名单中的图标名
- **THEN** 系统离线绘制本地 SVG；未知图标在校验阶段失败

### Requirement: 中层原语由节拍驱动且布局冻结
中层原语 SHALL 读取共享 beat 状态，只改变注册表允许的可视状态；节点数量、内容与基础几何 SHALL 在帧间保持由同一场景树确定。

#### Scenario: 仪表状态变化
- **WHEN** gauge 在 accumulate beat 中从低值推进到高值
- **THEN** 指示状态按 beat 局部进度变化，容器几何与标签布局不重排
