# 设计令牌

画面取值只有**一个真源**：`web/src/styles/tokens.css`。那里的名字就是运行时的 CSS
变量名，画面直接写 `var(--m2v-space-3)`、`var(--fig-line)`，也可用 Tailwind 的任意值语法取用。
不额外造一层 `--color-*` 别名——多一层别名意味着「改令牌」要改两处，
而漏改一处不会报错，只会有一半画面不跟着变。

令牌全部写在**一个** `@theme static` 块里，没有按主题或样式包切换的作用域层。
这一点是硬约束：曾经有 `:root[data-m2v-preset='keynote']` 与
`:root[data-m2v-style-pack='...']` 两层，而没有任何代码会给页面挂上这两个属性，
字阶、间距、圆角与描边阶恰好只写在里面，于是作品里的 `var(--m2v-space-3)` 一直是
空值——画面安静地落到初始值，没有任何报错。`tests/test_figure_contrast.py` 的 `TestSingleSource` 守住「不许再出现作用域层」。

用 `@theme static` 而不是 `@theme`：Tailwind 默认只输出被工具类用到的主题变量，
而这里的令牌多数是**组件直接引用**的。实测 `@theme` 下这些名字一个都不会出现在
产物里，组件同样会静默落到兜底值。

## 画布、安全区与栅格

| 令牌 | 值 | 用途 |
| --- | --- | --- |
| `--m2v-width` / `--m2v-height` | `1080px` / `1920px` | 画布逻辑尺寸；渲染脚本把视口设成同样大小，布局量测的绝对坐标判据依赖它 |
| `--m2v-safe-top` / `--m2v-safe-bottom` / `--m2v-safe-x` | `240px` / `320px` / `96px` | 竖屏平台上下 UI 会遮挡画面，正文不进入该区域 |
| `--m2v-safe-bottom-with-subtitles` | `520px` | 有字幕时的下边界，比 `--m2v-safe-bottom` 更大 |
| `--m2v-content-width` | `888px` | 安全区内的可用宽度 |
| `--m2v-grid-columns` / `--m2v-grid-gutter` | `12` / `24px` | 栅格列数与列间距 |

字幕几何真源是 `web/src/frames.json`（`m2v.core.frames` 读取），`m2v.engine.design_tokens`
只读 `tokens.css` 的非字幕令牌，并由 `tests/test_design_tokens.py` 守着「令牌层不得再出现
字幕/量测令牌」。这不是顺手抽公共常量：过去画面与量测两边各写一份字面量，改一处不会让另一处
报错，只会静默漂移——量测判的是旧边界，而画面已经挪走了。

注意 `--m2v-measure-*` 与 `--m2v-safe-*` **不是同一组概念**，取值也不相等：安全区描述
平台 UI 会遮挡哪里，量测边界描述项目自己的排版分区。`--m2v-safe-bottom-with-subtitles`
（`520px`）目前与量测用的 `--m2v-measure-content-bottom`（`1502px`）**并不自洽**，
且它当前没有任何消费方；按哪个为准需要单独判断，本轮刻意未动，不悄悄改掉一个已写进
文档的取值。

## 字幕尺寸的外部依据

字幕的取值此前是项目自定，没有出处。下表把公开规范与项目现值并列，**差异如实标出**，
不是「已符合规范」：

| 项 | 公开规范 | 项目现值 | 关系 |
| --- | --- | --- | --- |
| 9:16 字幕字号 | 约画幅高 **3.5%**（≈67px）[^bbc] | 字幕字号 40px（`web/src/frames.json`） | **低于**规范值约四成 |
| 9:16 字幕行数 | 最多 **3 行**[^bbc] | cue ≤28 字，实测折 2 行 | 在限内 |
| 9:16 字幕行宽 | 画幅宽 **90%**[^bbc] | 864 / 1080 = 80% | 更保守 |
| 9:16 字幕区纵向 | 不越出画面垂直中央 **75%**，即 y 240–1680[^bbc] | 字幕盒 1580–1780 | 下沿**超出**约 100px |
| 每行字数 | **16 字/行**、最多 2 行[^netflix] | 约 14 字/行 | 在限内 |
| 标点 | **不用逗号、句号**，改用单个空格[^netflix] | 在 `，。！？；：` 处断句且保留标点 | 取向**相反** |
| 阅读速度 | 成人 **≤9 字/秒**[^netflix] | 由实际 TTS 语速决定，`outputs/reading-pace.json` 只报告不阻断 | 取值随配音浮动 |

[^bbc]: BBC, *Subtitle Guidelines*（9:16 竖屏一节）
    https://www.bbc.co.uk/accessibility/forproducts/guides/subtitles/
[^netflix]: Netflix, *Chinese Simplified Timed Text Style Guide*
    https://partnerhelp.netflixstudios.com/hc/en-us/articles/215986007-Chinese-Simplified-Timed-Text-Style-Guide

标点与阅读速度两条**只是记录，尚未对齐**；行宽与行数在规范之内。
字号与字幕区下沿低于规范，改成规范值需要同时重排字幕盒并收短 cue，属于行为变更，
不在本轮范围内。

## 通用作品与令牌层的关系

通用 v8 作品的配色、排版与构图**由作品代码自己决定**：分镜里没有主题字段，`themes.json` 与
`palette.ts` 已随主题机制一并删除，作品不读取 `var(--m2v-*)` 之外的任何配色来源，也不要求
palette 解析。本文档余下的令牌服务的是**金融与住宅**这两种专用类型的画面。

字幕是唯一的例外：它是共享层，几何与样式按画幅集中在 `web/src/frames.json`——
Python 准备/量测、合成层与作品 SDK 读同一份。字幕用白字配不透明深色底板，**独立于作品配色**，
因此作品自己画深底还是浅底都不影响字幕可读性。

作品画幅只支持 1920×1080 与 1080×1920；横屏字幕安全区几何按竖屏高度缩放，字幕字号则横竖屏均为40px以适应手机观看；
水平内边距取画布宽度的同一比例，几何与字阶由测试守着（`tests/test_design_tokens.py`）。

统一制作流程中的 look bible、LUT、后期与镜头参数**不替代**这套自由设计：作品仍然自己决定
配色、排版与构图，look 只是把光色与质感基准固定下来并写进 `content.props.look` 与 shot list。
令牌层与 look 都不构成对作品配色的强制约束，两者都不得被写成「必须读取某个全局调色板」；
契约见[电影级表现与质量工具](cinematic-video.md)。

## 字体

`--m2v-font` 是中文优先的字体栈，声明在 `:root` 上，页面里所有元素都继承它。
两个 webfont（Inter、Noto Sans SC）由字体仓恢复，注册清单见 `web/src/assets/fonts.json`；
字体二进制不入库，恢复命令为 `uv run python fonts/fetch.py`。
系统字体只作兜底——系统字体不随仓库分发，换机器可能轻微影响字宽。
`--m2v-font-latin` 只给拉丁与数字用（图表里的数值列对齐依赖它），
`--m2v-font-sans` 是图形标签的槽位。

### 缺字机检

布局量测的第一步会逐个字符检查材料里**会被渲染**的文本是否在字体里有字形，
缺字直接报错并阻断预演与正式导出。判据不是拿某支字体去量，而是**画面实际注册过的
字体**：字体由 `web/src/assets/fonts.json` 声明、`web/src/fonts.ts` 在运行时注册
（文件清单见该目录的 README），量测按清单取出字体文件逐个核对字形——
只有当这些字体加起来都没有某个字形时，浏览器才真的会回退到系统字体——
那正是要抓的东西。清单为空时（画面一个字体文件都没注册）不报缺字：
无从判断，也不凭空拦人。

为什么它必须存在：缺字是唯一一种**静默失败**。浏览器不报错、不警告，直接用
系统字体顶上，字宽、字重、基线全变，而布局量测量的是元素框，照过。
它也是 webfont 子集化的前置条件——不做逐字检查就切字体，
等于把这种漂移变成常态。

范围与边界：

- 扫描材料里会被渲染的字段（`text`/`title`/`subtitle`/`label`/`quote`/`caption`/
  `value`/`unit` 等）；`narrationSegments` 是口播文本、不画在画面上，**不进扫描**；
- v8 的可见文字基本都在作品 `scenes/**/*.tsx` 里，因此源码中的字符串与模板字面量也一并
  扫描——这是 v8 唯一一处静态覆盖作品画面的检查，理由还是那一条：缺字是静默失败；
- 结论定位到 `sceneId.字段` 或作品内的相对路径——只说「缺字」不可修；
- 只判「字体里有没有这个字形」，不判字宽字重是否合适，也不判断浏览器
  实际选了哪个字体（那要跑浏览器）。

## 字号阶

相邻档位的比例落在 1.1–1.6，由测试守着。

| 令牌 | 值 | 用途 |
| --- | --- | --- |
| `--m2v-size-caption` | 28px | 角标、来源、页码 |
| `--m2v-size-label` | 34px | 组件标签、轴名 |
| `--m2v-size-body` | 40px | 正文、条目标题 |
| `--m2v-size-lead` | 60px | 引文、结论正文 |
| `--m2v-size-title` | 76px | 小节标题、大号说明 |
| `--m2v-size-headline` | 96px | 金句、主命题 |
| `--m2v-size-display` | 120px | 主角数字与极短命题 |
| `--m2v-size-hero` | 140px | 开场与收束，一个画面只用一次 |
| `--m2v-size-mega` | 220px | 字阶的模块化中间档 |
| `--m2v-size-numeral` | 350px | 数字幕的主角数值；更长的数值由拟合引擎按实测宽度往下取档 |

每一档都配一个行高 `--m2v-leading-*`（字号越大越紧）与一个字距
`--m2v-tracking-*`（标题收紧、标签放开）。行高显式指定，不依赖字体自带度量——
这是跨字体跨机器保持版式一致的前提。

组件内部的文字不引用裸字号，而是引用同一张表的语义别名：
`--m2v-ink-caption` / `-label` / `-body` / `-value` / `-lead` / `-title` /
`-display` / `-numeral`，以及幕标题的 `--m2v-heading-size` / `-weight` / `-track` /
`-color`。这样改字阶时组件会跟着走。

字重上限收到 `--m2v-weight-bold`（700）：Inter 与 Noto Sans SC 都是可变字体，
800 在中文上会让笔画粘连；「更大的数字」这个诉求已经由字号阶承担，
层级靠字号拉开，不靠加粗。

## 间距、圆角与描边

- 间距走 8pt 网格：`--m2v-space-1` … `--m2v-space-10` = 4 / 8 / 16 / 24 / 32 /
  48 / 64 / 96 / 128 / 192px。
- 圆角与层级成对，越大的表面用越大的圆角：`--m2v-radius-xs` / `-sm` / `-md` /
  `-lg` / `-xl` / `-pill` = 8 / 16 / 24 / 32 / 48 / 999px。
- 描边阶按**用途**分档，不按观感：`--m2v-stroke-1`（1px，发丝边界：卡片与面板边框）、
  `-2`（2px，次级结构：虚线辅助、坐标刻度）、`-3`（3px，数据描边）、
  `-4`（4px，图形主体：构件、轨道、节点边界）、`-5`（6px，焦点与运动轨迹）。
  分档问的是同一个问题：「这条线消失了，观众还看得懂吗」。竖屏 1080 宽在手机上
  实际显示约 400–500 逻辑像素，1px 缩过之后接近消失；但把所有线抬到 4px 又会让
  次级结构与数据描边一样重，层级反而塌掉。
- 组件字距收成五个语义槽：`--m2v-track-numeral` / `-display` / `-body` /
  `-caption` / `-label`。
- 图形几何只收「应当一起变」的那几个量：`--fig-node-r-min`、`--fig-surface-pad`、
  `--fig-connector-w`、`--fig-arrow-len`、`--fig-arrow-half`。一张图的**坐标**
  （立柱位置、节点角度、柱高数组）是内容而不是令牌，刻意留在组件里。

## 表面、墨色与强调色

- 三级背景：`--m2v-bg-0`（画布最底层 `#08090c`）、`--m2v-bg-1`（抬起的表面）、
  `--m2v-bg-2`（更高一层）；两级抬升表面 `--m2v-surface-1`、`--m2v-surface-1-top`。
- 墨色三级：`--m2v-ink-1`（18.26:1）、`--m2v-ink-2`（10.27:1）、`--m2v-ink-3`
  （7.79:1），别名 `--m2v-text-1` / `-2` / `-3`；`--m2v-ink-4`（4.54:1）不进正文。
- 描边三条：`--m2v-hairline`（纯分隔线，刻意保持耳语）、`--m2v-hairline-strong`
  （界定物体边界的描边，对抬升面 ≥ 3:1）、`--m2v-line`（图形描边下限 4.54:1）。
- 强调色一个画面只允许一个：`--m2v-accent`（`#32d6ff`，11.57:1）及其
  `-ink` / `-rgb` / `-soft` / `-line` / `-deep` / `-soft-solid` 派生档，
  加上压在重点面上的 `--m2v-on-focus` 与强调褪色落点 `--m2v-emphasis-fade`。
- 层级：`--m2v-shadow-1..3`、`--m2v-inset-highlight`、`--m2v-focus-halo` 与
  帧驱动光晕的模糊/浓度档 `--m2v-glow-emphasis-*` / `--m2v-glow-heat-*`。
- 背景层：`--m2v-glow-1/2`、`--m2v-grid-color`、`--m2v-grid-size`、
  `--m2v-grain-opacity`，几乎不可见，不参与叙事。

## 图形墨色与对比度预算

`--fig-*` 是图形专用的墨色与面填充。它们**必须存在**：一旦缺失，图形不会报错，
只会安静地变成透明，页面上只剩文字。

| 类 | 令牌 | 下限 | 判据基座 |
| --- | --- | --- | --- |
| 数据描边 | `--fig-line`、`--fig-line-data`、`--fig-water-line` | 4.5:1 | 画布 `--m2v-bg-0` |
| 图形内文本 | `--fig-water-text`、`--fig-title-grad-from/to`、`--fig-on-ink` | 4.5:1 | 画布；`--fig-on-ink` 与 `--fig-ink` 成对判定 |
| 边界描边 | `--m2v-hairline-strong` | 3.0:1 | 它落座的面 `--m2v-bg-2` |
| 装饰描边 | `--fig-line-soft` | 1.5:1 | 画布 |
| 面填充 | `--fig-ink`、`--fig-surface`、`--fig-water`、`--fig-hollow`、`--fig-node-shadow`、`--fig-drop-*`、`--fig-gauge-track` | 无 | — |

面填充不设数值下限是刻意的：形状的可读性由数据描边负责，而面阶本身
（`--m2v-bg-0` → `--m2v-surface-1`）就只有 1.1:1 左右，给面填充设下限会把正确的
做法判成缺陷。取而代之的判据是「同不同」：实心面不得等于画布，实心面、次级面
（水体）与空壳不得塌成同一个取值，次级面必须仍带冷色色相。

半透明令牌先合成到底色再量对比度——直接拿 alpha 前的取值算会高估。

`tests/test_figure_contrast.py` 按上表守着这些取值，并且要求**新增的图形颜色令牌
先进分类表**：「没有对应规则」不等于「可以放行」。改任何一个值之前先跑那个测试；
它同时守住几条不打算改的决定，例如纯分隔线要保持耳语（WCAG 1.4.11 管的是
「理解内容所必需的图形对象」，纯分隔线在豁免范围内，把每条线都提到 3:1 只会让
画面变重、层次变平）。

## 动效时长与帧驱动

`--m2v-dur-fast` / `-base` / `-slow` = 240 / 360 / 560ms（60 fps 下约 14 / 22 / 34 帧）只是
**配方里的时长刻度**，注释里换算成 60fps 的帧数供作者取用。画面本身仍然只由帧号
驱动：CSS `animation` / `transition` 会被源码闸门拒绝，见
[代码场景运行契约](code-scene-runtime.md)。

## 怎么用

```tsx
<div style={{
  padding: 'var(--m2v-space-6)',
  borderRadius: 'var(--m2v-radius-md)',
  background: 'var(--m2v-surface-1)',
  border: 'var(--m2v-stroke-1) solid var(--m2v-hairline-strong)',
  color: 'var(--m2v-text-1)',
  fontFamily: 'var(--m2v-font)',
  fontSize: 'var(--m2v-size-title)',
  lineHeight: 'var(--m2v-leading-title)',
}} />
```

Tailwind 类与令牌可以混用；需要令牌做任意值时用 `w-[var(--m2v-content-width)]`
这类写法。类名使用完整字符串，画面仅由帧号驱动。
