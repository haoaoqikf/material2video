## ADDED Requirements

### Requirement: 共享动效组件兼容代码场景

代码场景 SHALL 通过 `m2v/code-scene` 使用共享 L1/L2 动效组件。共享组件 MUST 只依赖显式 `progress`/`easing`，MUST NOT 依赖 Remotion composition context；`sequential` 与 `pure-time` MUST 使用同一套组件。作品与风格组件的直接 import 白名单 MUST NOT 因本能力放宽；新库只能由共享运行时封装后导出。

#### Scenario: 顺序录制
- **WHEN** 未声明 pure-time 的场景使用共享组件
- **THEN** 组件按连续帧推进，不启动自身计时器

#### Scenario: 纯时间录制
- **WHEN** 声明 pure-time 的场景使用共享组件
- **THEN** 场景通过静态源码闸门，正倒序 PSNR ≥ 60 dB

#### Scenario: 构建边界
- **WHEN** 场景从 `m2v/code-scene` 导入共享组件
- **THEN** esbuild 构建成功；作品源码不直接导入 `@remotion/*`
