# 汽车展示视频专题

本文定义 `vehicle-showcase` 类型的材料与画面契约；行为以 [OpenSpec 规格](../../../../openspec/changes/add-vehicle-showcase-su7/specs/vehicle-showcase/spec.md) 为准。

## 材料

- `showcase.json`（v1）：固定 1920×1080、30 fps、时长、模型相对路径、车轮节点名、镜头与疾驰效果时间。
- `manifest.json`（v1）：本地 glTF、二进制与贴图清单，逐项记录来源、上游提交、许可依据、路径与 SHA-256。
- 模型及其依赖只放在作品忽略内容目录；准备时把 glTF 的 buffer/image 内嵌为 data URI，渲染离线运行。

## 命令

```powershell
uv run m2v init --type vehicle-showcase --project <slug>
uv run m2v validate --project videos/vehicle-showcase/<slug>
uv run m2v prepare --project videos/vehicle-showcase/<slug>
uv run m2v preview --project videos/vehicle-showcase/<slug> --start-seconds 0 --end-seconds 4
uv run m2v render --project videos/vehicle-showcase/<slug>
```

## 画面与边界

- 30 秒、1920×1080、30 fps、无声；暗色展厅、亮灯显现、完整环绕、启动与视觉疾驰。
- 所有镜头、车轮角度、流光与抖动按帧求值；不依赖交互、挂钟或上一帧。
- 视觉疾驰不是真实道路驾驶；不宣称车辆性能或真实运动。
- 首例 SU7 资产必须来自已核实授权的 `alphardex/su7-replica` 固定提交；授权未落实时不得导入或发布。
