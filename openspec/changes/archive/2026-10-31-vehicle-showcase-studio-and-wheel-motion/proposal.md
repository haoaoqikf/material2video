## Why

首例 SU7 成片经过观感复核，暴露出三个必须修复的问题：

1. **车漆质感与参考网页差距过大**：现画面只使用 `RoomEnvironment` 和几盏方向光，车漆呈现为发白的青蓝色，缺少参考网页中的柔光棚 HDR 反射、车漆 AO 细节和辉光。
2. **背景不成立**：灰色金属地面配网格、远处可见地面边缘与光斑，像一个未完成的三维测试场景，而不是暗色影棚。
3. **车轮完全没有转动**：three.js 的 `GLTFLoader` 会用 `PropertyBinding.sanitizeNodeName` 把 glTF 节点名 `Wheel.001` 清洗为 `Wheel001`，现有代码按原名 `getObjectByName` 查找，永远找不到车轮，旋转逻辑从未生效。前次视觉评审把车轮旋转列为「静帧限制」，实际是未被发现的功能缺陷。

这次修复要同时达到参考网页的观感水平，并补上可验证的车轮运动，不能只调参数敷衍。

## What Changes

- **材料格式升级到 v2**：`showcase.json` 新增必填的 `studio` 对象，登记影棚环境图、车漆 AO、地面法线与粗糙度贴图；所有新增文件必须出现在 `manifest.json` 并记录来源、许可与 SHA-256，准备时内嵌为 data URI，渲染保持离线。v1 材料明确拒绝。
- **影棚画面**：使用参考仓库同一提交的 HDR 影棚环境图驱动 PBR 反射；增加顶部柔光板、暗色地面、平面反射（含法线扰动、粗糙度模糊与菲涅耳）、接触阴影与辉光；移除网格、灰色地面和地面边缘；亮灯显现、完整环绕、启动与视觉疾驰的时间轴保持不变。
- **车轮运动**：按 three.js 清洗后的节点名解析车轮，按本地 Z 轴旋转；环绕阶段静止，启动段加速，疾驰段高速旋转，收束段减速；角度由时间轴的解析积分给出，保持逐帧确定性且不产生频闪。
- **镜头与构图**：收紧环绕距离与 FOV，让车身在画面中占比接近参考网页；保持整圈完整可见。
- **文档、目录模板与测试**：同步类型目录、制作参考、OpenSpec 规格与测试；SU7 作品重新准备并渲染。

## Capabilities

### New Capabilities

### Modified Capabilities
- `vehicle-showcase`：材料 v2 的影棚资产契约、影棚灯光与反射地面、车轮旋转与确定性、首例观感验收。

## Impact

- 受影响代码：`src/m2v/types/vehicle_showcase/materials.py`、`src/m2v/types/catalog.json`、`web/src/compositions/VehicleShowcase.tsx`、`tests/test_vehicle_showcase.py`。
- 受影响材料：`videos/vehicle-showcase/su7/showcase.json`、`manifest.json` 与新增影棚资产（作品内容目录，不入 Git）。
- 受影响文档：`.agents/skills/material2video/references/vehicle-showcase-video.md`、`README.md`、`openspec/specs/vehicle-showcase/spec.md`。
- 渲染成本增加：每帧多一次平面反射与后期辉光；以短样片实测，不预设吞吐承诺。
- 不涉及其他视频类型；共享渲染管线不变。
