# 目录约定与输出路径

每篇文章占一个稳定、唯一的目录名（slug，推荐小写英文与连字符）。文章标题变化不改目录名。

**文章内容不入库**：`videos/` 是作品内容（原文、分镜、媒体素材），已在 `.gitignore` 中忽略；
仓库里保留的是制作方法与共享画面工程。文章既可以留在仓库的 `videos/` 下，也可以放在仓库之外的
**内容根**里，两种情况下的命令完全一致。

## 两层根

| 根 | 是什么 | 怎么确定 |
| --- | --- | --- |
| **仓库根**（repo root） | 存放 skill 与共享画面工程（`web/`）的仓库 | 输入文件向上查找 `.agents/skills/material2video/SKILL.md`；文件在仓库之外时取**正在运行的脚本**所在仓库 |
| **工作区根**（workspace root） | 存放 `videos/<type>/<slug>/`、`examples/<slug>/` 及作品产物的目录 | 默认就是仓库根；设置了内容根时是内容根 |

内容根按下面的优先级确定，**不自动探测、不猜**：

1. 命令行 `--content-root <dir>`；
2. 环境变量 `M2V_CONTENT_ROOT=<dir>`；
3. 都没有 → 工作区根 = 仓库根。

内容根要与仓库同构：它下面直接放 `videos/<type>/<slug>/`，产物位于作品目录下的 `outputs/`（示例源放
`examples/<slug>/`，产物位于 `videos/examples/<slug>/outputs/`）。内容根里**不需要**也不应该有 skill 副本——画面由仓库里
`web/` 的共享 composition 提供，契约页在渲染与体检时按仓库根自动定位并挂载。

## 目录结构

```text
<仓库根>/
├── .agents/skills/material2video/     # 制作方法与参考文档（入库）
├── web/                              # 共享画面工程：组件、令牌、composition（入库）
├── examples/<slug>/                  # 随仓库发布的示例（入库）
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
    ├── review.json                   # 可选人工画面评审，绑定当前准备指纹与完整预演（general）
    ├── layout-check.json             # 最近一次布局量测的三项硬判定结论（general）
    ├── reading-pace.json             # 逐条字幕的阅读速度与超限清单，只报告不阻断（general）
    ├── media/                        # 配音清单、音轨与缓存
    ├── audio-cache/                  # 逐段语音缓存（键含媒体契约版本）
    ├── code-cache/                   # general 代码场景的录制片段与摘要，按内容摘要命名
    ├── previews/                     # 预演产物，使用相同的成片文件名；`m2v render` 会先清掉它
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

`examples/<slug>/` 是仓库示例源；`m2v --project examples/<slug>` 使用其中的材料，
预演与成片落到 `videos/examples/<slug>/outputs/`；准备记录、评审及准备媒体仍在
`examples/<slug>/outputs/`。两处产物目录均不入库。
需要把示例的产物与源文件分开时，把示例目录整体复制到 `videos/<type>/<slug>/` 再制作。

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
2. 文件在仓库内的 `videos/<type>/<slug>/` 或 `examples/<slug>/` 时，工作区根即仓库根；
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
| `m2v preview --project <目录> --limit-frames N` | 调试用途；不会生成可绑定正式评审的完整预演记录 |

所有类型的正式成片都叫 `outputs/video.mp4`，预演叫 `outputs/previews/video.mp4`；
文件名不随有无配音变化（没有音轨时渲染的是无声画面，名字不变）。由 `project.json`
解析材料与输出位置，不通过旧式 `--media` 或输出路径参数切换制作归属。
v7 分镜不接受字符串 `narration`（口播写在 `narrationSegments`），所以不存在
「写了旁白却没配音」的中间态：需要配音请先执行 `uv run m2v prepare --project <目录>`。

## 交付权限

所有从临时目录搬到最终位置的产物都在搬运的同时交回所在目录的继承权限：成片、溯源记录、
混音主音轨、代码场景录制片段、导入素材与缓存条目。原因是 Windows 的 `tempfile` 临时目录
带一份收紧的 ACL（只有 `SYSTEM`、`Administrators` 与 `OWNER RIGHTS`，且关闭继承），产物
只 `replace` 不修复时，当前账号仍能读写，但以标准权限运行的打包应用打不开——用户双击成片时
媒体播放器报 `0x80070005 你没有访问该文件的权限`。

- 交付统一走 `m2v.core.security.deliver`（整个目录用 `deliver_directory`），不要手写 `Path.replace`。
- 交付后复核目标本身；仍缺少普通用户授权条目时日志会报告目标与所在目录，指出问题在父目录。
- 复核判据是 `security.has_usable_access`；非 Windows 平台不存在这个问题，`icacls` 为 Windows 自带命令。

## 成片溯源

渲染成功后在成片旁写 `<同名>.provenance.json`，用于回答「这个成片是不是旧材料渲的」。
`schemaVersion` 当前为 `1`。文章类型（`general`）的形状是：

```json
{
  "schemaVersion": 1,
  "type": "general",
  "projectId": "buffer-smoothing",
  "preparedFingerprint": "…",
  "compositionId": "ArticleExplainer",
  "inputs": { "storyboard": "…", "tts": "{…}", "implementation": "…",
              "file:article.md": "…", "renderer": "…" },
  "durationInFrames": 590, "fps": 30, "width": 1080, "height": 1920
}
```

`type` 为 `general` / `financial-timeseries` / `housing-timeseries`
之一，`compositionId` 是它对应的 Remotion composition 标识。
`preparedFingerprint` 是当前准备记录的指纹：与 `outputs/prepared.json` 不一致就说明
材料、资产或渲染代码已经变化，成片落后。
`inputs` 是准备时记下的逐输入摘要（分镜、`tts` 记录、实现摘要、`file:<作品内相对路径>`、
`audio:<场景>`、composition 可达源码的 `renderer` 指纹），用它逐项指出是哪个输入变了。

各类型的字段并不完全一致，差异有据可查：

| 类型 | 与上表的差异 |
| --- | --- |
| `general` | 无差异；**不含**根级 `renderer` 与 `bundleKey` |
| `financial-timeseries` / `housing-timeseries` | 多 `renderer` 与 `bundleKey`，并用 `frames` + `materialsAndAssetsSha256` 代替 `durationInFrames` + `preparedFingerprint`/`inputs` |

溯源**不参与交付判定**，它只是「这个成片是哪次准备渲的」的答案；判定由正式渲染
独立复核准备指纹与文件摘要完成。

## 渲染性能报告

同一支成片还写一份 `<同名>.performance.json`（同样不入库），回答的是另一类问题：
这次渲染慢在哪、缓存有没有命中、用了几个并发、开了几次浏览器。它**不参与交付判定**，
写不进去只告警，不会让一次已经验收通过的渲染失败。

```json
{
  "version": 1,
  "entry": "render",
  "generatedAt": "2026-09-20T12:00:00+00:00",
  "output": "voiced.mp4",
  "storyboard": "<分镜的绝对路径>",
  "frames": 1200, "fps": 30, "width": 1080, "height": 1920,
  "concurrency": 1,
  "stages": { "cache": 0.03, "bundle": null, "metadata": 4.1, "render": 91.8, "mux": 0.5, "probe": 1.4 },
  "skipped": ["bundle"],
  "executedSeconds": 97.8,
  "totalSeconds": 98.4,
  "environment": {
    "platform": "Windows-11-10.0.26300-SP0", "machine": "AMD64", "processor": "…",
    "cpuCount": 18, "memoryGiB": 31.6,
    "python": "3.12.10", "node": "v22.23.2", "remotion": "4.0.526",
    "ffmpeg": "ffmpeg version …", "executable": "…/python.exe"
  },
  "cache": { "status": "hit", "key": "…", "detail": "命中并复核了 55 个产物文件" },
  "session": { "browsersOpened": 1, "handshakeSeconds": 4.1 }
}
```

`entry` 标明数据来自哪个入口（`preview` 或 `render`），因为正式门禁下的数字与限帧
试渲染不同源，混着比会得出错误结论。`environment` 用来解释「同一份材料在两台机器上
为什么快慢不同」。各类型还会往报告根上补几个自己的字段（例如讲解渲染的
`layoutCheckSeconds`、通用视频的 `session.browsersOpened` / `observedPeakMemoryBytes`）。

`render` 已包含编码（两者在 Remotion 内部重叠），因此没有独立的 `encode` 阶段；
未执行的阶段是 `null` 且列在 `skipped` 里，不用 `0` 冒充实测。

## 兼容与覆盖规则

- 输出归属由 `--project` 唯一确定；类型内部临时文件在验收后原子替换默认输出；
- 不设内容根时工作区根即仓库根，路径与产物位置与引入内容根之前一致；
- 同类重复导出覆盖固定文件（同一篇文章的 `silent.mp4` 只有一份）；
- 产物先生成、验收后替换，失败不会破坏上一份可用成片；
- 统一入口正式渲染成功后清理本作品 `outputs/` 中旧视频及其字幕/溯源/性能旁车、预演、检查图和已知调试目录；保留本次成片及旁车、`prepared.json`、评审 JSON 和 `media/` 准备媒体。渲染或验收失败不清理，仓库共享构建缓存不受影响；清理错误按遗留路径报告；
- 限帧试渲染写入 `previews/`，不会覆盖正式成片。
- 旧统一作品使用 `m2v relocate --project videos/<slug>` 逐个迁移；命令先完整备份，同路径冲突不覆盖目标文件，可处理后重试。`m2v migrate --from financial` 只用于旧金融材料契约迁移。

## 相关文档

- [配音与字幕](media-contract.md)：媒体清单字段、缓存与字幕规则
- [渲染契约](render-contract.md)：网页接口、确定性要求与渲染模式
