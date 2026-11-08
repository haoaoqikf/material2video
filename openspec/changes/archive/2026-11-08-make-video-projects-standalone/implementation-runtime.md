# 本地运行基础实施记录

本记录对应任务 2.2–2.7：模板内的宿主、受控时钟、异步绘制、worker、场景构建、字体与媒体恢复、时间轴、字幕、声音、采集、合成、编码与技术检查。七例逐例结果另见[示例记录](implementation-examples.md)。

## 实现范围

- 受控时钟与宿主：`src/code-scene/capture-clock.js`、`host.tsx`、`frame-tasks.ts`、`context.ts` 与 `src/runtime/offline-guard.ts`。宿主在资源与字体就绪后开始录制，逐帧等待异步绘制；拒绝、超时、乱序与重叠提交均失败。
- 多进程：`runtime/python/film_runtime/types/scene_film/code_scenes/worker.py` 从作品环境启动，分块采集并复用内容寻址片段缓存。
- 场景构建：`scripts/build-code-scene.mjs` 只解析作品内相对导入与作品 `package.json` 声明的精确版本；拒绝 `m2v/*`、绝对路径、越界链接和父目录依赖兜底，并把实际构建输入写入摘要清单。
- 字体与媒体：`fonts/registry.json`、`fonts/fetch.py`、`scripts/sync-fonts.mjs`、`assets/fetch.py` 与 `core/example_media.py`；缺失或摘要不符明确失败，不覆盖已有正确文件。
- 时间轴与声音：`types/scene_film/explainer_prepare.py`、`sound_library.py`、`soundtrack.py`、`subtitles.py` 与 `engine/audio.py` 在本作品内完成旁白测量、事件窗口、字幕和混音准备。
- 采集与交付：`types/scene_film/code_scenes/capture.py`、`engine/render_pipeline.py`、`remotion/`、`core/delivery.py`；候选在私有暂存目录完成完整解码与技术核验后才发布，失败不替换原成片。
- 本地工具：`engine/lookdev.py` 新增 `lookdev` 与 `materialize` 本地命令，供主项目读取本地产物；`scripts/build-review-player.mjs` 与 `src/production/player.tsx` 提供本作品的时间线播放器。

## 验证

- `tests/standalone/` 覆盖纯时间源检查、候选搬移、旧契约拒绝、执行协议、进程树清理、管理绑定、样品复核、脚手架清单与本地 lookdev 路径边界；本轮运行 126 项通过。
- `src/code-scene/frame-tasks.test.ts` 覆盖异步等待、拒绝、重叠提交、thenable 与绘制屏障；七例真实构建都通过 `tsc --noEmit` 与 Vite 生产构建。
- 七例本地 `fonts/fetch.py` 恢复 2–22 项字体；`compound-connect` 恢复 20 个 KaTeX WOFF2。缺失字体或摘要不符时恢复与构建明确失败。
- 七例分别完成本地 `setup`、`validate`、`prepare`、完整 `render` 与本地 `qa`；结果见[示例记录](implementation-examples.md)。真实导出覆盖无音轨、事件声、旁白、字幕、转场、三维异步绘制与真实媒体。
- 仓库外含空格目录 `m2v-standalone-final/a folder/renamed-video` 在无主项目 PYTHONPATH、无共享 `node_modules` 的条件下重新安装并构建，完成本地 setup、5 帧预览、完整 90 帧导出、原生样品采集与技术检查；成片 SHA-256 `b270318287e9f09daabec5998fc0a713be169ce48c48e462401fd45952040aa5`，QA `pass`；记录保存在忽略的 `.cache/standalone-verification/final-base.json`。
- `m2v render/qa` 委托本地入口，主项目独立复核实际视频、摘要、准备身份和技术范围；`lookdev` 与 `review timeline` 通过本地 `lookdev`／`materialize` 命令读取本地产物。

## 边界

- POSIX 进程树、跨 GPU 逐字节一致性和首次恢复无网络均不在本机验证范围；作品说明与 README 保留这些前提。
- 三维与真实媒体示例的完整导出已在当前机器完成；跨硬件一致性和主观听感仍按既有评审门禁另行判断。
