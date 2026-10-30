# 实施验证与独立评审

- 类型材料：`building.json`、`construction.json`、`manifest.json` v1；范围、洞口、ID/阶段/资产校验与准备指纹已实现。
- 首例：两层框架住宅程序化等轴测，40 秒、1200 帧、1920×1080、30 fps、无音轨；成片 SHA-256 `cc4a67a7bc1f13711b27bbe3f50f69cdb3a71666325985193c6041b8857dcbf0`。
- 自动验证：`uv run pytest -q`、`pnpm --dir web test`、`typecheck`、`build`、`sync_docs.py --check`、`openspec validate ... --strict` 通过。
- 确定性：同一 10–11 秒窗口两次导出 SHA-256 完全一致（`a60a007e...`），PSNR 视为无穷大/≥60 dB。
- 独立视觉评审：首轮指出右侧悬空梁、庭院越界、楼梯悬空三项必改；修复后按 f-16/f-22/f-29/f-39.9 复查，三项均关闭，无新增必改项。
- 静帧限制：镜头运动、构件弹入衔接与手机尺寸观感未由静帧完全证明。
