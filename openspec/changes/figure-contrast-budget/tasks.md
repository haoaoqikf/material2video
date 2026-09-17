## 1. 立住规则

- [x] 1.1 在 `references/keynote-design-system.md` 增加「图形颜色：分类 + 对比度预算」一节：四类令牌（数据描边 / 图形内文本 / 装饰描边 / 面填充）、各自的判据、阈值与两套主题的实测值，以及为什么面填充不设数值下限（浅色主题自己的面阶只有 1.13:1）、为什么槽只能给耳语级一层白。
- [x] 1.2 在设计宪法里新增 C16「图形看得见」并写进「机检与人工的分工」表；证据：`references/design-constitution.md` 中出现 C16 与「图形颜色预算」一行。

## 2. 把令牌调到预算内

- [x] 2.1 两套主题新增 `--fig-line-data`（深色 `rgba(255,255,255,0.62)` 实测 7.75:1、浅色 `rgba(12,14,19,0.72)` 实测 7.42:1）；非预设主题层 `theme.css` 里定义为 `var(--fig-line-soft)`，未启用预设时与原来同值。
- [x] 2.2 不达标的取值全部进预算，逐条实测：浅色 `--fig-line` 3.31 → 5.22:1、浅色 `--fig-line-soft` 1.35 → 1.63:1、浅色 `--fig-water-line` 1.89 → 5.23:1、浅色 `--fig-water-text` 3.73 → 7.22:1、深色 `--fig-water-line` 3.23 → 4.82:1。
- [x] 2.3 `figures.css` 里承载结构的两处描边（`.loop-track` @489 / `.stair-axis` @592）改成 `var(--fig-line-data, var(--fig-line-soft))`；证据：两种命令口径下 `examples/declarative-number` 限帧 12 帧成片 SHA256 均与改动前一致。
- [x] 2.4 **落地过程中发现并修掉的同类缺陷**：`figures.css` 里写死的颜色不跟主题走——`.load-hollow` 的 `rgba(22,24,29,0.035)`、`.loop-node-shadow` 的 `rgba(30,26,22,0.07)`、`.drop-track` 的 `rgba(22,24,29,0.025)`、`.drop-fill` 的 `#3a3f4a→#23262d`、`.drop-fill.is-fact` 的红渐变、`.gauge-track` 的 `rgba(22,24,29,0.07)`、`.title-text` 的渐变。全部改成令牌 + 回落原值，两套预设各自给值；证据：运行时计算值从 `rgba(22,24,29,0.024)` 变成 `rgba(255,255,255,0.03)`、从 `rgb(58,63,74)` 变成 `rgb(109,125,149)`。

## 3. 机检

- [x] 3.1 新增 `tests/test_figure_contrast.py`：解析两套主题的 `--fig-*` 取值（半透明先合成到底色），按分类表断言每条预算，断言「出现未归类的图形颜色令牌即报错」，并禁止 `fill`/`stroke`/`background` 出现字面色值。
- [x] 3.2 断言分类表覆盖完整：遍历两套主题定义的全部图形颜色令牌与 `figures.css` 真正引用的令牌，`--fig-*` 集合必须被表覆盖（`test_every_token_is_classified` / `test_classes_cover_the_tokens_figures_css_actually_uses`）。
- [x] 3.3 断言浅色主题单独被覆盖：`test_data_strokes_are_measured_in_both_themes` 逐个主题核对主描边、结构描边与水体描边，防止只修深色主题。**顺带发现测试自己写错了**：浅色主题块的选择器一度取到深色块（`[data-a2v-preset="keynote"]` 先命中的是基础块），是 `test_both_themes_define_the_same_tokens` 把它抓出来的，已改成带主题名的完整选择器。

## 4. 验收

- [x] 4.1 逐帧打开确认（不看数字）：`cost` 一幕 35% 处左栏出现清晰的实心柱（改动前是 `#3a3f4a` 压在深色卡片上，看不见），96% 处抽干后只剩底下一线 + 虚线幽灵框 + 差额括号，右栏按设计是空的（`applyDrop(fillB, 0)`）；`attention` 水体轮廓、`freedom` 阶梯轴线、`opening` 的空壳都逐帧对过。
- [x] 4.2 `examples/declarative-number` 限帧 12 帧成片 SHA256：`--capture-format png` → `DAFDD423ED3B98DD8A4DCBAD89C607BCD68DA49CBED0D4C71605E09A9A208D31`（69287 字节），默认 → `DF1DB75DC8BED5171DF4000335EE781AD0CE091CAC9131DE126C0FB303A96510`（60665 字节），两者都与改动前一致。**记录本身的缺陷已修正**：原来只记了 `DAFDD423…` 而没记命令，照它用默认口径复现不出来——现在把命令与哈希一起写进参考文档。
- [x] 4.3 `uv run pytest` 全绿（含既有的 `TestThemeTokens`：组件库用到的每个墨色令牌都由主题层提供，因此新令牌也接进了非预设层）；`openspec validate figure-contrast-budget --strict` 通过。
- [x] 4.4 同步 `README.md`、`docs/PROJECT_PLAN.md`、参考文档与设计宪法；暂存内容不含生成媒体与缓存，已提交。
