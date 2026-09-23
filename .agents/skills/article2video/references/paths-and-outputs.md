# 目录约定与输出路径

每篇文章占一个稳定、唯一的目录名（slug，推荐小写英文与连字符）。文章标题变化不改目录名。

**文章内容不入库**：`videos/` 是作品内容（原文、分镜、专属画面模块），已在 `.gitignore` 中忽略；
仓库里保留的是制作方法与共享画面工程。文章既可以留在仓库的 `videos/` 下，也可以放在仓库之外的
**内容根**里，两种情况下的命令完全一致。

## 两层根

| 根 | 是什么 | 怎么确定 |
| --- | --- | --- |
| **仓库根**（repo root） | 存放 skill 与共享画面工程（`web/`）的仓库 | 输入文件向上查找 `.agents/skills/article2video/SKILL.md`；文件在仓库之外时取**正在运行的脚本**所在仓库 |
| **工作区根**（workspace root） | 存放 `videos\|examples/<slug>/` 及作品产物的目录 | 默认就是仓库根；设置了内容根时是内容根 |

内容根按下面的优先级确定，**不自动探测、不猜**：

1. 命令行 `--content-root <dir>`；
2. 环境变量 `A2V_CONTENT_ROOT=<dir>`；
3. 都没有 → 工作区根 = 仓库根。

内容根要与仓库同构：它下面直接放 `videos/<slug>/`，产物位于文章目录下的 `outputs/`（示例源放
`examples/<slug>/`，产物位于 `videos/examples/<slug>/outputs/`）。内容根里**不需要**也不应该有 skill 副本——画面由仓库里
`web/` 的共享 composition 提供，契约页在渲染与体检时按仓库根自动定位并挂载。

## 目录结构

```text
<仓库根>/
├── .agents/skills/article2video/     # 制作方法与参考文档（入库）
├── web/                              # 共享画面工程：组件、令牌、composition（入库）
├── examples/<slug>/                  # 随仓库发布的示例（入库）
├── videos/<slug>/                    # 实际文章内容（不入库，见 .gitignore）
│   ├── article.md
│   ├── storyboard.json
│   ├── scenes/                       # 代码场景模块（renderer.code），按需创建
│   └── assets/                       # 本篇专用素材，按需创建
└── videos/<slug>/outputs/            # 成片与中间产物（不入库）
    ├── silent.mp4                    # 最新无声成片
    ├── voiced.mp4                    # 最新配音成片
    ├── voiced.srt                    # 配音成片字幕
    ├── media/                        # 配音清单、音轨与缓存
    ├── previews/                     # 限帧试渲染，使用相同的成片文件名
    └── qa/                           # 验收截图等，按需创建
```

内容根在仓库之外时，`videos/<slug>/` 与其下的 `outputs/` 一起搬到内容根下，其余不变：

```text
<内容根>/
├── videos/<slug>/…
└── videos/<slug>/outputs/…
```

`examples/<slug>/` 与 `videos/<slug>/` 同构，但产物放入 `videos/examples/<slug>/outputs/`，
多一层 `examples/`，避免示例与实际文章同名时互相覆盖。

## 画面来自哪里

画面不再是一张作品自己的 HTML：渲染入口把分镜交给仓库 `web/` 里的共享
React composition（Remotion），由场景树递归解释器按分镜逐幕绘制。
需要新表达时按原语注册表流程新增通用原语；个别幕需要独特的图表面板、
关系图或定制 SVG 时，可以在该幕声明 `renderer.code`，模块放在作品目录的
`scenes/` 下（`videos/<slug>/scenes/` 或 `examples/<slug>/scenes/`，与分镜同目录），
本地资产放 `assets/`。模块契约与纪律见 [代码场景](code-scenes.md)。

本篇专用素材（`videos/<slug>/assets/`）由静态服务器按工作区根提供，
composition 里经相对 URL 引用；仓库 `web/` 自身的源码与字体则通过
`/__a2v_web__/` 别名挂载，内容根在仓库之外时同样可达。
代码场景的本地资产用打包器导入（`import markUrl from '../assets/mark.png'`），
构建时随作品源码一起进入依赖白名单检查与指纹。

## 归属推导

路径推导集中在 `scripts/a2v/paths.py`，命令行只负责参数默认值与报错。

1. 以输入文件位置向上查找含 `.agents/skills/article2video/SKILL.md` 的目录；找不到时
   取运行中的 bundle 所在仓库——契约页与 composition 从那一份取；
2. 文件在仓库内直属的 `videos/<slug>/` 或 `examples/<slug>/` 时，工作区根即仓库根；
3. 否则用内容根作为工作区根，slug 取 `videos|examples/<slug>/` 里的目录名；
4. 渲染、预览、体检与配音准备都以**分镜**确定归属；
5. 全程使用绝对路径，与执行命令时的工作目录无关。

推导失败时不猜归属，直接报错并要求显式指定输出路径：

| 情况 | 结果 |
| --- | --- |
| 找不到仓库根标记，且 bundle 不在仓库里 | 报错，提示需要显式指定输出路径 |
| 文件在仓库外、又没有内容根 | 报错，点名 `--content-root` 与 `A2V_CONTENT_ROOT` |
| 内容根里也没有 `videos|examples/<slug>/` | 报错，列出实际路径与它检查过的位置 |
| 省略 `--out` 且没有 `--storyboard` | 报错：无法确定成片文件名 |
| 媒体清单不在本篇文章的 `videos/<slug>/outputs/media/` 内 | 报错，拒绝跨文章合成 |

## 默认输出

| 命令 | 省略输出参数时的位置 |
| --- | --- |
| `prepare.py --storyboard <json>` | `<工作区根>/videos/<slug>/outputs/media/media.json`（含音轨与缓存） |
| `render.py --storyboard <json>` | `<工作区根>/videos/<slug>/outputs/silent.mp4` |
| `render.py … --media <media.json>` | `<工作区根>/videos/<slug>/outputs/voiced.mp4` 与同名 `.srt` |
| 上述渲染命令加 `--limit-frames N` | `<工作区根>/videos/<slug>/outputs/previews/<同名成片>` |

文件名只由「是否提供 `--media`」决定：提供则 `voiced.mp4`，否则 `silent.mp4`。
分镜写了 `narration` 但没有传 `--media` 时保持 `silent.mp4`，并输出警告，
不会静默产出一个看似有声的文件；需要配音请先执行 `prepare.py`。

## 成片溯源

渲染成功后在成片旁写 `<同名>.provenance.json`，用于回答「这个成片是不是旧画面渲的」：

```json
{
  "version": 4,
  "renderer": "remotion",
  "workspace": "../..",
  "renderedAt": "2026-09-20T12:00:00+00:00",
  "page": "__a2v_web__/.gen/active-composition.tsx",
  "storyboard": "videos/<slug>/storyboard.json",
  "frames": 300, "fps": 30, "width": 1080, "height": 1920,
  "captureFormat": "remotion",
  "assets": { "files": { "__a2v_web__/src/registry/registry.json": "…" }, "digest": "…" }
}
```

定位一律用**相对引用**：`workspace` 是产物目录到工作区根的相对路径，键相对工作区根记；
构建输入（composition 源码、注册表、令牌与字体清单）在仓库的 `web/` 里，记
`/__a2v_web__/` 别名键。这样溯源跟着成片走，换机器、换目录、换内容根都读得回来，
复核时也不需要 `--content-root` 或仓库标记。

`version` 不是 3 或 4 的溯源按「旧格式」处理：如实回答无法判断，不默认放行。

## 兼容与覆盖规则

- 显式 `--out`、`--out-dir` 始终优先，原有调用方式继续可用；
- 不设内容根时工作区根即仓库根，路径与产物位置与引入内容根之前一致；
- 同类重复导出覆盖固定文件（同一篇文章的 `silent.mp4` 只有一份）；
- 产物先生成、验收后替换，失败不会破坏上一份可用成片；
- 限帧试渲染写入 `previews/`，不会覆盖正式成片。

## 相关文档

- [配音与字幕](media-contract.md)：媒体清单字段、缓存与字幕规则
- [渲染契约](render-contract.md)：网页接口、确定性要求与渲染模式
