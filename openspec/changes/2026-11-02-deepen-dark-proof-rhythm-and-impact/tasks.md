## 1. 通用原语与效果层

- [x] 1.1 在 `dynamics.ts` 新增 `explosionField`、`moteField`、`impactEnvelope`，在 `rhythm.ts` 新增 `beatPhase`/`beatPulse`；验证端点透明、同种子同形态、跳帧一致。
- [x] 1.2 新增 `effects/screen-burst.tsx`：透明 Canvas、captureScale、预渲染 sprite、加法混合、字幕安全区遮罩；SDK 导出。
- [x] 1.3 新增强化测试：`dynamics.test.ts`、`rhythm.test.ts`；`tests/common/test_motion_primitives.py` 纳入指纹、源码闸门与 SDK 导出断言。
- [x] 1.4 在 1920×1080 / captureScale=2 下采集三个冲击帧，3 帧约 74 秒，画布像素检查通过；正式渲染 1 倍采集，渲染 341.9 秒、总计 594.3 秒。

## 2. 风格层

- [x] 2.1 新增 `impact.tsx` 与四个 preset；`style.json` 登记 `impact`，版本升 1.2.0。
- [x] 2.2 tokens 增加 `impact`、`dust`、`type.heroLarge`、`motion.bpm/pushScale`；`burst.tsx` 的 `drag` 降到 1.2。
- [x] 2.3 更新 `screen-subtitle` 关键词节拍脉冲；更新风格测试的组件集合、版本与 tokens 断言。
- [x] 2.4 更新 `GUIDE.md` 并核对组件表、光效边界、推近与微拍规则（已改，待复查）。

## 3. 示例

- [x] 3.1 场景加入 `Impact` 四事件、微事件、金点/关键词脉冲、点阵漂移与 8% 缓慢推近；冲击期间压暗点阵。
- [x] 3.2 保留八拍边界、13 条字幕、10 个检查点与 600 帧唯一硬切；只改拍内动画与事件。
- [x] 3.3 storyboard 新增 `line-shatter`、`elephant-reveal`、`formula-impact` 事件与撞击音；保持 9 个音频资产 ID。
- [x] 3.4 重写 `synthesize.py` 的 58 秒 112 BPM score，更新 `recipe.json` 摘要；分析频谱通量/类起音。
- [x] 3.5 更新 `DESIGN.md`、`SOUND.md`、`SOURCES.md`、README、PROJECT_PLAN 与风格 README，核对链接、版本与声音表。

## 4. 验证与证据

- [x] 4.1 运行 `vitest`、`tsc --noEmit`、`uv run pytest`、`uv run pytest -m "not slow"` 与 dark-proof slow 用例。
- [x] 4.2 代表帧、四个冲击、硬切、转场与字幕边界逐张核对；`lookdev --det` 通过。
- [x] 4.3 全片 `prepare`/`render`/`qa`；响度 −14 ±2 LUFS / ≤−1 dBTP；记录渲染时长与粒子层性能。
- [x] 4.4 量化对照：明显变化 ≥3/10s、近静止 <20%、平均帧差 ≥0.0025、金色峰值 ≥5%、亮部峰值 ≥6%、频谱通量 ≥0.15、类起音 ≥0.8/s、最长主内容停留 ≤1.5s。
- [x] 4.5 重做并排图、2 秒样片、`style-reference.md` 与 `visual-notes.md`；独立子代理冷审。
- [ ] 4.6 检查 Git 暂存范围，提交实施；同步主规格、归档变更并提交归档结果。
