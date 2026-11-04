# 《接》示例

`dark-proof` 风格包的规范示例：一条 60 秒、1920×1080、30 fps、无旁白的复利讲解短片。它只问一件事：**把上一次的结果接回下一次的起点，会发生什么？**

## 看完会发生什么

- 10 场对应 10 种说明方式：物理因果、时间跳切、数字滚动、定义回环、二叉分叉、尺度与曲线、对照实验、网络、棋盘传说、总和收束。
- 第一刀 8 毫米；第 100 天的水滴；100 刀与第 37 刀的滑刃；复利的三个条件；每层翻倍的 64 个叶节点。
- 一张纸对折 42 次是 439,804.65 公里，线性叠 42 张只有 4.2 毫米；40.9 秒有全片唯一一次硬切，从两堆纸切到同一张 100 节点网络。
- 网络先有前 10 个概念的 45 条连接，最后 10 个接入前 90 个再新增 945 条，是 21 倍；100 个概念共 4,950 条。
- 棋盘第 64 格是 2^63 粒；结尾由 4,950 条弦随 99→4,950 的计数画出“接”，再落片名。
- 配乐为 112 BPM 原创程序化 score，11 个声音资产全部由 `assets/synthesize.py` 生成。

## 重建

```powershell
uv run python styles/dark-proof/examples/compound-connect/assets/fetch.py
uv run m2v validate --project styles/dark-proof/examples/compound-connect
uv run m2v prepare --project styles/dark-proof/examples/compound-connect
uv run m2v lookdev --project styles/dark-proof/examples/compound-connect --sheet 2 6.2 14 20 25.8 36 41 47 52 59
uv run m2v render --project styles/dark-proof/examples/compound-connect
uv run m2v qa --project styles/dark-proof/examples/compound-connect
```

声音由 `assets/synthesize.py` 确定性生成，按 `assets/recipe.json` 校验摘要、采样率、声道与时长；生成媒体写入 `assets/media/` 与 `outputs/`，都不进入版本控制。

## 材料

- `storyboard.json`：v8 单幕分镜、1800 帧、11 条中英双语屏幕字幕、30 个事件与声音绑定。
- `scenes/compound-connect.tsx`：全部画面、几何与数学；不读取外部参考素材。
- 指数公式通过 `m2v/code-scene/math` 使用 KaTeX，并在 `ready()` 前等待公式字体；依赖安装后运行 `uv run python fonts/fetch.py` 恢复登记字体。图表曲线复用共享 D3 几何，接口见[表达组件](../../../../.agents/skills/material2video/references/visual-components.md)。
- `scenes/geometry.ts`、`motion.tsx`、`handoff.tsx`：本片共用的几何、逐帧运动与页面交接物。
- `DESIGN.md`：10 场时间表、数学口径、唯一硬切、参考拆解与机器合同。
- `SOURCES.md`：参考片、字体与声音来源边界。
- `SOUND.md`：声音角色、事件与混音约定。
- `VERIFICATION.md`：本示例实际执行的验证与已知限制。
- `HOWTO.md`：一个可复现的调时练习。

参考片只作为拆解与并排基准，画面、音轨、字幕与文案均不进入本示例。
