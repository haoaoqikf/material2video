# 验证记录

## 当前状态

| 项目 | 命令或材料 | 结果 |
|---|---|---|
| 材料校验 | `uv run m2v validate --project styles/dark-proof/examples/sample` | 通过 |
| 准备 | `uv run m2v prepare --project styles/dark-proof/examples/sample` | 通过 |
| 风格注册 | `uv run m2v styles --json` | 返回 6 个包，含 `dark-proof` 1.1.0 |
| 通用原语 | `pnpm -C web exec vitest run src/code-scene/dynamics.test.ts src/code-scene/subtitles.test.ts src/code-scene/primitives.test.ts` | 38 项通过 |
| 类型检查 | `pnpm -C web exec tsc --noEmit` | 通过 |
| 默认测试 | `uv run pytest` | 通过（仅 4 项按既有条件跳过） |
| 交付前回归 | `uv run pytest -m "not slow"` | 通过 |
| 风格包测试 | `uv run pytest tests/works/examples/test_dark_proof_style.py` | 通过（含 slow 场景构建） |
| 代表帧 | `lookdev --sheet 2.6 7 13.5 20.0 21.5 25.2 31.5 35.5 39 40.5 45.2 53.2 57.5` | 已核对八拍、光效、字幕与取样窗 |
| 转场边界 | `lookdev --sheet 5.6 5.8 6.0 6.2`、`12.7 12.8 12.9`、`50.8 51.0 51.2` | 旧层快速退出、新层稍后进入，无长时间双重曝光 |
| 唯一硬切 | `lookdev --sheet 19.9 20.0 20.1` | 通过：19.9 秒仍是四列，20.0 秒为三点空场，20.1 秒出现单环 |
| 同帧确定性 | `lookdev --det` | 通过：采样帧两次采集一致（部分 psnr 为 null，其余 100.05） |
| 声音生成 | `assets/fetch.py` 与 `assets/recipe.json` 摘要 | 通过：9 项摘要、采样率、声道与时长一致 |
| 分镜机械规则 | `uv run pytest tests/types/general/test_storyboard_copy.py` | 通过 |
| 完整渲染 | `uv run m2v render --project ...` | 通过：58 秒 / 1740 帧 / 1920×1080 / 30 fps |
| 技术 QA | `uv run m2v qa --project ...` | 通过：frozenFrames、picture、subtitleContrast、loudness、audioSync、claims |
| 响度 | `m2v qa` 输出 | −13.6 LUFS / 真峰值 −3.1 dBFS（目标 −14 ±2 LU，真峰值 ≤ −1） |
| 字幕安全区 | 屏幕字幕组件只使用 `subtitleSafeArea` | 通过（代码检查与合同量测规则） |
| 参考风格材料 | `outputs/style-reference.md`、三张并排图、2 秒样片、冷审记录 | 材料齐全；冷审结论见 `outputs/visual-notes.md` |

## 本次修复的四项

| 问题 | 处理 | 核对 |
|---|---|---|
| 轨迹与爆散没有光效 | 新增通用 `sampleTrail`/`burstField`/`expandingRings` 与 `light-trail`/`burst`/`shock-ring`；金点交接、趋势线、回归箭头、SE 曲线与评价翻转带上光轨或爆散 | 22.4、25.2、45.2、53.2 秒代表帧可看到头部光晕、粒子与扩散环 |
| 字幕进出没有效果 | 中文逐字展开（未轮到的字全透明）、英文延迟、关键词高亮、三类进场与三类出场 | 6.35–6.67 秒连续帧：先出现前几个字，英文不可见，随后整句与英文依次进入 |
| 转场像硬切/重影 | 1000 点阵与 3 个金点跨拍保留；旧层 14 帧快速退出、新层晚 2 帧进入；600 帧仍为唯一硬切 | 5.6–6.2、12.7–12.9、50.8–51.2 秒帧序列；`--det` 通过 |
| 大象不像大象 | 改用 Lucide Lab `elephant` 路径（ISC），补象牙与眼；耳/身体/腿/卷鼻分批生长；三个取样窗是同一轮廓的真实局部放大 | 37、39、40、40.5 秒代表帧可指出头、卷鼻、耳、眼、四腿与象牙；窗内是同一几何的放大 |

## 已知限制

- `lookdev --sheet 58` 会被拒（成片时长 0–57.967 秒）；末尾代表帧使用 57.5 秒。
- 代表帧按八拍起点取；拍内中段的并排基准另见 `outputs/style-reference/`。
- 方法说明是右下角小字（22/20 px）；393 宽下作为次级信息，主体数字与中文结论仍可辨。
- 收尾静止约 1 秒；`frozenFrames` 本次未报重复对，仍保留为观察项。
- 三个取样窗的引线在象身之后绘制，只在空场露出；窗口内是局部放大而非独立纹理，手机上仍需靠标签与位置识别。
- 本记录只证明技术链路和画面核对，不替代独立评审与观众理解观察。
