## Why

上一轮归档的 `keynote-design-system` 规格里有一条要求：「字号选取 SHALL 由测量得到的字宽决定，
SHALL NOT 由字数乘以经验系数估算」。**这条目前没有被满足**：排版引擎写完了、单测也过了，
但没有任何组件接上它，而且一旦接上就会立刻造成可见损坏。也就是说，现在所有字号都还是
逐个写死在组件里的，一篇文章换成长句就会静默溢出——这正是「稳定输出发布会级」最直接的缺口。

三个已实测的事实（都在共享页面的真实运行环境里验证）：

1. **引擎从未生效。** `autofit()` 每帧扫描 `[data-a2v-fit]`，而 `figures.js` 里
   `data-a2v-fit` 命中 0 次，探针也确认页面上不存在任何 `[data-a2v-fit]` 元素。
   `fit()` / `measureAdvance()` / `balance()` 全部是死代码。
2. **接上就会删掉强调词。** 给 `.quote-text` 加 `data-a2v-fit` 后调用 `autofit`，
   DOM 从 `是做决定的<span class="key">力气<span class="key-underline"></span></span>`
   变成纯文本 `是做决定的力气`，`.key` 数量从 1 变成 0。原因是 `applyFit()` 为了让
   均衡断行生效而直接写 `el.textContent = fitted.lines.join('\n')`，把子元素一起抹掉了。
   强调色是「单一焦点」的载体，静默消失等于画面失去焦点。
3. **接上就会改版式。** 同一个元素，组件 CSS 取 60px / 行高 93px，引擎取 40px / 行高 58.8px。
   两者不一致，直接接线会让现有预设画面整体变小。

还有一个结构性问题：**没有溢出闸门**。C1–C6 都是源码静态检查（三层结构、曲线纪律、
不用大面积模糊、挂载点、文案单一真源、安全区令牌），K1–K6 覆盖留白、强调色、字号种类、
对齐、对比度、卡片纪律，**没有任何一项检测「文字是否超出安全区或容器」**。
所以溢出既不会被引擎处理，也不会被闸门拦下。

## What Changes

- 让 `applyFit()` 不再破坏子元素标记：均衡断行只重排文本节点，保留 `.key`、
  `.key-underline` 等强调元素；无法安全重排时保留原文而不是抹掉标记。
- 为可能承载任意文案的组件文本元素声明 `data-a2v-fit="<档位>"`，档位取**该元素在预设下的
  现有字号档**，保证「放得下时结果不变、放不下时才降档」。
- 校验「引擎结果与组件 CSS 字号一致」：同一元素在同一份文案下，引擎取档必须等于
  样式表给它的档；不一致就是两套真源，必须由测试挡住。
- 新增溢出闸门：正文级文本块的墨迹超出安全区，或 `fit()` 返回 `fits: false`，
  都要给出实测数值与阈值；按「废片类」处理而不是只提醒——文字被裁掉或压出安全区
  不是审美问题，是画面坏了。
- 同步文档：把 `keynote-design-system.md`、`visual-spec.md` 里对排版引擎的表述
  改成与实现一致的「组件必须声明 `data-a2v-fit` 才会生效」，并在参考文档中写明
  需要声明哪些元素。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `keynote-design-system`：`把排版算出来而不是试出来` 这一条从「引擎存在」收紧为
  「引擎被组件实际使用，且不得破坏强调标记、必须与组件字号一致」；`观感闸门` 这一条
  增加溢出检测。
- `declarative-video-scenes`：`共享页面生成画面` 增加「共享页面在预设生效时对声明了
  `data-a2v-fit` 的元素按字号阶取档，且不改动非预设页面」的行为。

## Impact

- 资产层：`.agents/skills/article2video/assets/typography.js`（`applyFit` 的标记保留）、
  `figures.js`（新增 `data-a2v-fit` 声明）、`declarative.js`（取档调用点与可用宽度）。
- 闸门：`.agents/skills/article2video/scripts/a2v/keynote.py`（新增溢出判定）、
  `inspect.py`（记录每个文本块的墨迹边界）、`constitution.py`（与 K 系列分开报告）。
- 测试：`tests/test_typography.py`（标记保留、与组件字号一致、退化输入）、
  `tests/test_keynote_layout.py`（溢出判定）、`tests/test_review.py`（新闸门用例）。
- 文档：`references/keynote-design-system.md`、`references/visual-spec.md`、
  `references/design-constitution.md`、`SKILL.md`。
- 兼容性：未声明 `visual.preset` 的页面根本不会调用 `autofit`，必须保持逐字节不变；
  预设页面在「文案放得下」时取档结果等于现有字号，也必须逐字节不变。
