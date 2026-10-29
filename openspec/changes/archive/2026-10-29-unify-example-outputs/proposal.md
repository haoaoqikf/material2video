## Why

仓库自带示例的源材料在 `examples/<slug>/`，产物却被分流到 `videos/examples/<slug>/outputs/`：同一示例被拆成两处，检查、清理与查找都要在两个目录间切换，用户要求把示例产物统一归入各自示例目录。本次同时把 `videos/examples/` 下已生成的产物合并进 `examples/<slug>/outputs/`。

## What Changes

- 移除示例作品根到 `videos/examples/<slug>/` 的重定向：`delivery.outputs`、`qa.delivered_video`、general 的 preview/render 输出根、render 后清理目录都直接使用作品根下的 `outputs/`。
- 示例的产物（`delivery.json`、`video.mp4`、候选、QA、评审包、准备与缓存）统一写入 `examples/<slug>/outputs/`；该目录继续由 `.gitignore` 的 `outputs/` 规则忽略，示例源仍入库。
- 迁移现有产物：`videos/examples/*/outputs/` 合并到 `examples/*/outputs/`，同名文件保留修改时间较新的版本，被较新版本取代的旧文件另存到 `.superseded-from-videos/`。
- 更新测试与文档：路径推导、示例说明、制作流程参考与 OpenSpec 主规格同步到新位置。

## Capabilities

### Modified Capabilities

- `article-workspace`：示例作品根同样按「产物归属作品目录」处理，产物落在 `examples/<slug>/outputs/`。
- `modular-video-production`：仓库自带示例走统一入口时，媒体、预演与成片写入示例自身的 `outputs/`。
- `article-explainer`：三个固定示例的成片位置改为各自 `examples/<slug>/outputs/`。

## Impact

只改变仓库内示例的产物归属，不影响正式作品 `videos/<type>/<slug>/outputs/` 与内容根推导；不新增 CLI、schema 或类型。`examples/*/outputs/` 仍不入库，示例源材料与媒体恢复流程不变。旧位置 `videos/examples/` 不再产生新产物。
