## Why

用户已选定《太阳系，成了一幅画》方案：15 秒、无声、二向箔掠过太阳系，三维空间被压成有边界的圆形油画，最后侧视证明零厚度。作品的 `DESIGN.md`、四张独立目标关键帧与两轮盲审帧包已经完成，但分镜仍是初始化脚手架，场景、素材、音频、成片与验收记录均未落地，需要按 OpenSpec apply 完成制作。

## What Changes

- 新增作品级规格 `two-dimensional-foil-video`，约束《太阳系，成了一幅画》的可观察交付行为、素材来源政策与验收证据。
- 把内容根 `videos/general/solar-system-2d-foil`（按仓库约定不入库）从脚手架补成可生成作品：1920×1080、60 fps、900 帧、无旁白、单幕代码场景，含二向箔入场、沿黄道面的压平传播、完整圆画与侧视零厚度。
- 导入 NASA/JPL 与 Solar System Scope 的行星颜色贴图，登记作者、许可、来源与实测尺寸；深空、轨道、二向箔、颜料重采样与圆画边缘由本地代码生成。
- 用本地确定性脚本原创合成 15 秒音床与三个事件声，登记来源、许可、采样数与摘要，按现有音轨契约接入。
- 关键帧、核心动态窗口、完整候选各保留独立评审与帧序列证据；技术交付与制作复核分别记录。
- 制作中发现的可复用流程问题，在本轮实施并验证；超出范围的事项登记 OpenSpec 或项目规划。

## Capabilities

### New Capabilities

- `two-dimensional-foil-video`：约束《太阳系，成了一幅画》的时长、画幅、事件顺序、三维到二维的可观察变化、零厚度侧视、素材来源与验收证据。

### Modified Capabilities

无。

## Impact

实施涉及 `videos/general/solar-system-2d-foil` 的 `project.json`、`storyboard.json`、`scenes/`、`assets/` 与 `outputs/`，以及 `openspec/` 中的本变更与归档后的主规格。复用 general v8 代码场景、素材导入、统一音轨与既有渲染/验收链路，不新增视频类型、不升级分镜版本、不引入新依赖。内容根按 `.gitignore` 不入库，仓库只提交规格与必要的文档修正。
