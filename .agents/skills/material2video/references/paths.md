# 目录约定与输出路径

> **适用范围：** 本文描述作品目录的归属与输出路径：两层根、内容根、目录结构、画面来源、
> 归属推导、默认输出与兼容覆盖规则。交付权限、成片溯源、渲染性能报告与候选保留见
> [交付与溯源](delivery-and-provenance.md)；准备记录字段见[准备记录与字幕](prepared-and-subtitles.md)，
> 渲染引擎见[渲染引擎](render-engine.md)。

每篇文章占一个稳定、唯一的目录名（slug，推荐小写英文与连字符）。文章标题变化不改目录名。

**文章内容不入库**：`videos/` 是作品内容（原文、分镜、媒体素材），已在 `.gitignore` 中忽略；
仓库里保留的是制作方法与共享画面工程。文章既可以留在仓库的 `videos/` 下，也可以放在仓库之外的
**内容根**里，两种情况下的命令完全一致。

`styles/<id>/examples/<slug>/` 中的风格示例媒体也不入库：各示例的 `assets/fetch.py` 按 `assets/recipe.json` 下载或生成，
逐项校验登记摘要与实测尺寸、时长；公共字体及其许可继续随仓库分发。

## 两层根

`init` 从类型材料模板派生项目输出画幅：general 的 `project.json` 与 v8 分镜均默认1920×1080横屏；专用类型保留各自模板画幅。已有作品不会被初始化过程改写，切换画幅须同时检查作品与分镜声明。

| 根 | 是什么 | 怎么确定 |
| --- | --- | --- |
| **仓库根**（repo root） | 存放 skill 与共享画面工程（`web/`）的仓库 | 输入文件向上查找 `.agents/skills/material2video/SKILL.md`；文件在仓库之外时取**正在运行的脚本**所在仓库 |
| **工作区根**（workspace root） | 存放 `videos/<type>/<slug>/`、`styles/<style-id>/examples/<slug>/` 及作品产物的目录 | 默认就是仓库根；设置了内容根时是内容根 |

内容根按下面的优先级确定，**不自动探测、不猜**：

1. 命令行 `--content-root <dir>`；
2. 环境变量 `M2V_CONTENT_ROOT=<dir>`；
3. 都没有 → 工作区根 = 仓库根。

内容根要与仓库同构：它下面直接放 `videos/<type>/<slug>/`，产物位于作品目录下的 `outputs/`（仓库风格示例源放
`styles/<style-id>/examples/<slug>/`，产物位于 `styles/<style-id>/examples/<slug>/outputs/`）。内容根里**不需要**也不应该有 skill 副本——画面由仓库里
`web/` 的共享 composition 提供，契约页在渲染与体检时按仓库根自动定位并挂载。

## 目录结构

```text
<仓库根>/
├── .agents/skills/material2video/     # 制作方法与参考文档（入库）
├── web/                              # 共享画面工程：组件、令牌、composition（入库）
├── styles/<style-id>/examples/<slug>/ # 随仓库发布的风格示例（入库；媒体与产物除外）
├── videos/<type>/<slug>/             # 实际文章内容（不入库，见 .gitignore）
│   ├── article.md                    # article 输入的源文，可改用 article.accepted.md；topic 输入省略
│   ├── storyboard.json               # general 的 v8 全画布代码分镜
│   ├── scenes/                       # general 代码场景的本地 TSX 入口，按需创建
│   ├── assets/media/                 # 已导入并留证的内容寻址素材，按需创建
│   └── assets/                       # 本篇专用素材（音床、音效、代码场景资源），按需创建
└── videos/<type>/<slug>/outputs/     # 成片与中间产物（不入库）
    ├── video.mp4                     # 正式成片（所有类型同名；文件名由渲染器决定，不随有无配音变化）
    ├── video.provenance.json         # 与该成片同名的溯源记录
    ├── video.performance.json        # 与该成片同名的渲染性能报告
    ├── prepared.json                 # 当前准备产物与派生时间轴
    ├── input-review.json             # 文章讲解的人工输入语义审查（general）
    ├── review.json                   # 可选人工画面评审，绑定当前准备指纹与候选文件摘要（general）
    ├── layout-check.json             # 最近一次布局量测的三项硬判定结论（general）
    ├── reading-pace.json             # 逐条字幕的阅读速度与超限清单，只报告不阻断（general）
    ├── media/                        # 配音清单、音轨与缓存
    ├── audio-cache/                  # 逐段语音缓存（键含媒体契约版本）
    ├── code-cache/                   # general 代码场景的录制片段与摘要，按内容摘要命名
    ├── previews/                     # 可选片段检查；成功交付后清理
    └── qa/                           # `m2v general keyframes` 的字幕量测截图，按需创建
```

当前没有 `.srt` 写出器：字幕烧录进画面，不导出外置字幕文件。旧版曾写出
`silent.mp4` / `voiced.mp4` / `voiced.srt`，统一入口后只有 `video.mp4` 一个名字。

打包缓存不在作品目录里，而在共享工程下：`web/.cache/m2v-bundles/<键>/`。
它只与「当前 `web/` 源码 + 当前作品输入 + 依赖版本」有关，跨作品共享，整目录可随时删除。

内容根在仓库之外时，`videos/<type>/<slug>/` 与其下的 `outputs/` 一起搬到内容根下，其余不变：

```text
<内容根>/
├── videos/<type>/<slug>/…
└── videos/<type>/<slug>/outputs/…
```

`styles/<style-id>/examples/<slug>/` 是仓库风格示例源；`m2v --project styles/<style-id>/examples/<slug>/` 使用其中的材料，
全部产物（准备记录、媒体缓存、预演、成片与评审）统一落到 `styles/<style-id>/examples/<slug>/outputs/`。
该产物目录同样由 `.gitignore` 的 `outputs/` 规则忽略，不入库。
需要把示例作为独立作品制作时，把示例目录整体复制到 `videos/<type>/<slug>/`。

## 画面来自哪里

画面不再是一张作品自己的 HTML：渲染入口把分镜交给仓库 `web/` 里的共享
React composition（Remotion）。三个类型各有自己的 composition，都在 `web/src/compositions/` 下，
由 `web/src/Root.tsx` 注册。
general 的 v8 分镜每一幕都是作品 `scenes/` 下的本地 React 组件：画面在 prepare 阶段按画幅实时
录成无声片段，`ArticleExplainer` 只负责回放这些片段并叠加共享字幕（片段经回环 HTTP 取），
契约见 [通用分镜 v8](storyboard-schema.md)。

本篇专用素材（`videos/<type>/<slug>/assets/`）由静态服务器按工作区根提供，
composition 里经相对 URL 引用；仓库 `web/` 自身的源码与字体则通过
`/__m2v_web__/` 别名挂载，内容根在仓库之外时同样可达。

## 归属推导

新制作以 `--project` 确定作品归属，材料路径相对于作品根；归属推导与内容根判定共用 `src/m2v/core/workspace.py`。

1. 以输入文件位置向上查找含 `.agents/skills/material2video/SKILL.md` 的目录；找不到时
   取运行中的 bundle 所在仓库——契约页与 composition 从那一份取；
2. 文件在仓库内的 `videos/<type>/<slug>/` 或 `styles/<style-id>/examples/<slug>/` 时，工作区根即仓库根；
3. 否则用内容根作为工作区根，slug 取 `videos/<type>/<slug>/` 的最后一级目录名；
4. 新制作入口以 `project.json` 确定类型和材料；文章辅助流程从 `videos/general/<slug>/` 分镜路径推导作品归属；
5. 全程使用绝对路径，与执行命令时的工作目录无关。

推导失败时不猜归属，直接报错并要求显式指定输出路径：

| 情况 | 结果 |
| --- | --- |
| 找不到仓库根标记，且 bundle 不在仓库里 | 报错，提示需要显式指定输出路径 |
| 文件在仓库外、又没有内容根 | 报错，点名 `--content-root` 与 `M2V_CONTENT_ROOT` |
| 内容根里也没有 `videos/<type>/<slug>/` | 报错，列出实际路径与它检查过的位置 |
| 缺失 `project.json` 或类型材料 | 指出作品目录或缺失材料，停止后续制作 |
| 准备记录、资产或渲染代码指纹已变化 | 要求重新 prepare，再生成预演与评审 |

## 默认输出

| 命令 | 省略输出参数时的位置 |
| --- | --- |
| `m2v prepare --project <目录>` | `<作品目录>/outputs/prepared.json` 与类型专属生成材料 |
| `m2v preview --project <目录>` | `<作品目录>/outputs/previews/` 下的当前预演 |
| `m2v render --project <目录>` | `<作品目录>/outputs/` 下类型默认的正式成片 |
| `m2v preview --project <目录> --limit-frames N` | 调试用途；严格短于全片，不参与交付门禁 |

general 正式成片为 `outputs/video.mp4`，片段为 `outputs/previews/video.mp4`；金融与住宅沿用各自类型文件名；
文件名不随有无配音变化（没有音轨时渲染的是无声画面，名字不变）。由 `project.json`
解析材料与输出位置，不通过旧式 `--media` 或输出路径参数切换制作归属。
v8 分镜不接受字符串 `narration`（口播写在 `narrationSegments`），所以不存在
「写了旁白却没配音」的中间态：需要配音请先执行 `uv run m2v prepare --project <目录>`。

## 兼容与覆盖规则

- 输出归属由 `--project` 唯一确定；类型内部临时文件在验收后原子替换默认输出；
- 不设内容根时工作区根即仓库根，路径与产物位置与引入内容根之前一致；
- 同类重复导出覆盖固定文件（同一篇文章的 `silent.mp4` 只有一份）；
- 产物先生成、验收后替换，失败不会破坏上一份可用成片；
- `render` 只读取作品材料与准备记录，不修改原始材料；
- 统一入口正式渲染成功后清理本作品 `outputs/` 中旧视频及其字幕/溯源/性能旁车、预演、检查图和已知调试目录；保留本次成片及旁车、`prepared.json`、评审 JSON 和 `media/` 准备媒体。渲染或验收失败不清理，仓库共享构建缓存不受影响；清理错误按遗留路径报告；
- 限帧试渲染写入 `previews/`，不会覆盖正式成片。
- 旧统一作品使用 `m2v relocate --project videos/<slug>` 逐个迁移；命令先完整备份，同路径冲突不覆盖目标文件，可处理后重试。`m2v migrate --from financial` 只用于旧金融材料契约迁移。

## 相关文档

- [交付与溯源](delivery-and-provenance.md)：交付权限、成片溯源、渲染性能报告与候选保留
- [准备记录与字幕](prepared-and-subtitles.md)：准备记录字段、缓存与字幕规则
- [配音音色与节奏](voice-and-rhythm.md)：音色、语速与停顿节奏
- [代码场景运行契约](code-scene-runtime.md)：契约页接口与确定性要求
- [渲染引擎](render-engine.md)：打包、渲染会话、字幕量测与成片编码
