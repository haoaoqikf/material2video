## Context

当前 `building-construction` 的渲染器是 `web/src/types/building_construction/BuildingConstruction.tsx`：把 `building.json` 展开成一组轴对齐盒子，按阶段进度整体抬升 0.5 个单位并淡入，用固定等轴测方位 35°→55° 的单机位绘制 SVG。v1 材料只有 `stages` 与一个 `camera`，没有构件引用、依赖、镜头切换或取景隐藏；规格里写的这些能力并没有实现。仓库已有 `vehicle-showcase` 以 raw three.js + Remotion 的 `delayRender` 方式逐帧渲染，证明 WebGL 可以在现有链路中确定性出帧；共享层另有 `@react-three/fiber`、`drei` 与 `postprocessing` 依赖。

## Goals / Non-Goals

**Goals:**

- 用构件级步骤、依赖与多镜头把“先做什么、后做什么、构件怎么接”变成可验证的数据与画面。
- 用真实三维的材质、阴影、轮廓与剖切提高画面质量，同时保持逐帧确定性。
- 让观众在无旁白、无设计文档的情况下复述建造顺序和柱梁板墙的连接关系。
- 材料升级为 v2，v1 明确拒绝；不保留兼容分支。

**Non-Goals:**

- 不做 BIM/CAD 导入、结构计算、真实施工组织或任意建筑生成。
- 不做 photoreal 或 PBR 资产级渲染；仍是程序化示意，不引入外部模型/贴图。
- 不加入配音或音轨；首例仍为无声交付。若未来要声音，另立变更。
- 不改变其他视频类型的材料、渲染或评审链路。
- 不引入第二套渲染引擎，也不为同一能力重复增加依赖。

## Decisions

### 1. 用 raw three.js 组件，而不是 R3F 或继续 SVG

选择 raw three.js（与 `VehicleShowcase` 同一模式）：在 `useLayoutEffect` 中创建一次 `WebGLRenderer`、场景、相机、材质与灯光，每帧只更新对象矩阵、可见性与相机，然后渲染一次；`delayRender`/`continueRender` 控制资源就绪。这样能直接控制 shadow map、clipping plane、透明排序与渲染顺序，也避免 R3F 的 React 调和与帧驱动时序在 1800 帧长片里引入不确定性。

替代方案：
- R3F：声明式、代码短，但需要把 `useCurrentFrame` 注入场景，且 reconciler 的提交时序与 `delayRender` 组合更难证明同帧一致；本类型已有 raw three 的成熟先例，不选。
- 继续 SVG：确定性和实现成本最低，但无法提供真实阴影、材质、剖切与近景空间关系，正是本轮要解决的问题。

### 2. 材料升级为 v2，并拒绝 v1

`building.json` v2：

```json
{
  "schemaVersion": 2,
  "canvas": {"width": 1920, "height": 1080},
  "house": {
    "width": 12, "depth": 9, "floors": 2, "floorHeight": 3, "bayCount": 3,
    "roof": {"type": "gable", "height": 2.2, "overhang": 0.6},
    "wallThickness": 0.25, "foundationDepth": 1.2, "sitePadding": 3,
    "stairs": {"side": "right", "offset": 1.0, "width": 1.4},
    "openings": [
      {"id": "door-entry", "floor": 1, "side": "front", "offset": 5.1,
       "width": 1.4, "height": 2.3, "sill": 0}
    ]
  }
}
```

`construction.json` v2：

```json
{
  "schemaVersion": 2,
  "durationSeconds": 60,
  "fps": 30,
  "stages": [
    {"id": "site", "label": "场地与开挖", "startSeconds": 0, "endSeconds": 10}
  ],
  "shots": [
    {"id": "establish", "startSeconds": 0, "endSeconds": 8,
     "camera": {"position": [18, 14, 20], "target": [0, 3, 0], "fov": 38},
     "hide": []}
  ],
  "initial": ["site", "ground-grid"],
  "steps": [
    {"id": "excavate", "stage": "site", "select": ["excavation"],
     "action": "excavate", "startSeconds": 1, "endSeconds": 5, "after": []},
    {"id": "footing", "stage": "site", "select": ["foundation-*"],
     "action": "pour", "startSeconds": 6, "endSeconds": 9, "after": ["excavate"]}
  ]
}
```

v1 直接失败并提示“需按 v2 重写 building.json/construction.json”，不迁移。理由：v1 没有步骤/镜头/窗台/屋顶/楼梯位置，无法可靠推导新语义；项目规则也要求版本升级默认不兼容。

### 3. 构件图先展开，再用 glob 选择器引用

Python 侧和 TypeScript 侧用同一套确定性规则生成构件 ID：

- `site`、`excavation`、`foundation-slab`、`foundation-ring-*`
- `column-{floor}-{bay}-{front|back}`、`beam-{floor}-{front|back}-{bay}`
- `slab-{floor}`、`stair-{floor}-{step}`、`stairwell-{floor}`
- `wall-{floor}-{side}-{segment}`、`roof-{panel}`、`opening-{id}`、`finish-{id}`、`yard-*`

`steps[].select` 只支持末尾 `*` 的简单 glob；Python 校验器展开后必须满足：每个非 `initial` 构件恰好匹配一次；选择器不得重叠；`initial` 不得被步骤再次匹配；未匹配到任何构件的选择器失败。这样既保留可读的材料，又不用手写数百个构件 ID。

替代方案：在 `building.json` 里手写每个构件。缺点是把生成规则复制进材料，容易漂移；glob 仍能表达“所有一层柱”这类建造单元。

### 4. 步骤动作是闭式函数，依赖只约束开始时间

每个步骤声明 `action` 与可选几何参数；渲染器按 `frame` 求 `progress = smooth((t - start) / (end - start))`，再求该步所选构件的变换：

- `excavate`：基坑深度与土层层数增长；
- `pour`：基础/楼板顶面从底部长到最终高度，湿料色在步骤内渐变到固化色；
- `grow`：柱从柱脚向上生长；
- `slide`：梁沿轴向从场外滑入并落位；
- `lift`：墙板/屋面板从上方落到最终高度；
- `rotate`：屋面板块从临时角度转到设计坡度；
- `insert`：门窗框与玻璃从略小的尺度淡入并吸附到洞口；
- `spread`：庭院路径沿长度展开。

`after` 只约束步骤开始不得早于依赖结束；不把上一帧状态作为输入。这样任意帧 seek 与乱序取帧都能得到同一画面。

### 5. 镜头用显式 shot 轨道，切换即硬切

`shots` 覆盖全片、首尾相接、不重叠。每个 shot 有固定 `position`/`target`/`fov`，可在 shot 内用 `camera.from`/`to` 做单向缓动；shot 边界默认硬切，建筑示意不要求溶解。计划 6 个镜头：全局建立、基础近景、一层框架近景、二层框架拉远、墙体与屋顶、完工环绕。近景用 35–45° 透视与较低机位，让柱梁板交接占据画面；完工镜头回到 3/4 全景。

`shots[].hide` 只隐藏取景中的构件（例如近侧墙），实现剖切观察；隐藏不改建成状态，最终镜头 `hide: []` 恢复全部构件。实现上用对象 `visible` 与 three.js clipping plane，不使用会改变几何的布尔运算。

### 6. 画面质量用灯光、材质、轮廓与接触阴影

- 灯光：一盏带阴影的平行主光 + 半球补光；阴影方向固定，shadow map 2048；构件移动时每帧更新 shadow map。
- 材质：混凝土（暖灰、粗糙）、深混凝土、木（门窗/楼梯）、玻璃（低不透明度、低粗糙度）、金属屋面、土壤、草地/铺装；明度与粗糙度可区分。
- 轮廓：`EdgesGeometry` + 细线，低透明度，帮助读出板/梁/墙的边界。
- 接触阴影：地面渐变贴图 + 建筑底部柔影，弥补阴影贴图在接触处的不足。
- 背景：浅灰蓝渐变与轻微暗角，不用纯色大平铺；不引入需要随机采样的 SSAO，避免同帧漂移与性能风险。
- 剖面：近景隐藏近侧墙时，保留楼板/梁/柱的截面边线，避免“被掏空”的观感。

### 7. 可读性层放在 SVG 覆盖层，不放进 WebGL

- 阶段轨：底部 7 段，当前段高亮，已完成段弱化；文字用 `M2V Sans`，字号按 1080p 设计，不随 3D 缩放。
- 构件名称：当前步骤的 `label`（如“框架柱”“框架梁”“楼板”“屋面板”）以引线指向所选构件的投影包围盒；同时最多两条，放在主体轮廓外，不压连接点。
- 幽灵轮廓：最终体量的 `LineSegments`，低不透明度，主体完成前可见，完工镜头淡出。
- 比例尺：3 m 标尺与“建造过程示意”小字，放在右下安全区；不遮挡主体。
- 标签位置由每帧的 3D 投影计算，包含简单的屏幕边界夹取；不做自动避让，避免不确定性。

### 8. 依赖与性能按外部方案调研结果处理

已评估的现成方案：`three` 0.186.1（MIT）、`@react-three/fiber` 9.8.2（MIT）、`@react-three/drei` 10.7.9（MIT）、`postprocessing` 3.2.2（MIT）均已在仓库中；`three-bvh-csg` 0.0.18（MIT，2026-02 发布）是维护中的 CSG 方案。本轮不新增依赖：墙洞用 `THREE.Shape` 的 holes + `ExtrudeGeometry`，剖切用 clipping plane，轮廓用 `EdgesGeometry`，接触阴影用程序化 Canvas 贴图。若后续需要复杂构件布尔，再按“来源、版本、许可、确定性”登记引入 `three-bvh-csg`。

性能目标：先按 1920×1080、shadow map 2048、像素比 1 渲染 1800 帧，记录渲染时长与内存；若单帧明显慢于可接受范围，优先把 shadow map 降到 1024、减少透明玻璃层，而不是降低画幅或帧率。

## Risks / Trade-offs

- [WebGL 同帧不一致] → 所有几何/材质在挂载时构建一次；每帧只由 `frame` 求变换与可见性；不使用 `Math.random`、挂钟、纹理动画或跨帧累积；用 `lookdev --det` 与正序/倒序探针 PSNR ≥ 60 dB 验证。
- [阴影贴图抖动/闪烁] → 固定灯光位置与 shadow camera 范围；构件移动时更新 shadow map；不逐帧改 shadow bias。
- [透明玻璃排序错误] → 玻璃使用低不透明度、`depthWrite: false` 并最后绘制；必要时改用半透明纯色而非 transmission。
- [标签遮挡] → 引线从构件包围盒外缘出发，标签夹取在安全区；每帧只显示当前步骤标签；代表帧逐张检查。
- [步骤/选择器写错] → Python 校验器在准备前展开 glob、检查覆盖与依赖；错误报告具体步骤与构件 ID。
- [v1 材料被拒绝导致现有作品不可用] → 首例材料同步重写为 v2；不保留兼容分支，错误信息给出字段级升级提示。
- [渲染时间上升] → 记录性能；必要时降 shadow map 与透明层；不牺牲镜头与建造动作。
- [独立评审仍认为不可读] → 按复述场景逐条修正镜头、步骤或标签；不以阶段标签和技术 QA 替代。

## Migration Plan

1. 写 v2 schema、材料校验与 init 模板，先让 v1 明确失败。
2. 重写 three.js 渲染器与标签/阶段轨层，保留 composition id 与输出名。
3. 把 `videos/building-construction/two-story-house` 的 `building.json`/`construction.json` 重写为 v2，重跑 validate/prepare/lookdev。
4. 更新类型指南、catalog 说明、README/PROJECT_PLAN 生成清单与测试。
5. 渲染 1800 帧，跑 QA、同帧确定性、代表帧与独立评审；按复述场景修正。
6. 检查暂存范围并提交；同步 OpenSpec 主规格并归档。

回滚：v2 与旧 v1 不兼容；若重制失败，恢复 v1 代码与材料需要回退整个提交。由于旧 v1 候选与 QA 已作废，不以旧成片冒充新首例。

## Open Questions

无。具体步骤数量、镜头角度与材质色值属于实施中的设计选择，不改变 v2 契约或验收场景。
