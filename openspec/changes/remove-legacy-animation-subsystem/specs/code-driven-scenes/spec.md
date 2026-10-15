## REMOVED Requirements

### Requirement: 作品可以声明代码场景
**Reason**: 该需求描述的是 v4 全片契约：`world.renderer` 只声明一次、模块贯穿整条视频、`stages[]` 不得自带 renderer、且全片只能在 tree 与 code 之间二选一。承载这套语义的 world/stage 运行时、场景树与 `M2VComposition` 均已删除；通用视频改为在**幕**上声明 renderer。
**Migration**: 作品把 `world.renderer` 与 `stages[]` 改写为 `general-plan.json` 的 `scenes[]`，在需要代码画面的那一幕上写 `renderer: { kind: "code", module: "<模块标识>" }`；模块文件位置与默认导出要求不变。

### Requirement: 代码场景继续接受统一体检
**Reason**: 该需求要求共享契约探针读取代码场景的节点标识与语义角色，并让 C/K/M 系列闸门量测该场景。C/K/M 闸门实现（`LayoutGeometryPreflight`、`runtime/geometry.ts`）已删除，且现存唯一布局量测 `explainer_render.py::MEASURE` 只读取 `data-m2v-copy` / `data-m2v-box` / `data-m2v-subtitle` / `data-m2v-content` 标记，只覆盖 `article-narrative` 的 v5 讲解模板，不覆盖 `general` 的代码场景。继续保留该需求等于承诺一项无人执行的验收。
**Migration**: 不需要迁移。`@m2v/scene` 仍导出 `probe()` / `useProbeProps()`，作者可继续用稳定节点标识标注文本与容器；当前没有消费者读取这些标记，通用视频的代码场景不参与浏览器布局量测。

### Requirement: 代码场景接收统一导演运行时上下文
**Reason**: 该需求要求注入全局 `beats`、阶段语义状态、全片镜头进度与跨阶段累计对象状态，并保证随机寻帧得到与场景树相同的上下文。节拍运行时（`engine/beats.py`）、镜头与状态轨道（`runtime/camera*.ts`、`stateTracksV4.ts`）已删除；通用视频没有语义节拍、镜头运动与跨幕对象状态可注入。
**Migration**: 不需要迁移。代码场景只依据幕数据与帧号编排动作；`beats` / `motion` / `objectStates` 槽位改为传入文档化的空值。

### Requirement: 代码场景显式加入节点级连续性
**Reason**: 节点级连续性与连续性探针由 v4 场景树运行时（`runtime/continuity.ts`、`worldTreeV4.ts`）实现，该运行时已删除；通用视频不提供跨幕对象身份与几何追踪。
**Migration**: 不需要迁移；代码场景在单幕内自行维护对象身份，跨幕一致性由作者在幕数据中显式表达。

## ADDED Requirements

### Requirement: 作品可以在幕上声明代码场景
作品 SHALL 在 `general-plan.json` 的幕上以 `renderer: { kind: "code", module: "<scenes/ 下的模块标识>" }` 声明代码场景；模块标识 SHALL 解析到当前作品 `scenes/` 目录内的真实模块，该模块 SHALL 默认导出 `M2VCodeScene` 组件。共享层 SHALL 注入该幕的 `data`、幕内帧与幕内进度、`fps`、画布尺寸、主题与按幕标识播种的稳定随机源；模块 SHALL NOT 自行决定幕顺序、总时长或字幕边界。

#### Scenario: 幕级模块进入全片时间轴
- **WHEN** 作品的某一幕声明 `renderer.kind` 为 `code`
- **THEN** 该幕的预览、预演与导出使用同一模块，并落在该幕在全片中的帧区间内

#### Scenario: 模块缺失或没有规定导出
- **WHEN** 幕引用的模块无法解析、逃出 `scenes/` 或没有默认导出规定的场景组件
- **THEN** 校验在启动浏览器或渲染前失败，并指出该幕的 `renderer.module` 与目标源码位置

#### Scenario: 同一幕同时声明 renderer 与内联内容
- **WHEN** 一幕既声明 `renderer` 又声明该幕类型自带的内联图文内容
- **THEN** 校验拒绝该幕，要求二选一

### Requirement: 代码场景接收幕级上下文槽位
共享层 SHALL 向代码场景注入幕标识、幕数据、幕内帧与幕内进度、`fps`、画布尺寸、主题与稳定随机源，并 SHALL 保留类型化的 `beats`、`motion` 与 `objectStates` 槽位。通用视频当前不提供语义节拍、镜头运动与跨幕对象状态，这些槽位 SHALL 以文档化的空值传入（`beats.current` 为 `null`、`beats.plan` 为空、`motion.camera.kind` 为 `"none"`、`motion.continuity` 为 `null`、`objectStates` 为空对象）；代码模块 SHALL NOT 假设这些槽位被填充。

#### Scenario: 同一帧重复求值得到同一上下文
- **WHEN** 以任意顺序、任意次数求同一幕的同一帧号
- **THEN** 代码场景收到相同的幕数据、幕内帧、幕内进度与随机序列

#### Scenario: 代码场景读取空镜头槽位
- **WHEN** 代码场景读取 `motion.camera`
- **THEN** 读到文档化的空镜头（`kind` 为 `"none"`），并据此走无镜头分支而不是抛错
