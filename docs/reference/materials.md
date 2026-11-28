# 素材、署名与作品存储

本文件从 README 下沉，权威内容仍以 [`.agents/skills/material2video/references/`](../../.agents/skills/material2video/references/) 为准。具体见[素材检索与采用](../../.agents/skills/material2video/references/material-sourcing.md)、[媒体和声音契约](../../.agents/skills/material2video/references/article-media-and-sound.md)、[目录约定](../../.agents/skills/material2video/references/paths.md)。

## 素材采用与署名

当前不支持以口播为主线、配实拍或外部素材剪辑成片的形态。

人物不设默认限制。按本项目的素材采用政策，只有权利人明确禁止当前用途才不用，平台条款等作为风险记录。画面标注、片尾编排及必要署名见[素材采用与署名](../../.agents/skills/material2video/references/material-sourcing.md#5-采用政策与署名)。

## 导入与核查

用 `m2v author assets import` 导入选定画面并写入 `assets/media-sources.json`。用 `m2v assets report` 核对台账，`contact-sheet` 核对候选，`audit` 检查登记文件。音效使用作品自己的配方和 `setup`。具体见[媒体和声音契约](../../.agents/skills/material2video/references/article-media-and-sound.md)。

Pexels 是可用的图片和视频素材来源。选定素材后，把公开媒体直链填入 `mediaUrl`，由 `m2v author assets import` 下载并留证，无需 API Key。操作见 [Pexels 导入示例](../../.agents/skills/material2video/references/material-sourcing.md#pexels-公开媒体直链)。

## 按需使用素材工作库

需要批量发现、索引、语义检索、精裁、跨作品整理或本地浏览时，按[素材工作库](../../.agents/skills/material2video/references/material-sourcing.md#完整工作层发现获取索引检索预览选择)选择相应命令。索引和查找离线运行，模型须显式恢复。

## 缓存与目录

字体按[字体登记](../../fonts/registry.json)恢复并校验，字体二进制由 Git 忽略。

Remotion 构建缓存按使用时间保留最近 8 份，并保护正在渲染或取帧的构建。场景录制与合成共用片段缓存上限，成功编码后即回收对应中间帧，并按进程启动身份回收中断录制。文件位置和清理范围见[目录约定](../../.agents/skills/material2video/references/paths.md#构建与录制缓存)。

`uv run m2v storage inventory` 盘点仓库内作品与示例，可用 `--project` 指定单个工程或用 `--content-root` 纳入仓库外作品。清理中断录制、封存评审媒体和恢复隔离副本的操作见[作品存储](../../.agents/skills/material2video/references/paths.md#清理预览与执行)。

示例生成媒体与作品 `outputs/` 由 Git 忽略。下载素材在所在示例的 `assets/recipe.json` 登记，恢复入口见[随附示例](../../examples/README.md)。
