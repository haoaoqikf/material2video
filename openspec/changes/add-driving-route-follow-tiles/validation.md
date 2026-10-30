# 实施验证与独立评审

## 自动验证

- Python：`uv run pytest -q` 通过（含 driving 60 秒/16×、route v3 行政区、z12 走廊、卫星样式、旧版本拒绝）。
- 前端：`pnpm --dir web test` 157 项通过；`pnpm --dir web typecheck`、`pnpm --dir web build` 通过。
- 文档：`sync_docs.py --check` 通过；`openspec validate add-driving-route-follow-tiles --strict` 通过。
- 抖动：首例 16×/30fps 相机中心逐帧加速度 p95≈0.44 px/frame²、最大≈0.94 px/frame²；行政区标签固定上方并取整到整数像素，不再上下切换。

## 首例

- 道路版：1800 帧、1080×1920、30 fps、60.00 秒、无音轨；z12 走廊 1648 块，prepared 约 32.7 MB。
- 卫星版：同路线/同标签/同镜头，style=6 卫星瓦片，route service=satellite-tiles。
- 具体成片 SHA-256 与材料摘要见两版 `publish-notes.md`。

## 独立评审

- 视觉评审：道路/卫星两版静帧均无必改项；市/县同为 30 px，自绘层不出现区名，卫星标签清晰。运动抖动仅能由实际播放确认，静帧不代替。
- 代码评审：行政区取数两遍组装、凭据字段宽匹配、卫星样式/服务一致性、固定标签锚点、端点锚点等问题已修复。
