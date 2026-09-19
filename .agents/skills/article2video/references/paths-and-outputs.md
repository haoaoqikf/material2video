# 目录约定与输出路径

每篇文章占一个稳定、唯一的目录名（slug，推荐小写英文与连字符）。文章标题变化不改目录名。

**文章内容不入库**：`videos/` 是作品内容（原文、分镜、专属网页），已在 `.gitignore` 中忽略；
仓库里保留的是制作方法与共享资产。文章既可以留在仓库的 `videos/` 下，也可以放在仓库之外的
**内容根**里，两种情况下的命令完全一致。

## 两层根

| 根 | 是什么 | 怎么确定 |
| --- | --- | --- |
| **仓库根**（repo root） | 存放 skill 与共享资产的仓库 | 输入文件向上查找 `.agents/skills/article2video/SKILL.md`；文件在仓库之外时取**正在运行的脚本**所在仓库 |
| **工作区根**（workspace root） | 存放 `videos\|examples/<slug>/` 与 `outputs/` 的目录 | 默认就是仓库根；设置了内容根时是内容根 |

内容根按下面的优先级确定，**不自动探测、不猜**：

1. 命令行 `--content-root <dir>`；
2. 环境变量 `A2V_CONTENT_ROOT=<dir>`；
3. 都没有 → 工作区根 = 仓库根。

内容根要与仓库同构：它下面直接放 `videos/<slug>/` 与 `outputs/<slug>/`（示例放
`examples/<slug>/`）。内容根里**不需要**也不应该有 skill 副本——共享页面与共享资产始终
用仓库里那一份。

## 目录结构

```text
<仓库根>/
├── .agents/skills/article2video/     # 制作方法、共享页面与共享资产（入库）
├── examples/<slug>/                  # 随仓库发布的示例（入库）
├── videos/<slug>/                    # 实际文章内容（不入库，见 .gitignore）
│   ├── article.md
│   ├── storyboard.json
│   ├── index.html                    # 专属网页路径需要；声明式路径可省略
│   └── assets/                       # 本篇专用素材，按需创建
└── outputs/<slug>/                   # 成片与中间产物（不入库）
    ├── silent.mp4                    # 最新无声成片
    ├── voiced.mp4                    # 最新配音成片
    ├── voiced.srt                    # 配音成片字幕
    ├── media/                        # 配音清单、音轨与缓存
    ├── previews/                     # 限帧试渲染，使用相同的成片文件名
    └── qa/                           # 验收截图等，按需创建
```

内容根在仓库之外时，`videos/<slug>/` 与 `outputs/<slug>/` 一起搬到内容根下，其余不变：

```text
<内容根>/
├── videos/<slug>/…
└── outputs/<slug>/…
```

`examples/<slug>/` 与 `videos/<slug>/` 同构，但产物放入 `outputs/examples/<slug>/`，
多一层 `examples/`，避免示例与实际文章同名时互相覆盖。

## 引用共享资产

页面要用共享样式与脚本，写法由页面位置决定：

| 页面位置 | 引用写法 | 例子 |
| --- | --- | --- |
| 仓库内（示例、仓库内文章） | 相对路径 | `../../.agents/skills/article2video/assets/figures.css` |
| 内容根内（仓库外文章） | 别名绝对路径 | `/__a2v__/figures.css` |

`/__a2v__/` 由渲染脚本启动的静态服务器挂到仓库的 `assets/` 目录上，因此内容根里的页面
不需要知道仓库在哪。别名只服务文件、不列目录，`..` 也不能穿出挂载目录。

skill bundle 自带页面（`assets/declarative.html`）保持相对引用：它本身就在 bundle 里，
相对路径经别名访问时同样成立。

## 归属推导

路径推导集中在 `scripts/a2v/paths.py`，命令行只负责参数默认值与报错。

1. 以输入文件位置向上查找含 `.agents/skills/article2video/SKILL.md` 的目录；找不到时
   取运行中的 bundle 所在仓库——共享资产被挂载的就是那一份；
2. 文件在仓库内直属的 `videos/<slug>/` 或 `examples/<slug>/` 时，工作区根即仓库根；
3. 否则用内容根作为工作区根，slug 取 `videos|examples/<slug>/` 里的目录名；
4. 专属网页路径以**本地网页**确定归属；声明式渲染、预览与配音准备以**分镜**确定归属；
5. 全程使用绝对路径，与执行命令时的工作目录无关。

推导失败时不猜归属，直接报错并要求显式指定输出路径：

| 情况 | 结果 |
| --- | --- |
| 找不到仓库根标记，且 bundle 不在仓库里 | 报错，提示需要显式指定输出路径 |
| 文件在仓库外、又没有内容根 | 报错，点名 `--content-root` 与 `A2V_CONTENT_ROOT` |
| 内容根里也没有 `videos|examples/<slug>/` | 报错，列出实际路径与它检查过的位置 |
| 远程网页（`http(s)://`） | 报错：无法确定归属 |
| `--page` 指向目录 | 报错：需要网页文件 |
| 省略 `--out` 且没有 `--storyboard` | 报错：无法确定成片文件名 |
| 媒体清单不在本篇文章的 `outputs/<slug>/media/` 内 | 报错，拒绝跨文章合成 |

## 默认输出

| 命令 | 省略输出参数时的位置 |
| --- | --- |
| `prepare.py --storyboard <json>` | `<工作区根>/outputs/<slug>/media/media.json`（含音轨与缓存） |
| `render.py --page <html> --storyboard <json>` | `<工作区根>/outputs/<slug>/silent.mp4` |
| `render.py --storyboard <json>` | `<工作区根>/outputs/<slug>/silent.mp4`（共享页面） |
| `render.py … --media <media.json>` | `<工作区根>/outputs/<slug>/voiced.mp4` 与同名 `.srt` |
| 上述渲染命令加 `--limit-frames N` | `<工作区根>/outputs/<slug>/previews/<同名成片>` |

文件名只由「是否提供 `--media`」决定：提供则 `voiced.mp4`，否则 `silent.mp4`。
分镜写了 `narration` 但没有传 `--media` 时保持 `silent.mp4`，并输出警告，
不会静默产出一个看似有声的文件；需要配音请先执行 `prepare.py`。

## 成片溯源

渲染成功后在成片旁写 `<同名>.provenance.json`，用于回答「这个成片是不是旧资产渲的」：

```json
{
  "version": 3,
  "workspace": "../..",
  "page": "__a2v__/declarative.html",
  "storyboard": "videos/<slug>/storyboard.json",
  "assets": { "files": { "__a2v__/figures.css": "…", "videos/<slug>/index.html": "…" } }
}
```

定位一律用**相对引用**：`workspace` 是产物目录到工作区根的相对路径，键相对工作区根记；
共享资产（含共享页面本身）在仓库的 `assets/` 里，记 `/__a2v__/` 别名键。这样溯源跟着成片
走，换机器、换目录、换内容根都读得回来，复核时也不需要 `--content-root` 或仓库标记。

`version` 不是 3 的溯源按「旧格式」处理：如实回答无法判断，不默认放行。

## 兼容与覆盖规则

- 显式 `--out`、`--out-dir` 始终优先，原有调用方式继续可用；
- 不设内容根时工作区根即仓库根，路径与产物位置与引入内容根之前一致；
- 同类重复导出覆盖固定文件（同一篇文章的 `silent.mp4` 只有一份）；
- 产物先生成、验收后替换，失败不会破坏上一份可用成片；
- 限帧试渲染写入 `previews/`，不会覆盖正式成片。

## 相关文档

- [配音与字幕](media-contract.md)：媒体清单字段、缓存与字幕规则
- [渲染契约](render-contract.md)：网页接口、确定性要求与渲染模式
