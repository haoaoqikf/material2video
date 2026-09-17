# 任务：把假的弹簧换成真的

## 1. 立住物理曲线

- [x] 1.1 vendored 阻尼谐振子的位置闭式解到 `assets/vendor/spring.js`（wobble 1.5.1 · MIT），
      文件头写明出处、许可证、4 处刻意改动与「为什么选闭式解而不是积分」；
      许可证全文放同目录 `vendor/wobble-LICENSE`。
- [x] 1.2 导出 `position(seconds, response, dampingFraction)` 与
      `restSeconds(response, dampingFraction, band)`（包络解出的收敛时刻）。
- [x] 1.3 修掉实现时写反的初始位移（`x₀ = -1` → `+1`）：写反会让入场从相反方向进来，
      实测位移 −14.43px 而不是 +14.4px。

## 2. 把运行时接到物理参数上

- [x] 2.1 `spring(seconds, { response, dampingFraction })`：读物理参数、秒数为负或 0 时返回 0、
      到收敛时刻返回确切的 1、读不到求解器时抛错并说明引入顺序。
- [x] 2.2 新增 `since(localFrame, startFrame)`（帧 → 秒，起点前夹到 0），
      挂到 `api` 与 `A2V` 两处导出上。
- [x] 2.3 `RECIPES` 的 `springDamping` / `springFrequency` 换成
      `springResponse` / `springDampingFraction`；`SPRINGS` 四档按「`response` 只决定快慢、
      ζ 只决定过冲」重排，并把等价的旧值写进注释备查。
- [x] 2.4 `enterRecipe` / `enterAlive` / `enterSvg` / `springBy` 的参数语义改成秒，
      JSDoc 写明「弹簧本身就是曲线，喂缓动过的进度会让它的自然周期失去意义」。
- [x] 2.5 `motion.springs()` 的快照键跟着改成 `response` / `dampingFraction`。

## 3. 组件侧迁移

- [x] 3.1 `figures.js` 的 23 处调用点从 `api.progress(f, start, dur, EASE)` 改成
      `api.since(f, start)`（用配平括号的脚本改，正则改法会把 `beat(state, 0.03)` 拆坏）。
- [x] 3.2 三处手工改写：`balance` 的横梁（`beamP` 仍要给描边用，另取秒数）、
      动作条（`actionP` 仍要给不透明度用）、数字组件（`progress` 仍要给数数用）。
- [x] 3.3 `declarative.html`、`examples/why-effort-fails/index.html`、
      `videos/never-fear-interviews/index.html` 在 `timeline.js` **之前**引入 `vendor/spring.js`。
- [x] 3.4 直接由 `api.progress` 写出的不透明度（如 `beamP`）保持不动，
      把这一轮的视觉差异限制在真正坏掉的那部分。

## 4. 机检

- [x] 4.1 `tests/test_motion_trajectory.py`：按帧驱动浏览器读入场位移，
      断言第一帧 ≤ 25%、90% 至少 6 帧、到位前不回退、过冲 ≤ 10%、末尾正好为 0。
- [x] 4.2 `tests/test_vendor_spring.py`：ζ=1 单调不过冲、ζ=0.62 峰值等于
      `e^(-πζ/√(1-ζ²))`、换 `response` 只改时间尺度、纯函数、
      许可证与改动记录在案、`Infinity` 的收敛时刻、每个页面先加载求解器。
- [x] 4.3 `tests/test_motion_runtime.py`：探针先加载 `vendor/spring.js`；
      入场签名取 0 / 0.15s / 2s 三点；钉住新的中段值；
      新增「组件喂给弹簧的必须是秒数而不是缓动进度」的反向断言。
- [x] 4.4 全量 `uv run pytest` 通过（含既有 505 项，未削弱任何既有断言）。

## 5. 文档与验收

- [x] 5.1 同步渲染契约、视觉规范、组件目录、分镜参考四份 skill 文档里的原语签名与预设表。
- [x] 5.2 README 的当前状态与 `docs/PROJECT_PLAN.md` 记录本轮实测
      （旧曲线逐帧表、新曲线逐帧表、被证伪的「旧形状也是一种弹簧」）。
- [x] 5.3 重新记录非预设成片的字节一致性哈希：先用 HEAD 资产复现旧哈希
      （`DAFDD423…` / `DF1DB75D…` 命中），再记录新哈希，证明变化只来自动效。
- [x] 5.4 `keynote-baseline` 的 C 系列 0 错误 0 提醒、K 系列 38 通过 / 7 提醒 /
      0 失败 / 11 跳过（与改动前一致），并逐帧复核入场不再弹跳。
