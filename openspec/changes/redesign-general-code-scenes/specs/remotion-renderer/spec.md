## MODIFIED Requirements

### Requirement: 画面由 React composition 渲染
系统 SHALL 以共享 React composition 为唯一合成执行者，由 Remotion 逐帧渲染编码。general SHALL 使用 v8 全画布本地代码场景在 prepare 录制的无声片段；作品 MUST NOT 自行注册 Remotion 根、composition、契约页或共享时间轴。

共享 composition 可达画面 SHALL 由帧号或共享场景参数驱动，不依赖挂钟、系统随机数、CSS 动画或组件自带计时器。渲染前 SHALL 对共享源码和 CSS 静态检查，命中禁用写法时报出文件位置并拒绝。作品 scenes 代码 SHALL 仅运行于独立录制页，不进入 composition；其自由动画不承诺逐像素复现，正式导出只回放已验收片段。

#### Scenario: 使用帧号钩子
- **WHEN** 共享合成组件计算第 N 帧的显示状态
- **THEN** 结果来自帧号和运行时参数，与求值顺序和真实时间无关

#### Scenario: 组件库自带计时器
- **WHEN** 共享可达组件包含未经确定性适配的真实计时器或 CSS 动画
- **THEN** 静态检查拒绝并定位源文件

#### Scenario: 随机访问一帧
- **WHEN** 同一已准备作品的同一帧被直接求值两次
- **THEN** 回放同一片段，满足既有画面确定性阈值

#### Scenario: 作品试图声明独立 composition
- **WHEN** 作品试图声明独立 Remotion 根或 composition
- **THEN** 拒绝该材料，要求使用共享合成及本地录制入口
