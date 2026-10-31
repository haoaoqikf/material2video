# 实施记录（2026-10-31）

## 问题定位

- 车轮不动的根因不是参数，而是 three.js `GLTFLoader` 用 `PropertyBinding.sanitizeNodeName` 把 glTF 节点名 `Wheel.001` 清洗为 `Wheel001`；原实现按原名 `getObjectByName` 查找，永远返回 `undefined`，旋转分支从未执行。
- 车漆与背景差距来自渲染方案：原实现只有 `RoomEnvironment`、方向光和灰色网格地面，缺少参考仓库的 HDR 影棚环境、车漆 AO、平面反射、柔光板与辉光。

## 材料与资产

- `showcase.json` 升到 v2，新增必填 `studio`：`environment`、`bodyAo`、`floorNormal`、`floorRoughness`。
- 新增四张影棚资产，取自 `alphardex/su7-replica@6d56d366059575c138dde72a1f15585ddd31fc09` 的 `public/texture/`，保存在作品忽略内容目录并在 `manifest.json` 登记来源、许可与 SHA-256：
  - `t_env_light.hdr` → `assets/studio/env_light.hdr`
  - `t_car_body_AO.raw.jpg` → `assets/studio/car_body_ao.jpg`
  - `t_floor_normal.webp` → `assets/studio/floor_normal.webp`
  - `t_floor_roughness.webp` → `assets/studio/floor_roughness.webp`
- 准备阶段把 glTF 依赖和四张影棚贴图内嵌为 data URI，渲染离线；v1 材料明确拒绝。

## 画面实现

- HDR 环境图经 `PMREMGenerator` 预滤波后作为 `scene.environment`，按帧调节 `scene.environmentIntensity` 完成亮灯显现与疾驰增强。
- 顶部圆形白色柔光板（中心亮、边缘渐隐，`toneMapped: false`）提供可见光源；地面为暗色圆盘（`#6f7c82`），使用镜像相机 + 斜裁剪把场景渲染到 960×540 反射目标，再由自定义着色器按法线扰动、模糊、菲涅耳、距离衰减与有序抖动合成；接触阴影中心加深，并增加前后轴两条紧致的车轮接触阴影。
- 车底椭圆接触阴影、微弱半球光补车下沿；`postprocessing` 的 `BloomEffect` 让灯板、尾灯与高光发光。
- 移除网格、灰色测试地面与可见地面边缘；背景为纯黑。
- 车漆改为深青底色 `#007a7a` 的 `MeshPhysicalMaterial`，加清漆层（`clearcoat: 0.6`、`clearcoatRoughness: 0.12`）并单独绑定 HDR 环境（逐帧按亮灯强度使用 `envMapIntensity` 2.2）；另加一盏顶部大面积 `RectAreaLight`（6.5×3.2、强度 0.45、冷白偏青）提供柔和高光带。后期在辉光后加 `HueSaturationEffect`（saturation +0.12）把车漆饱和度校到参考的深青水平。玻璃压暗到 `#05080a`、不透明度 0.45、反射强度 3.0；渲染使用 Cineon 色调映射。车漆 AO 使用 `channel = 1` 的线性过滤。
- 车轮按原名或清洗后名称解析，直接旋转节点自身 Z 轴；角度为分段线性速度轨道的解析积分：0–16 s 静止，16–19 s 加速至 4.5 rad/s，19–26 s 升至 13.5 rad/s，26–30 s 减速。30 fps 下最大约 0.45 rad/帧，低于五辐轮毂对称周期。
- 镜头：侧视角与前后视角按视角收放距离（`distance × (0.8 + 0.2·|sin(angle)|)`），保持主体占比；相机高度 0.9、侧视距离 7.05、FOV 34。开场用连续 `push = 1 - smooth(t/4)` 从远处推近并在 4 秒处无缝接入环绕，修复旧实现 4.0 秒一帧跳变；加速段加入 3° 缓慢环绕与 0.1 推近，26 秒车尾仍保留画面内边距。
- 所有状态均为 `frame / fps` 的纯函数，反射目标每帧重渲染，不跨帧累积。

## 变更文件

- `src/m2v/types/vehicle_showcase/materials.py`、`src/m2v/types/catalog.json`
- `web/src/compositions/VehicleShowcase.tsx`
- `tests/test_vehicle_showcase.py`
- `.agents/skills/material2video/references/vehicle-showcase-video.md`
- `videos/vehicle-showcase/su7/showcase.json`、`manifest.json` 与 `assets/studio/`（作品内容，不入 Git）
