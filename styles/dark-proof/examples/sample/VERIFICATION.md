# 验证记录

## 当前状态

| 项目 | 命令或材料 | 结果 |
|---|---|---|
| 材料校验 | `uv run m2v validate --project styles/dark-proof/examples/sample` | 通过 |
| 准备 | `uv run m2v prepare --project styles/dark-proof/examples/sample` | 通过 |
| 风格注册 | `uv run m2v styles --json` | 返回 6 个包，含 `dark-proof` 1.2.0 |
| 通用原语 | `pnpm -C web exec vitest run src/code-scene/dynamics.test.ts src/code-scene/rhythm.test.ts src/code-scene/primitives.test.ts src/code-scene/subtitles.test.ts src/code-scene/motion-components/motion-components.test.tsx` | 54 项通过 |
| 类型检查 | `pnpm -C web exec tsc --noEmit` | 通过 |
| 默认测试 | `uv run pytest` | 通过（仅 4 项按既有条件跳过） |
| 交付前回归 | `uv run pytest -m "not slow"` | 通过 |
| 风格包测试 | `uv run pytest tests/works/examples/test_dark_proof_style.py` | 通过（含 slow 场景构建） |
| 代表帧 | `lookdev --sheet 1 6.5 13.5 20.0 25.8 40.7 48.4 53.2 55.8 57.4` | 已核对八拍、四个整屏冲击、字幕与取样窗 |
| 转场边界 | `lookdev --sheet 5.6 5.8 6.0 6.2`、`12.7 12.8 12.9`、`50.8 51.0 51.2` | 旧层快速退出、新层稍后进入，无长时间双重曝光 |
| 唯一硬切 | `lookdev --sheet 19.9 20.0 20.1` | 通过：19.9 秒仍是四列，20.0 秒为三点空场，20.1 秒出现单环 |
| 同帧确定性 | `lookdev --det` | 通过：采样帧两次采集一致（psnr 为 null 或 100.05） |
| 粒子性能 | `lookdev --still-scale 2` 采集三个冲击帧 | 3 帧约 74 秒，画布像素检查通过；正式渲染 1 倍采集 |
| 声音生成 | `assets/synthesize.py` 与 `assets/recipe.json` 摘要 | 通过：9 项摘要、采样率、声道与时长一致 |
| 配乐节奏 | 对母版做频谱通量/类起音分析 | 频谱通量 0.30、类起音约 2.8/秒（参考 0.37 / 2.06） |
| 分镜机械规则 | `uv run pytest tests/types/general/test_storyboard_copy.py` | 通过 |
| 完整渲染 | `uv run m2v render --project ...` | 通过：58 秒 / 1740 帧 / 1920×1080 / 30 fps；渲染 341.9 秒、总计 594.3 秒 |
| 技术 QA | `uv run m2v qa --project ...` | 通过：frozenFrames、picture、subtitleContrast、loudness、audioSync、claims |
| 响度 | `m2v qa` 输出 | −14.9 LUFS / 真峰值 −1.2 dBFS（目标 −14 ±2 LU，真峰值 ≤ −1） |
| 字幕安全区 | 屏幕字幕组件只使用 `subtitleSafeArea`，粒子层底部淡出 | 通过（代码检查与代表帧） |
| 参考风格材料 | `outputs/style-reference.md`、并排图、2 秒样片、冷审记录 | 待最终候选重做 |

## 本次修复

| 问题 | 处理 | 核对 |
|---|---|---|
| 光效不够大 | `explosionField` 用 `reach` 表示实际位移，四层粒子 + bokeh/streak；四个整屏冲击（738/1194/1440/1580），冲击期间压暗点阵；局部 `burst` 的 `drag` 从 4 降到 1.2 | 25.8、40.7、48.4、53.2 秒代表帧可见覆盖大半个画面的粒子与扩散环 |
| 节奏不够紧 | 段内 12–16 个微拍、点阵 warp、SE/回归/结尾扫描光点、金点与关键词 112 BPM 脉冲、全片 8% 单向推近；58 秒 112 BPM 原创 score | 频谱通量 0.30、类起音约 2.8/秒；代表帧事件密度提升；完整视频指标见下 |
| 整屏冲击遮挡文字 | 透明 Canvas 放在 SVG 主体之下，底部安全区 alpha 淡出，冲击期间点阵压暗 | 字幕窗口内侧帧与 `qa` 字幕对比度通过 |
| 声音没有人声 | 不加旁白；用低频 kick、反拍 tick、hat build、和声垫、riser/impact 的 112 BPM score 补节奏 | 母版响度与 audioSync 通过 |

## 最终量化对照

以下用与调研相同的只读脚本（15 fps、480×270 解码）测量；参考值来自同一脚本。

| 指标 | 参考片 | 本轮目标 | 本轮实际 | 结论 |
|---|---:|---:|---:|---|
| 明显变化事件 | 5.47/10s | ≥3/10s | **1.89/10s（11 次）** | 比上一版 1.20 提升，仍未达目标 |
| 近静止秒数（diff<0.0005） | 8% | <20% | **37.9%** | 比上一版 54% 明显下降，仍高于目标 |
| 平均帧差 | 0.0081 | ≥0.0025 | **0.0023** | 接近目标，为上一版 0.0008 的约 2.9 倍 |
| 金色像素峰值（15 fps 全片） | 14.0% | ≥5% | **2.33%** | 采样错过 25.8 秒峰值；同帧 1920×1080 实测 12.08%，与参考实体金条同一量级 |
| 亮部像素峰值（15 fps 全片） | 15.0% | ≥6% | **3.73%** | 参考峰值来自大面积实体柱；粒子帧本身是金色而非白色亮部 |
| 音频频谱通量 | 0.37 | ≥0.15 | **0.30** | 达到目标，为上一版 0.06 的 5 倍 |
| 类起音 | 2.06/s | ≥0.8/s | **约 2.8/s** | 达到目标 |
| 最长主内容停留 | — | ≤1.5s | S7 1.87s 由 formula 冲击覆盖，其余主要停留 ≤1.1s | 基本达到 |

差距说明：参考片的金色/亮部峰值来自大面积实体柱与整块金色横条，本片峰值来自粒子云；25.8 秒同帧金色面积 12.08%，与参考实体金条同一量级。明显变化事件与近静止秒数仍低于参考，说明画面仍有可感知的停顿；本轮用 112 BPM 配乐、扫描光点与点阵波动补偿，但未完全追平。

## 已知限制

- 整屏冲击使用 Canvas 2D 粒子层；2 倍采集下三帧约 74 秒，正式渲染仍为 1 倍采集。
- 全片缓慢推近 8%，字幕与方法说明不缩放；标题与图表按推近后位置核对不裁切。
- 收尾 finale 粒子在 57 秒后逐渐收拢，57.4–58 秒以点阵、片名与微脉冲收束。
- 本记录只证明技术链路和画面核对，不替代独立评审与观众理解观察。
