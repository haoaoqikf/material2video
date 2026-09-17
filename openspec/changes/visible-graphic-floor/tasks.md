## 1. 立住规则

- [x] 1.1 参考文档的分类表补上「边界描边 ≥ 3:1（基座 `--a2v-bg-2`）」一行，写明判据基座为什么不是画布、纯分隔线为什么豁免，并把「按用途分类而不是按取值分类」写成表头前提；另外记下「描边重量不是问题、对比度才是」这条被实测否掉的猜想。
- [x] 1.2 设计宪法 C16 从四类改成五类，补上边界描边的 3:1 与分隔线的豁免。

## 2. 把承重的描边调进预算

- [x] 2.1 `--a2v-hairline-strong` 调到真的过 3:1：深色 `rgba(255,255,255,0.36)` 实测 3.32:1、浅色 `rgba(12,14,19,0.45)` 实测 3.09:1（都按它落座的抬升面判定）；旁边与实测不符的注释（2.99:1）一并改掉。
- [x] 2.2 `.drop-track` 的边框改用 `var(--a2v-hairline-strong, var(--a2v-hairline))`；运行时实测计算值 `rgba(255,255,255,0.36)`。
- [x] 2.3 `.scale-rope` 按用途重新归类为结构描边：`var(--fig-line-data, var(--fig-line-soft))`；运行时实测 `rgba(255,255,255,0.62)`、4px。

## 3. 机检

- [x] 3.1 分类表加「边界描边」类（基座 `--a2v-bg-2`，阈值 3:1）；主题块解析扩到 `--a2v-*` 以便取基座，并断言两套主题都提供判定基座。
- [x] 3.2 加断言 `test_boundary_tokens_are_actually_used`：边界描边令牌必须被至少一处边框/描边声明引用（`--a2v-hairline-strong` 曾经定义了却一处都没用）。
- [x] 3.3 加断言 `test_decorative_separators_stay_a_whisper`：纯分隔线必须低于 3:1，防止被「顺手统一」抬高。

## 4. 验收

- [x] 4.1 逐帧打开 `opening`：天平的两条吊绳重新可见，横梁与秤盘的关系不再断；`attention`、`cost` 等其余幕未改坏（C 系列 24 帧 0 错误 0 提醒，K 系列 38/7/0/11 与改动前一致）。
- [x] 4.2 `examples/declarative-number` 限帧 12 帧成片 SHA256 两种口径都与改动前一致：png `DAFDD423…`、默认 `DF1DB75D…`。
- [x] 4.3 `uv run pytest` 全绿（`tests/test_figure_contrast.py` 15 项）；`openspec validate visible-graphic-floor --strict` 通过。
- [x] 4.4 同步 README 与 `docs/PROJECT_PLAN.md`，并修正上一轮记错的两条：`viewBox` 缩放会把描边变细——实测证伪（缩放比全是 1，问题在对比度）；「下三分之一空着」——实测内容在安全区内居中（上下留白 270 / 250），下方 320px 是平台界面保留带。
