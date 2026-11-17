## Why

仓库中的逐字显影、象形图和波形参考没有入库场景直接使用。逐字显影已有排版实现，象形图的透明度和波形的独立归一化容易让观众误读数据。

## What Changes

- 移除 `Typewriter`、`Pictogram`、`IconGrid`、`Waveform` 及其专属峰值重采样工具，清理相应的导出、测试和指导。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `shared-motion` 缩减可选动效参考清单和相应的行为约束。
- `react-code-scenes` 同步可复制采用的参考组件清单。

## Impact

影响 Web 参考源码、测试夹具、组件指南和《复利》中未使用的 `Typewriter` 副本。已有独立作品使用各自的本地源码。
