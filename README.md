# Material2Video（材料成片）

[English](README.en.md)

**把文章、数据和素材做成可编辑的短视频。**

用分镜组织内容，用代码制作画面，把素材、字幕和成片保存在一个能独立运行的工程里。

> 成片封面将在阶段 B 补到 `docs/site/assets/hero.jpg`。

**[看作品][video-gallery]** · **[做第一个视频](#三分钟做出第一条视频)** · **[查看源码](ARCHITECTURE.md)**

## 示例作品

| 作品 | 类型 | 时长 | 看什么 |
| --- | --- | ---: | --- |
| [复利 40 年](examples/data-evolution/compound-after-20/README.md) | 数据演化 | 38.7 秒 | 年度利息柱从零线生长，前后二十年归为两塔，解释 6.73 倍的差距。 [成片页][video-compound-after-20] |
| [全球市值前十](examples/data-evolution/global-market-cap-race-portrait/README.md) | 数据演化 | 107.13 秒 | 在竖屏上跟踪 2000–2026 年的排名变化，观察榜首交接与平台叠层留白。 [成片页][video-global-market-cap-race-portrait] |
| [运气到底是什么](examples/principle-metaphor/luck-on-stage/README.md) | 原理隐喻 | 41 秒 | 从一次命中开始，用飞行标记、概率盘和三柱比较解释预期成功次数。 [成片页][video-luck-on-stage] |
| [太阳系之旅](examples/spatial-3d/solar-system-journey/README.md) | 三维空间 | 120 秒 | 连续经过十五站，观察地月关系、土星环的视角揭示与外层尺度。 [成片页][video-solar-system-journey] |
| [从电报到大模型](examples/documentary-edit/american-science-milestones/README.md) | 纪实素材剪辑 | 30 秒 | 从馆藏电报纸带切入，用档案串起十项科技节点，结尾回到纸带。 [成片页][video-american-science-milestones] |

成片页将在阶段 B 上线。现在可打开任一作品说明，查看它的分镜、设计材料和恢复步骤。
五部示例都能作为独立工程恢复和导出。 [随附示例与复现说明](examples/README.md)

## 三分钟做出第一条视频

先用图文动效模板做一条三秒标题视频。首次安装依赖、恢复字体和下载浏览器的时间取决于网络。

需要 Python 3.11 或更新版本、uv、Node.js 22.12 或更新版本，以及 pnpm 10.15.0。
在仓库根目录运行这条命令。PowerShell 和 bash 通用。

```text
uv run m2v init --type text-motion --project demo
```

打开生成的 `videos/text-motion/demo/`，改两处内容。

1. 在 `storyboard.json` 的第一幕找到 `scenes[0].content.props`，
   将空对象换成 `{"title": "我的第一条视频"}`。开场场景从这个字段读取屏幕标题。
2. 在 `scenes/opening.tsx` 把 `background: '#0b0d12'` 改为
   `background: '#17365d'`，用这个颜色作为整张画布的主色。

回到仓库根目录，按当前 shell 选择一组命令。依赖与资源就绪后，最后一条制作并导出视频。

**PowerShell**

```powershell
Push-Location videos/text-motion/demo
pnpm install --frozen-lockfile --ignore-workspace
uv sync --frozen
pnpm run setup --download --install-browser
pnpm run render
Pop-Location
```

**bash**

```bash
(
  cd videos/text-motion/demo &&
  pnpm install --frozen-lockfile --ignore-workspace &&
  uv sync --frozen &&
  pnpm run setup --download --install-browser &&
  pnpm run render
)
```

从仓库根目录打开 `videos/text-motion/demo/outputs/video.mp4`，就能看到改过标题和主色的成片。
继续编辑分镜和场景源码，在同一作品目录重新导出。 [环境与资源恢复说明](templates/standalone/README.md)

## 它是怎么工作的

材料提供文章、数据和媒体，分镜把材料编排为有时序的场景并指向对应源码。
场景源码控制排版、相机、光影与动效，采集按帧记录实际绘制的画面，
再由作品内的 `SceneFilm` 合成片段、转场和字幕，最后混音并写出成片。
作品自带运行源码、依赖锁和资源恢复入口，可在作品目录独立运行。
[架构与模块职责](ARCHITECTURE.md)

## 当前能力

从五类视频中选择起点。五类使用同一套独立工程基础，按作品需要采用场景组件和素材。

<!-- generated:type-catalog:start -->
- `text-motion`：代码生成文字和图形，侧重排版与动效
- `data-evolution`：结构化数据的可视化变化
- `principle-metaphor`：程序生成物体和场景，说明抽象原理
- `spatial-3d`：三维模型和场景的空间渲染
- `documentary-edit`：真实视频、照片与档案的叙事剪辑
<!-- generated:type-catalog:end -->

可以制作代码画面，也可以剪辑登记过的真实媒体。地图轨迹和情境叙事可用作表现手法。
作品支持局部预览与完整导出。配音可由声音后端合成，带字幕的作品可使用双语字幕与自适应柔光。

## 文档导航

[技术文档索引](docs/reference/README.md)按以下主题整理工程细节与操作入口。

- [独立工程与分镜](docs/reference/project-model.md)涵盖工程版本、来源引用、依赖锁和资源恢复。
- [声音与字幕](docs/reference/voice-and-subtitles.md)涵盖配音后端、参考音色、双语字幕和柔光。
- [网页原生设计样品与媒体评审](docs/reference/sample-and-review.md)涵盖采集、预览、评审与交付。
- [素材、署名与作品存储](docs/reference/materials.md)涵盖素材台账、采用政策、缓存和目录。

制作顺序与各阶段契约见[制作 Skill](.agents/skills/material2video/SKILL.md)。
已实现行为见 [OpenSpec 规格](openspec/specs/)，后续路线见[项目规划](docs/PROJECT_PLAN.md)。

## 参与与许可

欢迎反馈制作与复现中的问题，或参与改进文档、示例和工具链。
[CONTRIBUTING.md](https://github.com/haoaoqikf/material2video/blob/main/CONTRIBUTING.md) 将在阶段 C 补齐。
仓库内的验证与提交约定见 [AGENTS.md](AGENTS.md)。

原创代码、文档及示例源码和原创文案采用 [MIT 许可证](LICENSE)。
Remotion 独立授权，其他另有许可标注的内容沿用各自声明。
依赖、字体、模型与示例素材的许可见[第三方声明](THIRD_PARTY_NOTICES.md)。

[video-gallery]: docs/site/index.html
[video-compound-after-20]: docs/site/index.html#compound-after-20
[video-global-market-cap-race-portrait]: docs/site/index.html#global-market-cap-race-portrait
[video-luck-on-stage]: docs/site/index.html#luck-on-stage
[video-solar-system-journey]: docs/site/index.html#solar-system-journey
[video-american-science-milestones]: docs/site/index.html#american-science-milestones
