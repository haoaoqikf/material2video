# 目录约定与输出路径

每篇文章占一个稳定、唯一的目录名（slug，推荐小写英文与连字符）。文章标题变化不改目录名。

**文章内容不入库**：`videos/` 是作品内容（原文、分镜、专属画面模块），已在 `.gitignore` 中忽略；
仓库里保留的是制作方法与共享画面工程。文章既可以留在仓库的 `videos/` 下，也可以放在仓库之外的
**内容根**里，两种情况下的命令完全一致。

## 两层根

| 根 | 是什么 | 怎么确定 |
| --- | --- | --- |
| **仓库根**（repo root） | 存放 skill 与共享画面工程（`web/`）的仓库 | 输入文件向上查找 `.agents/skills/material2video/SKILL.md`；文件在仓库之外时取**正在运行的脚本**所在仓库 |
| **工作区根**（workspace root） | 存放 `videos\|examples/<slug>/` 及作品产物的目录 | 默认就是仓库根；设置了内容根时是内容根 |

内容根按下面的优先级确定，**不自动探测、不猜**：

1. 命令行 `--content-root <dir>`；
2. 环境变量 `M2V_CONTENT_ROOT=<dir>`；
3. 都没有 → 工作区根 = 仓库根。

内容根要与仓库同构：它下面直接放 `videos/<slug>/`，产物位于文章目录下的 `outputs/`（示例源放
`examples/<slug>/`，产物位于 `videos/examples/<slug>/outputs/`）。内容根里**不需要**也不应该有 skill 副本——画面由仓库里
`web/` 的共享 composition 提供，契约页在渲染与体检时按仓库根自动定位并挂载。

## 目录结构

```text
<仓库根>/
├── .agents/skills/material2video/     # 制作方法与参考文档（入库）
├── web/                              # 共享画面工程：组件、令牌、composition（入库）
├── examples/<slug>/                  # 随仓库发布的示例（入库）
├── videos/<slug>/                    # 实际文章内容（不入库，见 .gitignore）
│   ├── article.md
│   ├── storyboard.json
│   ├── production.json                # 导演阶段、指纹、评审和返工记录（不入库）
│   ├── scenes/                       # 代码场景模块（renderer.code），按需创建
│   └── assets/                       # 本篇专用素材，按需创建
└── videos/<slug>/outputs/            # 成片与中间产物（不入库）
    ├── silent.mp4                    # 最新无声成片
    ├── voiced.mp4                    # 最新配音成片
    ├── voiced.srt                    # 配音成片字幕
    ├── voiced.performance.json       # 与该成片同名的渲染性能报告（不入库）
    ├── media/                        # 配音清单、音轨与缓存
    ├── previews/                     # 限帧试渲染，使用相同的成片文件名
    │   └── production/                # 关键幕有声样片、全片评审版与输出清单
    ├── bench/                        # 基准与验收报告、对照截图，按需创建（不入库）
    └── qa/                           # 验收截图等，按需创建
```

打包缓存不在作品目录里，而在共享工程下：`web/.cache/m2v-bundles/<键>/`。
它只与「当前 `web/` 源码 + 当前作品输入 + 依赖版本」有关，跨作品共享，整目录可随时删除。

内容根在仓库之外时，`videos/<slug>/` 与其下的 `outputs/` 一起搬到内容根下，其余不变：

```text
<内容根>/
├── videos/<slug>/…
└── videos/<slug>/outputs/…
```

`examples/<slug>/` 与 `videos/<slug>/` 同构，但产物放入 `videos/examples/<slug>/outputs/`，
多一层 `examples/`，避免示例与实际文章同名时互相覆盖。
示例对应的 `production.json` 也放在 `videos/examples/<slug>/`，避免把运行记录写进版本化的 `examples/<slug>/`。

## 画面来自哪里

画面不再是一张作品自己的 HTML：渲染入口把分镜交给仓库 `web/` 里的共享
React composition（Remotion），围绕全片 `world` 按全局时间轴绘制，`stages[]` 推进叙事。
需要新表达时按原语注册表流程新增通用原语；全片需要独特的图表面板、
关系图或定制 SVG 时，在 `world.renderer` 声明 `kind: "code"` 与 `module`，模块放在作品目录的
`scenes/` 下（`videos/<slug>/scenes/` 或 `examples/<slug>/scenes/`，与分镜同目录），
本地资产放 `assets/`。模块契约与纪律见 [代码场景](code-scenes.md)。

本篇专用素材（`videos/<slug>/assets/`）由静态服务器按工作区根提供，
composition 里经相对 URL 引用；仓库 `web/` 自身的源码与字体则通过
`/__m2v_web__/` 别名挂载，内容根在仓库之外时同样可达。
代码场景的本地资产用打包器导入（`import markUrl from '../assets/mark.png'`），
构建时随作品源码一起进入依赖白名单检查与指纹。

## 归属推导

新制作以 `--project` 确定作品归属，材料路径相对于作品根。文章兼容流程的既有路径推导位于 `src/m2v/types/article/paths.py`。

1. 以输入文件位置向上查找含 `.agents/skills/material2video/SKILL.md` 的目录；找不到时
   取运行中的 bundle 所在仓库——契约页与 composition 从那一份取；
2. 文件在仓库内直属的 `videos/<slug>/` 或 `examples/<slug>/` 时，工作区根即仓库根；
3. 否则用内容根作为工作区根，slug 取 `videos|examples/<slug>/` 里的目录名；
4. 新制作入口以 `project.json` 确定类型和材料；文章辅助流程仍以分镜路径推导历史目录；
5. 全程使用绝对路径，与执行命令时的工作目录无关。

推导失败时不猜归属，直接报错并要求显式指定输出路径：

| 情况 | 结果 |
| --- | --- |
| 找不到仓库根标记，且 bundle 不在仓库里 | 报错，提示需要显式指定输出路径 |
| 文件在仓库外、又没有内容根 | 报错，点名 `--content-root` 与 `M2V_CONTENT_ROOT` |
| 内容根里也没有 `videos|examples/<slug>/` | 报错，列出实际路径与它检查过的位置 |
| 缺失 `project.json` 或类型材料 | 指出作品目录或缺失材料，停止后续制作 |
| 准备记录、资产或嵌入项目指纹已变化 | 要求重新 prepare，再生成预演与评审 |

## 默认输出

| 命令 | 省略输出参数时的位置 |
| --- | --- |
| `m2v prepare --project <目录>` | `<作品目录>/outputs/prepared.json` 与类型专属生成材料 |
| `m2v preview --project <目录>` | `<作品目录>/outputs/previews/` 下的当前预演 |
| `m2v render --project <目录>` | `<作品目录>/outputs/` 下类型默认的正式成片 |
| `m2v preview --project <目录> --limit-frames N` | 调试用途；不会生成可绑定正式评审的完整预演记录 |

文章默认成片名由准备后的音轨决定：有音轨为 `voiced.mp4`，无音轨为 `silent.mp4`。由 `project.json` 解析材料与输出位置，不通过旧式 `--media` 或输出路径参数切换制作归属。
v4 分镜不接受字符串 `narration`（口播写在 `narrationSegments`），所以不存在
「写了旁白却没配音」的中间态：需要配音请先执行 `uv run m2v prepare --project <目录>`。

## 成片溯源

渲染成功后在成片旁写 `<同名>.provenance.json`，用于回答「这个成片是不是旧画面渲的」：

```json
{
  "version": 4,
  "renderer": "remotion",
  "workspace": "../..",
  "renderedAt": "2026-09-20T12:00:00+00:00",
  "page": "__m2v_web__/src/index.ts",
  "storyboard": "videos/<slug>/storyboard.json",
  "frames": 300, "fps": 30, "width": 1080, "height": 1920,
  "captureFormat": "remotion",
  "assets": { "files": { "__m2v_web__/src/registry/registry.json": "…" }, "digest": "…" }
}
```

定位一律用**相对引用**：`workspace` 是产物目录到工作区根的相对路径，键相对工作区根记；
构建输入（composition 源码、注册表、令牌与字体清单）在仓库的 `web/` 里，记
`/__m2v_web__/` 别名键。这样溯源跟着成片走，换机器、换目录、换内容根都读得回来，
复核时也不需要 `--content-root` 或仓库标记。

`version` 不是 3 或 4 的溯源按「旧格式」处理：如实回答无法判断，不默认放行。

## 渲染性能报告

同一支成片还写一份 `<同名>.performance.json`（同样不入库），回答的是另一类问题：
这次渲染慢在哪、缓存有没有命中、用了几个并发、开了几次浏览器。它**不参与交付判定**，
写不进去只告警，不会让一次已经验收通过的渲染失败。

```json
{
  "version": 1,
  "frames": 1200, "fps": 30, "width": 1080, "height": 1920,
  "concurrency": 1,
  "totalSeconds": 98.4,
  "stages": { "cache": 0.03, "bundle": null, "metadata": 4.1, "render": 91.8, "mux": 0.5, "probe": 1.4 },
  "skipped": ["bundle"],
  "cache": { "status": "hit", "key": "…", "prepareSeconds": 0.03 },
  "session": { "browsersOpened": 1, "handshakeSeconds": 4.1 },
  "environment": { "python": "3.12.10", "node": "v22.23.2", "remotion": "4.0.526" }
}
```

`render` 已包含编码（两者在 Remotion 内部重叠），因此没有独立的 `encode` 阶段；
未执行的阶段是 `null` 且列在 `skipped` 里，不用 `0` 冒充实测。
比对不同配置时用 `benchmark_render.py benchmark`，报告落在作品 `outputs/bench/`。

## 兼容与覆盖规则

- 输出归属由 `--project` 唯一确定；类型内部临时文件在验收后原子替换默认输出；
- 不设内容根时工作区根即仓库根，路径与产物位置与引入内容根之前一致；
- 同类重复导出覆盖固定文件（同一篇文章的 `silent.mp4` 只有一份）；
- 产物先生成、验收后替换，失败不会破坏上一份可用成片；
- 统一入口正式渲染成功后清理本作品 `outputs/` 中旧视频及其字幕/溯源/性能旁车、预演、检查图和已知调试目录；保留本次成片及旁车、`prepared.json`、评审 JSON 和 `media/` 准备媒体。渲染或验收失败不清理，仓库共享构建缓存不受影响；清理错误按遗留路径报告；
- 限帧试渲染写入 `previews/`，不会覆盖正式成片。

## 相关文档

- [配音与字幕](media-contract.md)：媒体清单字段、缓存与字幕规则
- [渲染契约](render-contract.md)：网页接口、确定性要求与渲染模式
