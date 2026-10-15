## Why

真实 MP4 抽查发现文章字幕被带 z-index: 1 的场景背景遮挡，先前只检查文字存在和布局不足以发现此问题。

## What Changes

- 提高文章字幕层级，并让浏览器量测拒绝被遮挡的字幕。
- 增加真实命中测试，重走三个作品的准备、完整预演与正式导出。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `article-explainer`：字幕可见性门禁明确拒绝遮挡。

## Impact

文章 composition、浏览器量测、回归测试及制作参考；不改变分镜字段。
