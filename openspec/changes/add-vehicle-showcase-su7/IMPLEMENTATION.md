# 实施记录（2026-10-31）

- 用户于 2026-10-31 确认已获得 `alphardex/su7-replica` 代码与模型的展示使用授权；上游固定提交 `6d56d366059575c138dde72a1f15585ddd31fc09`。
- 仅使用 `sm_car.gltf`、`sm_car_data.bin` 与 `sm_car_img0..8.webp`；未使用原 BGM、芙宁娜角色或其他未授权资源。
- 资产放在忽略内容目录 `videos/vehicle-showcase/su7/assets/`，清单记录来源、提交、许可说明与 SHA-256；未入库。
- 首例：30 秒、900 帧、1920×1080、30 fps、无音轨，成片 SHA-256 `a7af1eb10104862a0395a879a0217e463364aba7dbcfd0eebb2467f325e4450d`。
- 模型通过 glTF 内嵌（buffer/image data URI）离线加载，Meshopt 解码；镜头、车轮、流光和轻微抖动按帧求值。
