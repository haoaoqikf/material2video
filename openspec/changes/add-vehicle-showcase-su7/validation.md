# 实施验证与独立评审

- 上游固定 `alphardex/su7-replica@6d56d366059575c138dde72a1f15585ddd31fc09`；用户于 2026-10-31 确认代码与模型展示授权。
- 资产：仅 `sm_car.gltf`、`sm_car_data.bin`、`sm_car_img0..8.webp`；保存在忽略内容目录，清单记录来源/许可/SHA-256，不入库。
- Python/前端：`uv run pytest -q`、`pnpm --dir web test`、`typecheck`、`build` 通过；`openspec validate add-vehicle-showcase-su7 --strict` 通过。
- 首例：900 帧、1920×1080、30 fps、30.00 秒、无音轨；成片 SHA-256 `a7af1eb10104862a0395a879a0217e463364aba7dbcfd0eebb2467f325e4450d`。
- 重复取帧：同一 19–21 秒窗口两次导出 SHA-256 完全一致（`88f16d...`），视为该段 PSNR 无穷大/≥60 dB。
- 独立视觉评审：车身、车漆、玻璃、灯具、环绕视角无必改项；轮胎/轮拱和运动/车轮旋转列为静帧限制。
- 说明：为保持轮组几何位置，车轮使用轴心组旋转；模型轮拱阴影偏弱属于资产表现，不作为阻断。
