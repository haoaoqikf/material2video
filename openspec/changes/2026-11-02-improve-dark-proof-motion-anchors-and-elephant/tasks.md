## 1. 规则与外部选型

- [x] 1.1 在 `AGENTS.md` 增加「动效与组件先调研外部方案」规则，并在 skill 的 `code-scene-runtime.md` 引用；验证两份文档均包含检索要求与违规判定。
- [x] 1.2 记录 `svg-path-properties`、`perfect-freehand`、Lucide Lab 的引入理由，以及 `@remotion/motion-blur`、`tsparticles`、`reveal-text`、`roughjs`、`flubber` 的拒绝理由；验证 `design.md` 与示例 `SOURCES.md` 均含选型表或许可说明。
- [x] 1.3 在 `web/package.json` 固定 `svg-path-properties@2.2.0` 与 `perfect-freehand@1.2.3`，确认许可为 MIT 并提交锁文件；验证 `pnpm -C web exec tsc --noEmit`。

## 2. 通用原语

- [x] 2.1 新增 `web/src/code-scene/random.ts`、`dynamics.ts`、`subtitles.ts`：固定种子、路径采样、光轨、爆散、扩散环、互补溶解、逐字错峰、字幕窗口与两行切分；验证 `pnpm -C web exec vitest run src/code-scene/dynamics.test.ts src/code-scene/subtitles.test.ts src/code-scene/primitives.test.ts`。
- [x] 2.2 在 `sdk.tsx` 导出新模块与两个第三方纯函数，不整包 `export *`；验证 `tests/common/test_motion_primitives.py` 的导出与源码闸门断言。
- [x] 2.3 覆盖重复求值、跳帧、种子、端点透明、环半径单调、字幕窗口与错峰步长；38 项 Vitest 通过，`tsc --noEmit` 通过。

## 3. 风格组件

- [x] 3.1 新增 `light-trail.tsx`、`burst.tsx`、`shock-ring.tsx`，只接收几何、进度、强度、种子与颜色；验证 `styles/dark-proof/style.json` 登记三项、版本 1.1.0。
- [x] 3.2 升级 `screen-subtitle.tsx`（逐字展开、英文延迟、关键词高亮、三种进出场）、`counter.tsx`（残影）与 `hand-drawn-line.tsx`（锥形笔触）；验证未轮到的字全透明、英文在延迟前不可见。
- [x] 3.3 扩充 `tokens.json` 的 `light` 与 `subtitleMotion`，更新 `GUIDE.md` 的光效边界、字幕进出与转场规则；验证 `uv run pytest tests/works/examples/test_dark_proof_style.py -q`。

## 4. 示例

- [x] 4.1 把八段整层 opacity 叠放改为 `FieldAnchor`、`GoldAnchor`、`LightEvents` 持续层；金点在圆片顶、样本点、趋势点、取样窗与标准误标记之间交接；600 帧仍为唯一硬切。
- [x] 4.2 局部层旧层 14 帧快速退出、新层晚 2 帧进入，整段 16 帧；验证 5.6–6.3 秒、12.7–12.9 秒、50.8–51.2 秒帧序列无双重曝光。
- [x] 4.3 加入轨迹光轨、评价翻转小爆散、线溶解/全象揭示/n=1000/结尾爆散与扩散环；验证 25.2 秒、45.2 秒、53.2 秒可见粒子与环，600 帧只有单环。
- [x] 4.4 大象改用 Lucide Lab 路径并补象牙、眼与分批生长；三个取样窗改为同一几何的 `<use>` + `clipPath` 局部放大，引线指向真实部位；验证 37 秒、39 秒、40 秒代表帧可指出耳、头、鼻、腿、牙、眼。
- [x] 4.5 同步 `DESIGN.md`、`SOURCES.md`、`GUIDE.md`、`docs/PROJECT_PLAN.md` 与 `styles/README.md`；验证相对链接、版本号与组件清单一致。

## 5. 验证与证据

- [x] 5.1 运行 `uv run pytest`、`uv run pytest -m "not slow"` 与相关 slow 用例；记录通过/失败数量。
- [x] 5.2 重新渲染代表帧、边界帧与 `--det` 同帧一致性；核对字幕逐字展开、英文延迟、关键词高亮、光效与取样窗。
- [x] 5.3 全片 `uv run m2v render` 与 `uv run m2v qa`；检查响度约 −14 LUFS / ≤−1 dBTP，`outputs/` 不入库。
- [x] 5.4 重做 `outputs/style-reference.md`、并排图与 2 秒样片，删除旧「平涂无光晕」结论；由独立子代理冷审新图与样片并记录差异项。
- [ ] 5.5 检查 Git 暂存范围，提交实施；同步 `openspec/specs/` 主规格并把变更移入 `openspec/changes/archive/`，再提交归档结果。
