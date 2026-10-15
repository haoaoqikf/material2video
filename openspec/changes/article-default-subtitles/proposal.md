## Why

文章讲解已有自动字幕，但默认烧录到画面的要求不够明确，容易被误解为可省略或只交付外置字幕。

## What Changes

- 明确 article-narrative 无需开关，默认根据旁白生成并烧录同步字幕。
- 同步制作指导，补充默认生成、帧边界、停顿隐藏、主题可读性与嵌入保留的回归验证。
- 沿用现有实现，不批量重渲染已有作品。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `article-explainer`：明确默认画面字幕与旁白同步的交付要求。

## Impact

影响文章制作文档、规格及回归测试；不新增公共字段、依赖或字幕开关。
