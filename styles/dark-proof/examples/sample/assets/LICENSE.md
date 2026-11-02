# 原创声音许可

`assets/synthesize.py` 生成的环境床（`bed.wav`）与事件音（`swing.wav`、`impact.wav`、`scratch.wav`、`dissolve.wav`、`regress.wav`、`anchor.wav`、`formula.wav`、`finale.wav`）由 material2video contributors 原创合成，不含第三方采样，按 CC0-1.0 发布。

- `bed.wav` 为 58 秒无旋律持续纹理：0.4–3.0 秒轻入，20 秒硬切处短暂收窄，43–51 秒略抬，53.5–58 秒收束。它属于环境床，不是配乐。
- 事件音为确定性的短音；`impact.wav` 是硬切处的低频撞击，`dissolve.wav` 是线的权威被撤走时的空气层。
- 文件摘要、采样率、声道与时长由 `recipe.json` 固定；`fetch.py` 只恢复并核验，不接受摘要漂移，也不覆盖已有不同文件。
