## Why

`stock-montage` 的画布固定 1080×1920（9:16），但检索只按「竖/横/方」粗筛，画面再用 `objectFit: cover` 兜底，于是横屏素材被裁掉大半：现有作品 `pixabay-e2e-20261015` 选中的素材是 1280×720、1280×865、1920×1080、1280×853。素材长宽比必须与成片画布一致，这是画面质量与「素材可核验」的基本要求，不能靠事后裁切掩盖。

## What Changes

- `brief.json` 新增长宽比契约：`provider.aspectRatio`（`canvas` 默认 / `any`）与 `provider.aspectRatioTolerance`（默认 0.02），并支持幕级 `scene.aspectRatio` 覆盖。
- 检索阶段按比例**硬过滤**候选，而不是降权排序；视频变体按目标比例选择，替代当前偏向 1080 高度的偏置。
- 素材记录里的像素尺寸改为**所下载文件的实测尺寸**（ffmpeg 探测），比例不符时该幕失败并清理刚下载的文件。
- 校验与渲染门禁复核记录与素材的比例，记录被手改或素材被替换为比例不符的文件时失败。
- **BREAKING**：默认由「不校验比例」变为「按画布比例匹配」，既有作品的检索记录因 provider 块缺字段而失效，必须重新执行 `m2v stock search`。
- Pexels 图片在比例匹配开启时优先取保持原始比例的 `original/large2x/large`，不再取 Pexels 裁切过的 `portrait` 缩略图。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `stock-montage-video`：材料新增长宽比契约字段与幕级覆盖；检索必须只采用比例在容差内的候选；留证尺寸必须为实测尺寸；渲染前必须复核比例；画面呈现与裁切容差的关系写入规格。

## Impact

影响 `src/m2v/types/stock/`（材料校验、图库适配、检索与留证、CLI 输出）、新增 `src/m2v/engine/media_probe.py`（实测尺寸探测）、类型目录模板、Skill 参考文档与 README，以及 `tests/test_stock_montage.py` 与新增探针测试。不新增依赖，不修改渲染契约、时间轴编译、音频与清理流程，不改动 `web/` 画面代码。
