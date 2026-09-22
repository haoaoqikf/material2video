# Tasks

## 1. 媒体模块

- [x] 1.1 `media.py` 新增 `effective_storyboard(media)`：按媒体清单把每幕实际时长写回源分镜快照，返回派生分镜 dict。
- [x] 1.2 `media.py` 新增 `write_effective_storyboard(media, target_dir=None)`：落盘 `storyboard.effective.json`，默认写入媒体清单所在目录，返回路径。

## 2. 渲染入口

- [x] 2.1 `render.py` 的 `render_with_remotion`：`--media` 时在临时目录落盘有效分镜，`metadata` 与 `render_frames` 的 `props` 改用它；`bundle` 仍用原始分镜路径。

## 3. 预览与评审

- [x] 3.1 `cli.py` 的 `main_review`：`--media` 时落盘有效分镜并把 `a2v-storyboard` 指向媒体服务上的该文件；`a2v-media` 行为不变。
- [x] 3.2 `cli.py` 的 `main_preview`：同 3.1。

## 4. 文本换行与图表标签修复

- [x] 4.0 `web/src/styles/scene-tree.css`：文本原语 `.a2v-primitive-text` 启用 `white-space: pre-line`，让分镜换行符成为硬换行。
- [x] 4.0.1 `web/src/styles/scene-tree.css`：柱状图标签取标签档字号，图表容器底部留出标签带。
- [x] 4.0.2 新增样式契约测试，钉住换行与图表标签行为。
- [x] 4.0.3 重建契约页（`pnpm -C web build`）。

## 5. 回归测试

- [x] 5.1 `tests/test_media.py`：有效分镜派生使用延长时长、与源分镜不同。
- [x] 5.2 `tests/test_media.py`：落盘文件可解析、总帧数等于派生时间轴。
- [x] 5.3 `tests/test_media.py`：打桩 Remotion 环境后走 `render_with_remotion`，断言渲染 props 的总帧数等于派生时间轴、打包路径仍是原始分镜。

## 6. 文档同步

- [x] 6.1 `references/media-contract.md`：补充有效分镜文件的生成时机与用途。

## 7. 验证与归档

- [x] 7.1 `uv run pytest` 全量通过。
- [x] 7.2 实测：`render.py --media … --limit-frames 5` 成功；`review.py --media …` 不再出现空白帧误报。
- [x] 7.3 全量渲染成片并通过验收。
- [ ] 7.4 提交并按流程归档变更。
