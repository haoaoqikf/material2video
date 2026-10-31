## Why

上海到郑州成片中的市县标签在跟随镜头中频繁闪烁，之前的相机平滑没有解决标签自身每帧重算避让造成的硬切换。需要让标签在移动镜头下连续出现和消失，并以整段路线帧序列验证。

## What Changes

- 为行政区标签的碰撞避让增加连续可见性过渡，避免碰撞阈值附近逐帧闪烁。
- 固定标签间的优先级与布局决策，并增加整段帧序列的标签稳定性验证。

## Capabilities

### New Capabilities

### Modified Capabilities
- `driving-route-video`: 跟随过程的行政区标签在碰撞、视口边缘及遮挡变化时须平滑显隐，不因逐帧硬阈值跳变。

## Impact

- 影响 `web/src/compositions/DrivingRoute.tsx` 及其测试、driving-route 视觉契约与 OpenSpec 规格。
- 不改变材料格式、数据来源、标签字体或镜头运动。
