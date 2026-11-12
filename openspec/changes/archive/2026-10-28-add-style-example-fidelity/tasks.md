## 1. 共享相机原语

- [x] 1.1 新建 `web/src/code-scene/painter/camera.ts`：导出 `cameraAt(keys, progress)`，缩放按对数空间插值、焦点按缩放反比加权、缓动缺省 `sineInOut`；纯函数，不读挂钟与随机源。在 `painter/index.ts` 导出并同步 `references/code-scene-runtime.md`。
- [x] 1.2 新建 `web/src/code-scene/painter/camera.test.ts`：同输入两次求值相等、进度 0/1 精确落在端点、`scale=1→4` 的中点返回 2、空表与越界进度明确报错。`pnpm -C web test` 全通过，既有 `painter.test.ts` 不回归。

## 5. 增补：跨幕时间、事件与分层范式

- [x] 5A.6 分层绘制范式：把 `background → under → paint → overlay` 的四层分工（实物不吃辉光、发光体吃辉光、文字锐利）写进 `code-scene-runtime.md`。

## 7. 文档与交付

- [x] 7.2 补勾 `openspec/changes/archive/2026-10-28-add-vibe-fable-style-and-examples/tasks.md` 的 4.2/4.3 并说明对应提交。
- [x] 7.3 验证：`uv run m2v validate`、`prepare`、`lookdev`、`pnpm -C web test`、`uv run pytest tests/test_vibe_fable_style.py tests/test_vibe_night_style.py`，确认 `examples/` 三个固定示例不回归。
- [x] 7.4 检查暂存范围（排除示例 `outputs/`、参考采样帧、生成媒体），提交实施；同步主规格并归档变更。

> 2026-11-12 内容清理：已删除用户指定作品的专属内容；本档案仅保留其余历史范围，不代表本轮重新验证。
