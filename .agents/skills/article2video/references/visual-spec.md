# 竖屏视觉规范

面向抖音类竖屏信息可视化短视频的排版、层级与动效约定。目标是「中文排版清晰、无溢出、
跨机器可复现」，并让画面具备稳定的高级感；配色与气质的具体取舍仍由每支视频自己决定。

规范分两层：

- **硬约束**：画布、安全区、字号下限、帧驱动，违反会直接导致裁切、模糊或闪烁；
- **配方**：层级、动效、风格方向，是可以直接照抄的数值，也是「高级感」的来源。

## 画布

| 项目 | 值 | 说明 |
| --- | --- | --- |
| 逻辑尺寸 | 1080 × 1920 | 9:16 竖屏，与分镜的 `width`/`height` 保持一致 |
| 帧率 | 30fps | 与分镜的 `fps` 保持一致 |
| 色彩 | sRGB | 不做 HDR |

网页按逻辑尺寸写死布局，**不要**用 `vw`/`vh`/百分比做响应式适配。
预览所需的自适应由 `timeline.js` 的整体缩放完成，不进入画面计算。

## 安全区

平台 UI 会遮挡画面上下缘，正文必须留在安全区内。`base.css` 已定义变量并提供
`.a2v-safe` 容器：

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `--a2v-safe-top` | `220px` | 顶部留白（状态栏、账号信息） |
| `--a2v-safe-bottom` | `320px` | 底部留白（文案、进度条、按钮） |
| `--a2v-safe-x` | `96px` | 左右留白 |

可用区高度为 `1920 - 220 - 320 = 1380px`。排版超长时优先精简文案，
而不是压缩安全区。

## 字号下限

以 1080px 宽为基准，保证在手机小屏上仍可读：

| 用途 | 建议区间 |
| --- | --- |
| 开场主标题 | 110–150px |
| 金句正文 | 76–96px |
| 结论全文 | 88–110px |
| 节点 / 卡片标签 | 56–72px |
| 辅助说明、注释 | 30–38px |

低于 30px 的文字在竖屏上基本不可读，应改为口播或删除。

## 排版层级

字号只解决「看得清」，层级才决定「看起来贵」。同一画面里按下表分工，
不要靠加粗和变色堆重点：

| 角色 | 字号 | 字重 | 颜色令牌 | 说明 |
| --- | --- | --- | --- | --- |
| 主命题 | 110–150px | 700–800 | `--a2v-text-1` | 一幕只出现一句 |
| 正文 / 金句 | 76–98px | 500–600 | `--a2v-text-1` | 长句拆场景，不缩小字号 |
| 小节标题 | 44–56px | 500 | `--a2v-text-2` | 只做引导，不抢焦 |
| 标签 / 序号 | 28–34px | 400 | `--a2v-text-3` 或强调色 | 配 `letter-spacing: 0.22em` |
| 行动提示 | 34–40px | 500 | `--a2v-text-2` | 配左侧强调竖线 |

规则：

- **一个画面一个视觉焦点**：强调色只在焦点元素上出现；
- 标题用负字距（`-0.02em` 左右），标签用正字距（`0.2em` 以上），
  正文保持 0，字距是区分「标题感」和「正文感」最廉价的手段；
- 每个场景最多 3 行正文，每行不超过 14 个汉字，用分镜里的换行符手动断行，
  不要让浏览器自动折行决定重点词的位置；
- 关键短语用强调色 + 光晕标出，**不要**整句加粗或变色。

## 图形标注

「以形表意」的画面（天平、冰山、落差尺这类比喻）需要几个短标签才能读懂，
但它们不该写死在网页里，也不该塞进正文。分镜用 `annotations` 提供这些标签，
每个场景类型有一套约定键；网页按 `data.annotations["键"]` 取用，
取不到时留空而不是回退到默认文案：

| `type` | 约定键 | 用途 |
| --- | --- | --- |
| `title` | `leftPan`, `rightPan` | 天平两侧托盘上的名字 |
| `quote` | `assumption`, `fact`, `dropLabel`, `noDropLabel` | 落差尺：两栏标题与两把尺的标签 |
| `list` | `tip`, `mass`, `surface` | 冰山：水面之上、水面之下、水面线 |
| `diagram` | `gauge` | 反馈循环的进度表标签 |
| `timeline` | `axis`, `before`, `after` | 阶梯：纵轴名、翻转前后两种读法 |
| `conclusion` | `leftNode`, `rightNode` | 双向选择的两个端点 |

键的取值是**每篇文章自己的选择**，上表只是当前网页实现的键名。
新增画面时先在网页里定键名，再把同一组键写进分镜与本节表格。

## 视觉层级与景深

深色画面最容易显得「扁平、廉价」，按下面三层叠起来即可获得景深：

1. **背景层**（常驻，放在 `[data-a2v-stage]` 内、场景容器之外）：
   光晕 + 网格 + 细点阵，直接用 `theme.css` 的
   `.a2v-bg-glow` / `.a2v-bg-grid` / `.a2v-bg-grain`；
2. **表面层**（卡片、节点）：`--a2v-bg-1` 打底 + `--a2v-surface` 顶亮底暗渐变
   + 1px `--a2v-hairline` 边框 + `--a2v-inset-highlight` 内高光
   + `--a2v-shadow-2` 双层投影（近处小阴影定形，远处大阴影造景深）；
3. **焦点层**：只让一个元素同时拿到强调色边框、内发光与外发光
   （`rgba(var(--a2v-accent-rgb), a)` 拼接光晕，按帧改变 `a`）。

不要用 `filter: blur()` 做大面积模糊：它既拖慢逐帧截图，也无法被
「同帧一致」的验收覆盖。需要光晕就用 `radial-gradient` 或 `box-shadow`。

## 动效

- 只使用**由帧号推导**的 `transform`、`opacity`、颜色变化；
- 禁止 CSS `animation` / `transition`，原因见 [渲染契约](render-contract.md)；
  `render.py` 会在开渲前静态扫描并提示这类写法；
- 单次入场动效建议 12–30 帧（30fps 下 0.4–1.0 秒）；
- 逐项呈现的间隔建议 4–10 帧，过快会看不清，过慢会拖节奏；
- 画面不要长时间完全静止：入场结束后用常驻微动（`api.breath`，振幅 3–5px、
  周期 120–150 帧）保持活性；配音会把场景拉长，后段静止在成片里像卡住。

`timeline.js` 提供的原语（全部是纯函数）：

```js
api.progress(localFrame, startFrame, durationFrames, 'outCubic'); // 0..1
api.stagger(index, stepFrames, baseFrame);                        // 第 i 项的起始帧
api.enter(element, p, { distance: 56, axis: 'y' });               // 透明度 + 位移 + 缩放
api.spring(p, { damping: 6, frequency: 1.2 });                    // 带微过冲的进度
api.range(p, from, to, { clamp: true });                          // 进度映射为任意数值
api.breath(localFrame, { periodFrames: 120, amplitude: 4 });      // 常驻呼吸位移
api.drawPath(svgPath, p, { length });                             // SVG 描边动画
api.revealChars(el, text, p, { frame, staggerFrames });           // 逐字揭示
```

缓动名可选：`linear`、`outCubic`、`inOutCubic`、`outQuint`、`outBack`。
时间只走三条曲线：出场用 `outQuint`、双向变化用 `inOutCubic`、
逐项门控用 `outCubic`；混用更多曲线会让画面显得杂。

### 动效配方

下面的帧数是 30fps 下的实测推荐值，可直接照抄，再按成片观感微调：

| 场景 | 配方 |
| --- | --- |
| 卡片 / 节点入场 | 位移 56–64px + 缩放 0.96→1，`api.spring` 微过冲，20–24 帧 |
| 文字聚焦入场 | 位移 24px + 透明度 0→1，22 帧 `outQuint` |
| 标签横线 / 强调竖线 | `scaleX` / `scaleY` 0→1，20 帧 `outQuint` |
| 关键短语点亮 | 颜色 + 光晕 0→峰值，26–30 帧 `inOutCubic`，在句子读完后触发 |
| 关系图连线 | `api.drawPath` 描出，正向 14 帧、回环 60 帧 `inOutCubic` |
| 对比双栏 | 左右各 24–26 帧，起点相差 45–60 帧；落选一栏降到 0.42 不透明度 |
| 结论逐字 | `api.revealChars` 每字间隔 2 帧，起点在第 8 帧 |
| 场景末段 | `api.breath` 振幅 3–5px，`settle` 从第 70 帧起 40 帧渐入 |

## 可复用风格方向

三套风格都建立在同一套令牌上，只改令牌与构图，不必换运行时：

| 方向 | 背景与表面 | 强调色 | 排版 | 动效节奏 |
| --- | --- | --- | --- | --- |
| 深色科技（示例采用） | 近黑底 + 光晕 + 网格 + 细点阵，卡片带内高光 | 单一青色 `#35e0c8` | 大字重标题 + 负字距，标签正字距 | 20–30 帧入场，微过冲 |
| 编辑杂志 | 浅底 `#f6f7f9`，白色卡片，投影收敛 | 一点朱红或墨蓝 | 标题更大、正文更松，允许两栏 | 16–22 帧，曲线更克制 |
| 极简高级 | 单一深色或米色底，几乎无网格 | 用文字色而非彩色强调 | 大面积留白，一次只放一句话 | 24–36 帧，长缓动 |

## 场景节奏

- 场景时长由**口播文案**所需时间决定，不要先定时长再塞文案；
- 30fps 下常用参考：开场命题 4–6 秒，金句 6–9 秒，对比 8–10 秒，
  关系图 10–14 秒，结论 8–11 秒；
- 单场景不要短于 24 帧（0.8 秒），否则入场动效会被压缩到看不清；
  `validate.py` 会对过短的场景给出警告；
- 总时长 30–60 秒较适合单条内容；超过 90 秒建议拆成多条。

## 资产引用

共享资产位于 `.agents/skills/article2video/assets/`，按层级调整相对路径。
`theme.css` 提供设计令牌与背景层工具类，**不定义任何元素级样式**，
因此引入与否都不会改变既有画面：

```html
<link rel="stylesheet" href="../../.agents/skills/article2video/assets/base.css">
<link rel="stylesheet" href="../../.agents/skills/article2video/assets/theme.css">
<link rel="stylesheet" href="../../.agents/skills/article2video/assets/figures.css">
...
<script src="../../.agents/skills/article2video/assets/timeline.js"></script>
<script src="../../.agents/skills/article2video/assets/figures.js"></script>
```

顺序不能颠倒：`base.css` 负责画布与安全区，`theme.css` 提供令牌，
`figures.css` 是组件自己的样式，页面自身样式放在最后，保证页面永远拥有最终覆盖权。
`figures.js` 必须在 `timeline.js` 之后加载：它复用运行时的动效原语。

组件库承担「一幕画面怎么画」，页面只负责舞台、背景与挂载点；
要不要用组件、用哪一个，见 [视觉组件目录](figure-catalog.md)。

背景层是常驻元素，放在 `[data-a2v-stage]` 内、`[data-a2v-scene]` 之外，
并把场景容器抬到背景之上：

```html
<div data-a2v-stage>
  <div class="a2v-bg-glow" aria-hidden="true"></div>
  <div class="a2v-bg-grid" aria-hidden="true"></div>
  <div class="a2v-bg-grain" aria-hidden="true"></div>
  <section data-a2v-scene data-scene-id="opening">…</section>
</div>
```

```css
.stage-bg { z-index: 0; }
[data-a2v-scene] { z-index: 1; }
```

## 字体

`base.css` 使用系统中文字体栈（苹方 / 微软雅黑 / Noto Sans SC 等）。
好处是零体积、无需网络；代价是**不同机器字宽略有差异**，可能影响换行位置。

对换行位置敏感、或需要在没有中文字体的环境（如 Linux CI）出片时，
可改为随仓库分发 webfont 并在网页中声明 `@font-face`：

```css
@font-face {
  font-family: "A2V Sans";
  src: url("assets/fonts/noto-sans-sc.woff2") format("woff2");
  font-weight: 100 900; /* 可变字体需声明区间 */
  font-display: block;  /* 避免回退字体先渲染 */
}
```

使用 webfont 时必须同时分发其许可证文件（Noto Sans SC 为 SIL OFL 1.1），
并把 `--a2v-font` 覆盖为新字体。当前仓库尚未分发字体，本条属于可选增强。

## 排版自查

导出前至少检查一次：

- [ ] 所有正文在 `.a2v-safe` 内，没有被上下缘裁切；
- [ ] 最长的一行没有贴边或与其它元素重叠；
- [ ] 正文没有超过 3 行，长句已拆场景或手动换行；
- [ ] 同一画面只有一个视觉焦点，强调色只出现在它身上；
- [ ] 背景、表面、焦点三层都在，画面没有「贴在纯色底上」的扁平感；
- [ ] 卡片 / 节点有 1px 边框、内高光与双层投影，而不是纯色块；
- [ ] 入场动效都走 `outQuint` / `inOutCubic`，没有凭空多出的曲线；
- [ ] 末帧不是完全静止（有 `api.breath` 级别的微动）；
- [ ] 每帧重复渲染结果一致（可对同一帧截图两次比对）。

## 逐句字幕

有声模式共享运行时自动添加 `.a2v-with-subtitles` 与字幕层；1080 × 1920 下默认 48px、
行高 1.3、白字深色描边，左右沿用 96px 安全边距，底部沿用 320px 安全边距。
每条字幕最多 28 个字符，用真实字词边界拆分；最多两行，采用均衡换行。
正文 `.a2v-safe` 的底部额外留出 180px，禁止覆盖字幕区域。其他画布尺寸需相应调整样式。
空白或停顿时间不显示字幕；不缩小字号塞入超长字幕，不按字数猜测发音时间。
字幕随逐帧截图烧录，预览与导出排版相同，SRT 不携带字体样式。
