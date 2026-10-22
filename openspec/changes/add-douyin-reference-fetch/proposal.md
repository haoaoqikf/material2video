## Why

制作前需要把抖音上的作品作为参考素材留存：手工下载无法复核来源与文件摘要，也容易把带水印或错误版本混进工作区。抖音的详情接口依赖页面即时生成的签名参数，自己逆向签名算法会长期受改版影响，因此需要一个只做「浏览器取详情、直链下载、写留证」的稳定入口。

## What Changes

- 新增 `m2v ref fetch <分享链接或分享文本>`：用 Playwright 打开抖音页面，读取页面自己请求得到的详情，下载视频或图文作品到 `refs/douyin/<作品ID>/`。
- 新增 `m2v ref verify <目录>`：按 `recipe.json` 校验文件 SHA-256 与字节数，报告缺失或被替换的文件。
- 每个参考素材目录包含媒体文件、`metadata.json`（作者、文案、发布时间、来源链接、实测尺寸）与 `recipe.json`（摘要留证）；默认不覆盖已有目录，`--force` 才替换。
- 不实现签名算法，不依赖第三方下载库；复用已有 Playwright 与 ffmpeg，离线渲染主链不变。
- 参考素材按内容处理，`refs/` 不进入版本控制；媒体只用于分析，不进入成片。

## Capabilities

### ADDED Capabilities

- `reference-media-acquisition`：从抖音分享链接获取视频或图文参考素材，并保存可校验的来源与摘要记录。

## Impact

- 新增 `src/m2v/reference/` 行为模块与 `ref` 子命令，`tests/test_reference_douyin.py` 覆盖离线解析与留证校验。
- 修改 `.gitignore` 忽略 `refs/`；README 补充命令与目录说明。
- 不新增 Python 依赖；Playwright 浏览器已由现有安装流程提供。网络与登录状态是运行时条件，缺失时给出可执行的诊断，不影响渲染。
