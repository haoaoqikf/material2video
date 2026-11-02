# 《样本》示例

`dark-proof` 风格包的规范示例：一条 58 秒、1920×1080、30 fps、无旁白的数学讲解短片。它只问一件事：**你看到的是样本，还是总体？**

## 看完会发生什么

- 开场给出 3 条评价，再拉出 1000 个样本，让 3/1000 = 0.3% 同屏可见。
- 每次翻转一条评价，3 条评价的均值摆动约 33 点。
- 样本量从 3 增到 1000，均值误差（标准误）约缩小 18 倍；误差减半需要样本量翻四倍。
- 20.0 秒有全片唯一一次硬切：从“样本量四列”切到“三个点连成一条线”的空场，随后 1000 个点浮现、线溶解。
- 用均值回归与“盲人摸象”说明：局部样本可以是真，整体结论仍可能不成立。
- 结尾回到 1000 点阵中的 3 个金点，不新增概念。

## 重建

```powershell
uv run python styles/dark-proof/examples/sample/assets/fetch.py
uv run m2v validate --project styles/dark-proof/examples/sample
uv run m2v prepare --project styles/dark-proof/examples/sample
uv run m2v lookdev --project styles/dark-proof/examples/sample --sheet 6 13 20 24 28 35 43 51 57.9
uv run m2v render --project styles/dark-proof/examples/sample
uv run m2v qa --project styles/dark-proof/examples/sample
```

声音由 `assets/synthesize.py` 确定性生成，按 `assets/recipe.json` 校验摘要、采样率、声道与时长；生成媒体写入 `assets/media/` 与 `outputs/`，都不进入版本控制。

## 材料

- `storyboard.json`：v8 单幕分镜、13 条中英双语屏幕字幕与 10 个声音事件。
- `scenes/sample.tsx`：全部画面、几何与数学；不读取外部参考素材。
- `DESIGN.md`：八拍时间表、数学口径、唯一硬切与参考拆解。
- `SOURCES.md`：参考片、字体与声音来源边界。
- `VERIFICATION.md`：本示例实际执行的验证与已知限制。
- `HOWTO.md`：一个可复现的调时练习。

参考片只作为拆解与并排基准，画面、音轨、字幕与文案均不进入本示例。
