## Why

启用配音后（`--media`），画面时间轴必须使用媒体清单派生的延长时长。文档契约（`references/media-contract.md`）写明「composition 读取的分镜在渲染前由媒体清单派生（时长按口播延长）」「预览与导出均使用 `scenes` 中的派生时长」。但当前实现里，composition 拿到的 props 始终是原始分镜：

- **渲染**：`render.py` 只在内存里把模型换成媒体派生分镜，传给 Remotion 打包与渲染的 `--props` 仍是原始文件。总帧数交叉校验直接报「总帧数不一致：画面声明 1830 帧，分镜脚本累计 2059 帧」，有声渲染无法完成。
- **预览/评审**：契约页从 `a2v-storyboard` 加载原始分镜（声明时长），而体检按派生时长采样。错位的采样帧落到下一幕入场动效开始前的空窗，被机检判成「整帧几乎没有内容（墨迹 0.00%）」的假错误；预览的播放时长也与音轨不符。

实测复现：对 `videos/rest-not-reward` 执行 `render.py --media … --limit-frames 5` 报错退出；`review.py --media …` 在 `pressure` 幕 96% 与 `life` 幕 35% 两处抽帧报空白帧（同一帧的 DOM 探针却能读到全部文本）。

## What Changes

- 媒体模块新增派生分镜的单一出口：由媒体清单把每幕实际时长写回源分镜快照，生成「有效分镜」数据，并提供落盘辅助函数。
- 渲染入口在 `--media` 时把有效分镜落盘为临时 props 文件，`metadata` 与逐帧渲染都改用它；打包仍用原始分镜路径（代码场景清单与作品归属按原分镜解析）。
- 预览与评审在 `--media` 时把有效分镜写入媒体目录（`storyboard.effective.json`），契约页的 `a2v-storyboard` 指向该文件的媒体服务 URL；`a2v-media` 参数与音轨服务不变。
- 回归测试覆盖：有效分镜的派生与落盘、有声渲染传给 composition 的 props 总帧数与媒体派生时间轴一致。
- 修复场景树文本原语不 honored 分镜换行符的缺口：分镜文案里的 `\n` 在 HTML 里被折叠成空格，浏览器自动折行产生「吗」「分」这类单字孤行（视觉规范明确要求换行符是硬换行、由分镜决定断行位置）。文本原语改为 `white-space: pre-line`，让硬换行按分镜落位。
- 修复柱状图类别标签不可读的缺口：标签继承浏览器默认字号（约 16px，低于视觉规范 30px 下限）且落位与后续内容重叠。标签改取标签档字号（`--a2v-size-label`，34px），图表容器底部留出标签带。

## Capabilities

### Modified Capabilities

- `remotion-renderer`: 明确「带 `--media` 渲染/预览/评审时，composition 的 props 必须是媒体派生分镜」——这是把文档既有要求落进规格，防止再次回归。
- `scene-primitive-tree`: 明确文本原语的换行符语义——分镜文案中的换行符 SHALL 渲染为硬换行；柱状图类别标签 SHALL 使用可读字号且不与后续内容重叠。

## Impact

- `scripts/a2v/media.py`：新增派生与落盘辅助函数。
- `scripts/a2v/render.py`：`render_with_remotion` 在 `--media` 时改用临时 props 文件。
- `scripts/a2v/cli.py`：`main_preview` 与 `main_review` 在 `--media` 时改用媒体服务上的有效分镜 URL。
- `web/src/styles/scene-tree.css`：文本原语启用 `white-space: pre-line`；柱状图标签取标签档字号并留出标签带（需重建契约页）。
- `tests/test_media.py`：新增回归测试；新增场景树文本换行与图表标签可读性的契约测试。
- Skill 参考文档（`media-contract.md`）补充有效分镜文件的说明。
- 不改变：分镜 schema、媒体清单格式、命令行参数、无声渲染路径。
