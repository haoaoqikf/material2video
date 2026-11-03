## Why

现有 `videos/building-construction/two-story-house` 是一条 40 秒、单一等轴测机位、构件按阶段整体淡入的动画。观众看不出“怎么建起来”：没有构件级动作、没有镜头切换或近景、没有连接与承重关系的可见线索；主体只占画面一小部分，门窗在墙完成后才以贴片出现，屋顶像一块压板。用户明确反馈“完全看不懂在表达什么、效果也很差”。现行规格已经写了构件引用、依赖、镜头区间与剖开/隐藏，但 v1 材料与渲染器没有实现这些，规格与实现脱节。

## What Changes

- **BREAKING** `building.json` 升到 v2：洞口增加窗台高度；屋顶改为显式 `roof`（坡屋顶/平屋顶、檐口、脊高）；楼梯增加位置与梯井参数；保留稳定构件 ID 与类别。
- **BREAKING** `construction.json` 升到 v2：用 `shots` 多镜头轨道替换单一 `camera`；用 `steps` 构件级建造动作（开挖、浇筑、立柱、架梁、浇板、砌墙、吊装屋顶、安装门窗）替换按阶段整体显现；每步声明构件选择器、动作、时间窗与前置依赖；镜头可声明仅影响取景的隐藏构件。
- 渲染器从 SVG 平面投影改为现有 three.js/Remotion 底座上的真实三维：阴影、接触阴影、材质区分、轮廓线、背景渐变；保留逐帧确定性，不引入第二套渲染引擎。
- 新增可读性层：常驻阶段轨、当前构件名称小字标注与引线、完工体量幽灵轮廓、比例尺与示意边界小字；近景镜头用剖切隐藏近侧墙，完工镜头恢复。
- 首例重制为 60 秒/1800 帧、1920×1080、30 fps、无音轨；阶段、镜头与动作全部从 v2 材料推导；v1 材料明确拒绝，不提供迁移工具。
- 更新类型目录、init 模板、Python 与前端测试、类型指南、README/PROJECT_PLAN 生成清单与 OpenSpec 规格。
- 验证增加“独立观察者复述建造顺序与连接”和同帧 PSNR/乱序取帧；旧候选、QA 与评审证据作废，需重渲染与独立评审。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `building-construction-video`: 材料升级到 v2；新增镜头轨道、构件级建造动作、依赖与取景隐藏；新增可读性、视觉呈现与复述验收要求；首例由 40 秒改为 60 秒。

## Impact

- Python：`src/m2v/types/building_construction/{schema,materials,adapter,render}.py`、`src/m2v/type_system/catalog.json` 的 init 模板与类型说明。
- 前端：`web/src/types/building_construction/BuildingConstruction.tsx` 及同目录新模块；复用已安装的 `three` 0.186.1、`@react-three/fiber` 9.8.2、`@react-three/drei` 10.7.9、`postprocessing` 3.2.2，不新增渲染引擎。
- 测试：`tests/types/building_construction/test_building_construction.py`，以及目录、文档、源码确定性闸门相关测试。
- 文档：`.agents/skills/material2video/references/building-construction-video.md`、`README.md`、`docs/PROJECT_PLAN.md`、`openspec/specs/building-construction-video/spec.md`。
- 内容：`videos/building-construction/two-story-house/{building,construction,manifest}.json` 重写为 v2 并重渲染；作品与生成媒体仍不入库。
- 性能：WebGL 渲染预计比 SVG 慢，需记录渲染时长、内存与同帧确定性；`three-bvh-csg` 经评估为 MIT、0.0.18，但本轮不引入，墙洞用 `ExtrudeGeometry` 挖孔、剖切用 three.js clipping plane。
