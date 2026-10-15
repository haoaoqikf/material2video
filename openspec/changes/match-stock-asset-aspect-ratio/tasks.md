## 1. 比例契约与材料

- [x] 1.1 新增 `src/m2v/types/stock/aspect.py`：画布常量、`canvas`/`any` 枚举、默认容差、`canvas_ratio()`、`target_ratio()`、`effective_mode()`、`ratio_matches()`。
- [x] 1.2 `brief.py` 接入新字段（`provider.aspectRatio`、`provider.aspectRatioTolerance`、幕级 `scene.aspectRatio`）、默认值与一致性校验，并让 `WIDTH/HEIGHT` 引用共享常量。

## 2. 图库适配

- [x] 2.1 Pexels 与 Pixabay 的视频变体按目标比例选择，保留无目标比例时的原行为。
- [x] 2.2 Pexels 图片在比例匹配开启时优先保持原始比例的缩略图。

## 3. 检索、留证与门禁

- [x] 3.1 新增 `src/m2v/engine/media_probe.py`：用 ffmpeg 探测本地媒体实测像素尺寸。
- [x] 3.2 `search.py` 逐幕硬过滤比例不符的候选，报错给出放宽路径，记录写入实测尺寸与长宽比声明，指纹纳入幕级覆盖。
- [x] 3.3 `load_record` 复核 provider 新字段、幕级声明与记录尺寸比例，不符即失败。
- [x] 3.4 `stock` CLI 逐幕输出尺寸，便于交付核对。

## 4. 目录与文档

- [x] 4.1 `src/m2v/types/catalog.json` 模板补新字段并运行 `sync_docs.py` 重新生成类型清单。
- [x] 4.2 更新 `references/stock-montage-video.md` 与 `README.md`，写明契约、容差、放宽路径与破坏性变化。

## 5. 验证与交付

- [x] 5.1 扩展 `tests/test_stock_montage.py`（比例过滤、变体选择、容差边界、幕级放宽、失败信息、记录过期与复核、实测尺寸）并新增 `tests/test_media_probe.py`。
- [x] 5.2 运行 `uv run pytest`、`sync_docs.py --check` 与 web 回归，检查暂存内容后提交。
- [ ] 5.3 重跑 `videos/stock-montage/pixabay-e2e-20261015`：检索、校验、准备、完整预演与正式导出，报告新旧素材尺寸与成片参数。
