# 设计：媒体派生时间轴的单点修复

## 根因

`media.load_media` 已经构建了延长时长后的分镜模型（`Media.storyboard`），但只用于 Python 侧的数值推导：

- `render.py` 的 `render_with_remotion` 把 `storyboard` 换成 `media.storyboard` 后，`--props` 仍指向原始分镜文件，Remotion 按声明时长注册 composition，总帧数交叉校验必然失败。
- `cli.py` 的 `main_review` / `main_preview` 让契约页从 `a2v-storyboard` 加载原始分镜，页面时间轴是声明时长；而 `inspect.scene_windows` 按 `media.storyboard` 的起止采样。两侧时间轴错位，采样帧可能落进下一幕的入场空窗（动效从第 8–10 帧才开始），截出整帧空白。

## 方案取舍

**候选 A：契约页自己读取 `a2v-media` 并合并时长。** 被否决：契约页是构建产物，改 web 侧要动 React 代码、重建契约页并同步 web 测试；而且「时长在脚本侧派生」是既有文档口径（media-contract.md：预览与导出均使用 `scenes` 中的派生时长，不在网页重新估算），让页面再算一遍会引入第二个真源。

**候选 B（采用）：Python 侧物化「有效分镜」props。** 媒体清单里已有全部信息（`source` 快照 + 每幕实际 `durationInFrames`），写回生成一份 JSON 即可；契约页与 Remotion 都只认 props 文件，无需感知媒体的存在。单一真源仍是媒体清单，派生是纯函数。

## 细节

- `media.effective_storyboard(media)`：`deepcopy(media.data["source"])`，按序把 `media.data["scenes"][i]["durationInFrames"]` 写回。`load_media` 已校验场景数量、ID 与「实际时长 ≥ 声明时长」，派生无需重复校验。
- `media.write_effective_storyboard(media, target_dir=None)`：落盘为 `storyboard.effective.json`；默认目录是媒体清单所在目录（预览/评审用它，恰好已被带 CORS 的媒体服务覆盖）；渲染传入渲染输出旁的临时目录，随临时目录销毁。
- 渲染：`bundle(storyboard_path=原始路径)` 保持不变——代码场景清单、作品归属、安全边界检查都按原分镜与文章目录解析；只有 `metadata(props=…)` 与 `render_frames(props=…)` 换成有效分镜文件。溯源仍记录原始分镜 URL。
- 预览/评审：`a2v-storyboard` 指向媒体服务上的 `storyboard.effective.json`（绝对 URL，跨端口靠媒体服务已开启的 CORS）；`a2v-media` 参数原样保留。契约页只读 `a2v-storyboard`，`a2v-media` 对它是无操作，不破坏任何既有行为。
- 命名用 `storyboard.effective.json` 而不是 `effective.json`：落在 `outputs/<slug>/media/` 里，名字要能自证内容。
- 无声路径（无 `--media`）逐字节不变：不写文件、不改 URL。

## 风险

- 媒体目录新增一个派生文件：`prepare.py` 不会清理它，但媒体清单过期时它随下一次预览/评审重写，不参与指纹校验，无陈旧风险。
- `Media` 数据类不加字段：派生函数从 `media.data` 现算，避免破坏既有的手工构造调用点。
