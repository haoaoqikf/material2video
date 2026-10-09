## Why

事件资料、事件暂停与画面标记让金融视频偏离连续行情展示，并增加制作、校验和验收负担。统一移除事件流程，保留仅由真实日收盘价驱动的折线动画。

## What Changes

- **BREAKING** 金融工作流取消事件搜索、事件文件、事件停顿及所有画面事件元素。
- 动画计划升级至 schemaVersion 4；价格材料保持 version 3。
- 60 秒时间轴改为开场 3 秒、连续推进 51 秒、全貌展开 2 秒、全貌停留 4 秒。
- 显式迁移旧计划；英伟达重制为无事件成片，并清理旧视频和检查产物。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `financial-timeseries-video`：取消事件工作流与标注，调整动画计划版本、评审门禁和材料迁移规则。

## Impact

金融材料校验、CLI、时间轴编排、渲染器、React composition、测试、金融专题文档及被忽略的 Nvidia 作品产物。
