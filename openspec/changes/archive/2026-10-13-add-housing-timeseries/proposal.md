## Why

项目目前没有用于呈现住房价格年度变化的专用工作流。新增该类型后，可以用可追溯的年度统计数据制作郑州住宅销售均价视频，并在画面中说明数据口径变化。

## What Changes

- 新增 `housing-timeseries` 视频类型，使用统一 `m2v` 生命周期与离线数据材料。
- 新增无声竖屏年度价格折线画面，逐年展示住宅销售均价，并标出 2005 年统计口径变化。
- 更新类型目录、README、项目规划、制作 Skill 与 OpenSpec 规格。
- 用郑州市统计局公开的 2002—2024 年住宅销售额和面积生成一份位于仓库 `videos/` 忽略目录的郑州作品并渲染视频；均价按公布值计算并说明原表精度限制。

## Capabilities

### New Capabilities
- `housing-timeseries`: 年度住宅销售均价材料校验、动画准备、预演和渲染。

### Modified Capabilities
- 无

## Impact

- 影响 `src/m2v/types/` 类型实现与目录、Remotion 组合注册和画面、README/规划/Skill 文档及测试。
- 新增无运行时依赖；作品数据、预演及成片位于仓库内被忽略的 `videos/zhengzhou-housing-2002-2024/`，不纳入 Git。
