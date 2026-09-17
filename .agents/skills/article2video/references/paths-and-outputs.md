# 目录约定与输出路径

每篇文章占一个稳定、唯一的目录名（slug，推荐小写英文与连字符）。文章标题变化不改目录名，
源文件纳入 Git，生成产物统一忽略。

## 目录结构

```text
videos/<slug>/
├── article.md
├── storyboard.json
├── index.html              # 专属网页路径需要；声明式路径可省略
└── assets/                 # 本篇专用素材，按需创建

outputs/<slug>/
├── silent.mp4              # 最新无声成片
├── voiced.mp4              # 最新配音成片
├── voiced.srt              # 配音成片字幕
├── media/                  # 配音清单、音轨与缓存
│   ├── media.json
│   ├── cache/
│   └── …                   # 生成资源保持既有命名
├── previews/               # 限帧试渲染，使用相同的成片文件名
└── qa/                     # 验收截图等，按需创建
```

`examples/<slug>/` 与 `videos/<slug>/` 同构，但产物放入 `outputs/examples/<slug>/`，
多一层 `examples/`，避免示例与实际文章同名时互相覆盖。

## 归属推导

路径推导集中在 `scripts/a2v/paths.py`，命令行只负责参数默认值与报错。

1. 以输入文件位置向上查找含 `.agents/skills/article2video/SKILL.md` 的目录，作为项目根；
2. 在该根下识别直属的 `videos/<slug>/` 或 `examples/<slug>/`，slug 即目录名；
3. 专属网页路径以**本地网页**确定归属；声明式渲染、预览与配音准备以**分镜**确定归属；
4. 全程使用绝对路径，与执行命令时的工作目录无关。

推导失败时不猜归属，直接报错并要求显式指定输出路径：

| 情况 | 结果 |
| --- | --- |
| 找不到项目根标记 | 报错，提示需要显式指定输出路径 |
| 网页或分镜不在 `videos/<slug>/`、`examples/<slug>/` 内 | 报错，列出实际路径 |
| 远程网页（`http(s)://`） | 报错：无法确定归属 |
| `--page` 指向目录 | 报错：需要网页文件 |
| 省略 `--out` 且没有 `--storyboard` | 报错：无法确定成片文件名 |
| 媒体清单不在本篇文章的 `outputs/<slug>/media/` 内 | 报错，拒绝跨文章合成 |

## 默认输出

| 命令 | 省略输出参数时的位置 |
| --- | --- |
| `prepare.py --storyboard <json>` | `outputs/<slug>/media/media.json`（含音轨与缓存） |
| `render.py --page <html> --storyboard <json>` | `outputs/<slug>/silent.mp4` |
| `render.py --storyboard <json>` | `outputs/<slug>/silent.mp4`（共享页面） |
| `render.py … --media <media.json>` | `outputs/<slug>/voiced.mp4` 与同名 `.srt` |
| 上述渲染命令加 `--limit-frames N` | `outputs/<slug>/previews/<同名成片>` |

文件名只由「是否提供 `--media`」决定：提供则 `voiced.mp4`，否则 `silent.mp4`。
分镜写了 `narration` 但没有传 `--media` 时保持 `silent.mp4`，并输出警告，
不会静默产出一个看似有声的文件；需要配音请先执行 `prepare.py`。

## 兼容与覆盖规则

- 显式 `--out`、`--out-dir` 始终优先，原有调用方式继续可用；
- 同类重复导出覆盖固定文件（同一篇文章的 `silent.mp4` 只有一份）；
- 产物先生成、验收后替换，失败不会破坏上一份可用成片；
- 限帧试渲染写入 `previews/`，不会覆盖正式成片。

## 相关文档

- [配音与字幕](media-contract.md)：媒体清单字段、缓存与字幕规则
- [渲染契约](render-contract.md)：网页接口、确定性要求与渲染模式
