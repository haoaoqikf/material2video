## Why

通用讲解此前只有 dark/light 两档，而且主题数据与动效时长分散在三处：颜色写在
`web/src/palette.ts`，入场与阅读停留是 `ArticleExplainer.tsx` 与 `explainer.py` 里的字面量，
转场时长只由分镜声明。结果是既没法引入一套有出处的风格，也没法让风格同时决定节奏。

调研外部视频风格包后选定 HyperFrames `visual-styles.md` 的 Velvet Standard（Vignelli 调性）。
它的原值不能直接落地：强调色 `#1a237e` 在近黑底上对比度只有 1.49:1，
动效时长是现有值的 4–6 倍（入场 1.2s 对 8 帧）。因此需要把「主题」提升为同时承载
颜色、排版与动效的共享数据，并让主题能够接管节奏。

## What Changes

- 新增 `web/src/themes.json` 作为主题的唯一真源，前端 `palette.ts` 与 Python
  `m2v.engine.themes` 同读；主题名单、默认主题与契约校验都由它派生。
- 新增 `velvet` 主题：颜色按项目既有的对比度预算改编（强调色同色相提亮到 12.25:1），
  排版只取字重 300 / 字距 0.15em / 拉丁大写（原风格的 web 尺度字号不采用），
  动效照搬 1.2s / 3.0s / 1.5s 即 36 / 90 / 45 帧。
- 主题声明了 `transitionFrames` 就覆盖每幕的 `transitionFrames`；未声明则沿用分镜，
  因此 dark/light 的既有作品画面逐像素不变（已实测）。
- 同步参考文档与规格，写清主题与令牌层的边界、以及 `velvet` 相对原风格的三条改编。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `article-explainer`：主题不再限定深浅两档，主题可接管转场时长与阅读停留。
- `keynote-design-system`：明确令牌层仍只提供一套深色，多主题由主题数据承载，且不引入作用域层。

## Impact

前端 `palette.ts`、`ArticleExplainer.tsx`、`themes.json`；Python `explainer.py` 校验、
`explainer_prepare.py` 时间轴、新增 `m2v/engine/themes.py`；浏览器验收与制作参考文档。
不新增或修改分镜字段，`catalog.json` 与 `sync_docs.py` 不涉及主题。
作品代码场景按约定拿到主题**名字**，因此需要覆盖清单中的每一个主题。
