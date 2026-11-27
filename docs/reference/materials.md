# 素材、署名与作品存储

本文件从 README 下沉，权威内容仍以 [`.agents/skills/material2video/references/`](../../.agents/skills/material2video/references/) 为准。具体见[素材检索与采用](../../.agents/skills/material2video/references/material-sourcing.md)、[媒体和声音契约](../../.agents/skills/material2video/references/article-media-and-sound.md)、[目录约定](../../.agents/skills/material2video/references/paths.md)。

## 素材采用与署名

口播配实拍或外部素材使用 `documentary-edit`。逐段匹配文案里的对象、动作、过程与情绪，通用画面优先查 Pexels 和 Pixabay，按缺口扩展到其他公开来源。具体事实优先核对原件，选材见[制作指导](../../.agents/skills/material2video/references/visual-material-selection.md#观点旁白与意境素材)。

人物不设默认限制。按本项目的素材采用政策，只有权利人明确禁止当前用途才不用，平台条款等作为风险记录。画面标注、片尾编排及必要署名见[素材采用与署名](../../.agents/skills/material2video/references/material-sourcing.md#5-采用政策与署名)。

## 素材工作层

创作辅助命令为 `m2v author`：源文审查、候选稿、素材导入和音效操作分别见 `m2v author --help` 与[媒体和声音契约](../../.agents/skills/material2video/references/article-media-and-sound.md)。外部画面素材使用 `assets/media-sources.json` 留证；`m2v assets report`、`contact-sheet`、`audit` 用于台账和技术检查。字体二进制按 [`fonts/registry.json`](../../fonts/registry.json) 恢复并校验，不纳入 Git。

Pexels 是可用的图片和视频素材来源。选定素材后，把公开媒体直链填入 `mediaUrl`，由 `m2v author assets import` 下载并留证，无需 API Key。操作见 [Pexels 导入示例](../../.agents/skills/material2video/references/material-sourcing.md#pexels-公开媒体直链)。

`m2v author assets` 另有 discover / fetch / index / find / preview / select / library / models / doctor 九个工作流，覆盖无分镜发现、受控公开/平台/本地获取、字幕/转录/OCR/镜头/文本/视觉索引、中文检索与候选预览、精裁选择和作品内凭据。索引/查找离线运行，模型必须显式 `models prepare`；完整教程与能力边界见[素材工作层](../../.agents/skills/material2video/references/material-sourcing.md#完整工作层发现获取索引检索预览选择)。`search`/`import` 行为保持不变，Pexels API 仍停用。

素材库支持全时间轴预算采样、可继续的流式增量扫描、来源标题/描述的跨语言语义检索及背景负例筛选；同次请求复用查询编码。`library annotate/list/similar/browse` 提供标签、收藏、主题集合、已有视觉索引的相似镜头建议和显式多库本地浏览。相似建议不合并来源或删除文件，动作与身份仍需观察。

## 缓存与目录

Remotion 构建缓存按使用时间保留最近 8 份，并保护正在渲染或取帧的构建。场景录制与合成共用片段缓存上限，成功编码后即回收对应中间帧，并按进程启动身份回收中断录制。文件位置和清理范围见[目录约定](../../.agents/skills/material2video/references/paths.md#构建与录制缓存)。

`uv run m2v storage inventory` 盘点仓库内作品与示例，可用 `--project` 指定单个工程或用 `--content-root` 纳入仓库外作品。清理中断录制、封存评审媒体和恢复隔离副本的操作见[作品存储](../../.agents/skills/material2video/references/paths.md#清理预览与执行)。

示例生成媒体与作品 `outputs/` 由 Git 忽略。下载素材在所在示例的 `assets/recipe.json` 登记，恢复入口见[随附示例](../../examples/README.md)。
