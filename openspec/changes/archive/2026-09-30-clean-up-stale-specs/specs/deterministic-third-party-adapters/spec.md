## REMOVED Requirements

### Requirement: 第三方组件按动画机制分类

**Reason**: 第三方组件分类表（`web/src/third-party/catalog.json`）与整页组件接入路径已随「场景树 + 代码场景」架构一并删除，`web/src/third-party/` 目录不存在且被架构禁止；分类表不再有任何消费者，本条不可验证。第三方依赖的确定性要求由 `code-driven-scenes` 的模块白名单与白名单视觉库适配规则承担。

**Migration**: 无需迁移。需要第三方库能力时，按 `code-driven-scenes` 在作品的代码场景里声明，并使用白名单视觉库（ECharts / Dagre / Lucide）的专用适配规则。

### Requirement: CSS 动画的帧同步包装

**Reason**: 帧同步包装层 `FrameSyncedCssAnimation` 全仓库已不存在，随整页组件接入机制删除；本条描述的实现对象与判据都不存在。

**Migration**: 无需迁移。画面动效一律走场景树的受控配方，或由代码场景用帧号驱动的纯函数实现。

### Requirement: 自带时钟组件必须改写成帧驱动

**Reason**: 该条以「整页组件接入清单」为适用对象，清单与接入流程已删除；对代码场景的同类约束已由 `remotion-renderer` 的帧纯函数与源码静态检查覆盖，本条不再有独立的可验证对象。

**Migration**: 无需迁移。约束仍在生效，但由 `remotion-renderer`「画面由 React composition 渲染」与 `code-driven-scenes`「代码场景保持帧确定性」承担。

### Requirement: 未改造组件不得进入渲染路径

**Reason**: 该条要求渲染路径在开渲前拒绝未改造的第三方组件，与 `remotion-renderer`「画面由 React composition 渲染」中的源码静态检查是同一条要求；分类表机制删除后本条失去判定对象，保留会形成两个真源。

**Migration**: 无需迁移。静态检查仍在，且仍会在命中禁用写法时报出文件与位置、拒绝开渲。

### Requirement: 接入依赖随仓库锁定

**Reason**: 该条的适用对象是「接入第三方组件时随仓库锁定依赖」，而接入机制已删除；依赖锁定本身由包清单与锁文件承担，不需要一条针对已废止流程的需求。

**Migration**: 无需迁移。代码场景的依赖仍随仓库锁定，约束见 `code-driven-scenes`。

### Requirement: 代表性组件验证适配闭环

**Reason**: 该条要求至少有一个随仓库固化的代表组件来证明适配闭环，该代表组件与分类表都已删除，闭环不再存在，本条不可验证。

**Migration**: 无需迁移。代码场景的能力由 `code-driven-scenes` 的白名单与体检探针覆盖。

### Requirement: 白名单视觉库具有专用确定性规则

**Reason**: 该条与 `code-driven-scenes`「白名单视觉库采用确定性适配」重复，且在本次清理后成为同一约束的第二处描述。

**Migration**: 无需迁移。ECharts / Dagre / Lucide 的确定性适配规则继续由 `code-driven-scenes` 描述与验证。
