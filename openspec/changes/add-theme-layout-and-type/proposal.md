## Why

上一轮的 `velvet` 主题只做到了换色。逐项核对原因：`ArticleExplainer` 的观感由**取形（圆角与描边）、间距、构图对齐、字阶比例**共同决定，而这四类取值全部以字面量写在组件里，主题数据里没有任何字段、组件里也没有任何读取点。于是无论换哪套风格，产出都只能是"换色 + 变速"。

具体缺口（均为实测）：

- 外部风格包 Velvet Standard 定义了 `colors / typography / rounded / spacing / motion` 五类，项目只接了 `colors / typography / motion`，**`rounded` 与 `spacing` 完全没有接线**。
- 组件的圆角是 `24 / 24 / 20 / 16 / 22`（面板 / 对比列 / 步骤卡 / 因果节点 / 媒体框），而 Velvet 的签名是 `sm 0px / md 2px` 的近直角——这一层完全没有接口。
- 排版四个字段里，`uppercase` 对中文完全无效、`bodyLineHeight` 1.5→1.6 近乎不可见；真正决定层级感的**字号是写死的**（标题 68 : 正文 40 = 1.7:1，而 Velvet 是 3:1）。
- 入场进度是**线性斜坡**，Velvet 的性格在缓动（`sine.inOut`）上，因此时长拉长只读作"变慢"。

## What Changes

- 主题数据扩展到**取形、间距、构图、字阶**四类，与既有的颜色、排版、动效并列，仍以 `web/src/themes.json` 为唯一真源。
- 组件里写死的 37 个样式取值改为从主题读取；`velvet` 值保持既有画面**逐像素不变**（dark / light 取值与现状逐字相等，并实测比对）。
- 新增**构图模式**：主题声明水平对齐与垂直对齐，`velvet` 取居中对称以兑现"generous negative space / symmetrical, centered"。
- 新增**字阶比例**：主题声明各角色的字号，`velvet` 取 标题 120 : 正文 40 = 3:1。
- 入场动效改为**帧驱动的三次贝塞尔缓动**，主题声明曲线控制点；dark / light 用 `[0,0,1,1]`（即线性），画面不变。纯帧函数实现，不引入 CSS 动画，不触碰源码闸门。
- 图形尺寸（因果图、媒体框、代码框）也纳入主题，使更大的标题有空间可放。
- 同步参考文档与规格，并逐条标注 `velvet` 相对原风格的改编。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `article-explainer`：视觉主题的承载范围从"颜色、排版、动效"扩展到"取形、间距、构图、字阶、动效"，并明确构图模式与缓动的契约。
- `keynote-design-system`：明确讲解画面的按主题取值（含取形、间距、构图）由主题数据承载，令牌层仍只提供一套深色。

## Impact

`web/src/themes.json`、`web/src/palette.ts`、`web/src/compositions/ArticleExplainer.tsx`、
`src/m2v/engine/themes.py`（动效字段校验需接受缓动曲线）、浏览器验收与制作参考文档。
不新增分镜字段，不改准备阶段的时间轴算法，`catalog.json` 与 `sync_docs.py` 不涉及主题。
