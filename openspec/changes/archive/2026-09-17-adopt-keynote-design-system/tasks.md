## 1. 外部资产与设计语言层

- [x] 1.1 落盘字体资产：在 `.agents/skills/article2video/assets/fonts/` 放入 Inter Variable 与 Noto Sans SC Variable，并放入两套 OFL 许可证文本与一份 `README.md` 记录字体名称、版本、来源 URL 与许可；以 `fontTools` 读出 family/axes/许可证字段与 README 一致来验证。
- [x] 1.2 新增 `assets/keynote.css`：定义模块化字号阶（固定比例、含下限说明）、8pt 间距阶、五个圆角档加一个 pill、三级投影、字号相关的行高与字距配对、按亮度序排列的表面与描边令牌、单一强调色与其 RGB 分量、两级对比度下限（正文 7:1 / 大字 4.5:1），并用注释写明每个数值的来源；以 `tests/test_keynote_assets.py` 的令牌自检（对比度、单调性、字距/行高配对、与排版引擎档位一致）读通全部令牌来验证。
- [x] 1.3 在 `keynote.css` 中用 `@font-face` 声明两套可变字体（`font-weight: 100 900`、`font-display: block`、相对路径引用本地文件），并把 `--a2v-font` 覆盖为「Inter 在前、Noto Sans SC 在后」的组合栈；以 `tests/test_offline_assets.py` 确认资产层没有任何外部 URL 且每处 `url()` 都指向仓库内真实文件、限帧导出可跑通来验证。
- [x] 1.4 提供 `optically-sized` 与网格对齐工具类（标签正字距、标题负字距、点阵背景等），全部只引用本文件或 `theme.css` 的令牌；以 `grep` 确认新增样式里没有裸色值与裸字号来验证。

## 2. 排版引擎

- [x] 2.1 新增 `assets/typography.js`，暴露 `A2V.type`：实现 `emWidth()`（按字体签名缓存单字宽度）、`measureAdvance()`（用 `Range.getBoundingClientRect()` 实测参考串宽度）、`fit()`（在字号阶上从大到小取第一个能容纳的档，触及下限返回 `fits: false` 与所需行数建议）、`applyFit()`（把结果写到元素上）；以同一输入重复调用返回相同结果为验证。
- [x] 2.2 实现 `balance(text, maxCharsPerLine)`：按语义断点（标点与空格）与字数上限把长文本断成行数最少且各行均衡的方案，末行不得只剩一个字或一个标点；以中文与中英混排各一例，人工核对断行位置符合语义来验证。
- [x] 2.3 实现 `optical(node)`：把行首的中文标点与开引号设为悬挂（负外边距，不占行首位置）；以带引号开头的段落渲染后首字仍从其后的汉字对齐来验证。
- [x] 2.4 降级路径：字体未加载或测量不可用时，`fit()` 返回按字数与经验系数估算的结果并置 `measured: false`；以在 `document.fonts.ready` 之前调用得到 `measured: false`、之后得到实测值来验证。

## 3. 主题预设

- [x] 3.1 在 `keynote.css` 中提供 `keynote-dark` 与 `keynote-light` 两套预设，各自给出完整的表面与文字令牌、单一强调色、图形墨色令牌（`--fig-*`）与字幕令牌覆盖；以两套预设下 `figures.css` 引用的全部 `--fig-*` 令牌都有定义来验证（缺一个就会安静地画出透明图形）。
- [x] 3.2 为两套预设各写一份对比度自检：正文对表面、次级文字对表面、强调色对表面、图形线对表面，全部满足 7:1 / 4.5:1 下限；以自检脚本输出实际比值清单来验证。
- [x] 3.3 覆盖字幕样式：浅色预设下字幕改为深字浅底描边，深色预设下保持白字深描边；以浅色预设下字幕区帧量测的对比度为证。

## 4. 启用路径与校验

- [x] 4.1 在 `scripts/a2v/storyboard.py` 的 `_VISUAL_THEMES` 同级新增 `_VISUAL_PRESETS = ("keynote",)`，并把 `preset` 加入根级 `visual` 的受支持字段；未知预设名报错并指出 `visual.preset`；以 `validate.py` 对未知预设的报错输出为证。
- [x] 4.2 `assets/declarative.html` 引入 `keynote.css` 与 `typography.js`（顺序在 `theme.css` 与 `figures.js` 之后），`assets/declarative.js` 读取 `storyboard.visual.preset`，命中时设置 `data-a2v-preset` 并在场景内容渲染前完成字号拟合；以未声明预设时页面 DOM 与本次变更前一致来验证。
- [x] 4.3 预设生效时的版面细化：补齐 `left` 版面（页面原本只定义了居中与下置，未声明的 `data-layout` 一律兜底为 `center`）、把组件内部散落的裸字号收进字阶（新增 `--a2v-ink-*` 别名令牌，22 处 `font-size` 改为「令牌 + 原值兜底」）、修正居中版面上引文装饰把正文推离中心的问题；**验证方式改为量测而不是看图**：`tests/test_keynote_layout.py` 用浏览器实测四种版面下每个文本块的位置与字号，断言安全区不越界、字号全部落在阶上、居中版面文字中心与画面中心误差 ≤2px、下置版面内容底边低于画面中线、未声明版面时兜底为居中、两种主题版面几何一致；以 `uv run pytest tests/test_keynote_layout.py` 全绿为证。
- [x] 4.4 为上述新增行为补测试：`tests/test_typography.py`（排版引擎纯函数：字号阶顺序、取档与越界兜底、均衡断行与避头尾、退化输入）、`tests/test_offline_assets.py`（`visual.preset` 校验、资产一致性、限帧导出）、`tests/test_keynote_assets.py`（`keynote.css` 必须定义 `figures.css` 引用的全部 `--fig-*` 令牌）；以 `uv run pytest` 全绿为证。

## 5. 观感闸门

- [x] 5.1 在 `scripts/a2v/inspect.py` 的帧量测基础上新增 K 系列指标计算：留白率（背景像素占比）、强调色面积占比、单帧字号种类、对齐基线一致性、正文对比度、卡片与描边纪律；每项给出实测数值与阈值，无法实测时标记 `skipped` 并写明原因。
- [x] 5.2 在 `scripts/a2v/constitution.py` 与 `scripts/review.py` 中把 K1–K6 与 C 系列分开报告与计数，终端输出与 `report.json` 都要能看出「哪一条是废片类、哪一条是观感类」；以 `review.py --declarative` 在示例上的输出为证。
- [x] 5.3 为 K 系列补测试：构造留白不足、强调色超量、字号种类过多的合成画面，断言闸门报告对应条目与实测数值；以测试通过为证。

## 6. 文档同步

- [x] 6.1 新增 `references/keynote-design-system.md`：写清「发布会级别」的可判定定义、令牌体系与数值来源、排版引擎的接口与降级、预设的启用方式、K1–K6 的阈值与判定方法，以及它与 `visual-spec.md`（通用规范）的分工。
- [x] 6.2 更新 `references/visual-spec.md`：字体一节改为指向随仓库分发字体与预设；排版层级一节补上「字号取自字号阶」；明确未启用预设时的行为不变。
- [x] 6.3 更新 `references/design-constitution.md`：新增 K1–K6 一节，并在「机检与人工的分工」表中标注每条 K 的检查强度（实测 / 跳过）。
- [x] 6.4 更新 `references/storyboard-schema.md` 与 `references/figure-catalog.md`：记录 `visual.preset` 字段与它对组件墨色令牌的要求，并把 `narration` 等「当前不渲染」的标注核对一遍。
- [x] 6.5 更新 `SKILL.md`、`README.md`、`docs/PROJECT_PLAN.md`：把设计语言与观感闸门写入当前状态与阶段路线，未实现的部分（视觉模型自动评审、webfont 子集化、自动选择预设）明确留在未实现清单。

## 7. 验收

- [x] 7.1 用启用预设的分镜走通「校验 → 预览 → 限帧导出 → 视觉评审」全链路，`validate.py --declarative --strict` 零错误零警告、`review.py` 的 C 系列零错误、K 系列给出实测数值；以命令输出与 `report.json` 为交付物。
- [x] 7.2 逐帧不变性回归：对未启用预设的既有示例，在本次变更前后各取同一帧做逐像素比对，要求完全一致；以比对结论为交付物。
- [x] 7.3 断网渲染验证：`tests/test_offline_assets.py::TestOfflineRender::test_page_loads_with_every_non_local_request_blocked` 在 Playwright 层拦掉浏览器发出的每一个非本地请求（非 `127.0.0.1` 一律 `abort`），断言「没有任何请求被拦下」「两套 webfont 的 `FontFace.status` 都是 `loaded`」「两个 `.ttf` 确实从本地路径取回」。静态扫 URL 只能证明资产层没有外链，证明不了浏览器真的只用本地资产。
- [x] 7.4 运行 `uv run pytest` 与 `openspec validate adopt-keynote-design-system --strict`，确认既有测试与规格校验全部通过。
- [x] 7.5 检查暂存内容不包含生成媒体、缓存或密钥（字体资产与许可证必须包含），按仓库约定提交本变更与配套文档，并在交付时报告 commit 标识与验证结果。以 `520b9c0` 提交；暂存内容经扫描无 `outputs/`、`*.mp4`、缓存与凭据，字体资产与两套 OFL 许可证均已跟踪。
