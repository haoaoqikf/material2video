# Material2Video（材料成片）

面向短视频的离线制作工具链，采用**共享制作底座、独立视频类型、统一制作入口**。项目当前能力见下方类型目录；制作流程和类型契约由 [material2video Skill](.agents/skills/material2video/SKILL.md) 及其参考文档维护。

## 当前视频类型

<!-- generated:type-catalog:start -->
- `financial-timeseries`：股票、指数及 crypto 日线材料（含 USD/CNY 历史汇率折算）、假设投资计算、手机竖屏折线画面和完整候选自动验收。
- `general`：v8 全画布代码场景讲解：作品自行设计横屏或竖屏画面的配色、构图与动效，支持原文或主题输入、带来源留证的媒体导入、双来源音效库与本地音床，成片最长 600 秒。
- `housing-timeseries`：年度住宅销售均价动态折线视频，保存原始销售额、面积与来源口径，输出无声竖屏成片。
<!-- generated:type-catalog:end -->

固定示例：[从电报到大模型](examples/american-science-milestones/README.md)、[复利](examples/compound-interest/README.md)和[太阳系之旅](examples/solar-system-journey/README.md)。复利示例为29秒数学讲解动画：开场以“复利的力量”点题；1枚圆片=1,000元，以米白/金色/暗金三种资金状态解释收益再投入；第30年以40枚/约174.5枚可数圆片直接比较两种处理方式的30年总资产，随后用独立 S6 让16枚金色收益归队变白，只剩175枚本金堆，再以结论与片名收束。无旁白、无旋律配乐，含8秒进入的环境床与25个同步事件音。制作状态见示例验证记录。作品材料和输出位置见各示例说明及[协作约定](AGENTS.md)。

通用视频的画面设计与复核方法见[视觉创意方向](.agents/skills/material2video/references/visual-creative-direction.md)和[视觉力量设计](.agents/skills/material2video/references/visual-impact-design.md)。

制作载体选择见[素材选择规范](.agents/skills/material2video/references/visual-material-selection.md#视频优先与代码适用场景)；规则来源及文档维护边界见[架构说明](ARCHITECTURE.md#契约与文档)。类型清单、制作门及审核策略表由共享定义生成，运行 `uv run python .agents/skills/material2video/scripts/sync_docs.py --check` 可检查漂移。

## 快速开始

```powershell
uv sync
uv run python fonts/fetch.py
pnpm -C web install
pnpm -C web build
uv run playwright install chromium
uv run m2v types
uv run pytest
pnpm -C web test
```

需要浏览器或真实构建的用例标记为 `slow`；日常快速反馈用 `uv run pytest -m "not slow"`，CI 只跑该子集。

统一入口以作品目录为唯一归属：

```powershell
uv run m2v init --type general --project <slug> # 创建 videos/general/<slug>/，项目与分镜均默认横屏
uv run m2v validate --project videos/general/<slug>
# 有自身旁白时，先按下文选音并保存；手动制作可在 prepare 指定 --voice。
uv run m2v prepare --project videos/general/<slug>
# 可选局部片段检查：默认前十秒或显式短窗口，不能替代全片生成
uv run m2v preview --project videos/general/<slug>
# 所有类型 render 只生成一次全片，自动验收后直接交付；m2v review 为可选工具，适用审核轮按独立子代理流程执行。
uv run m2v render --project videos/general/<slug>
uv run m2v relocate --project videos/<old-slug> # 迁移旧作品源文件与全部产物
```

general 作品未配置旁白、音乐和音效时，预览与正式成片均不含音轨；有任一声音声明则保留原混音与验收流程。

有旁白的制作流程为：材料审查 → 编排旁白 → **制作助手自动选择音色并保存** → 校验与时间轴准备 → 按需检查生成与修改 → 全片生成一次 → 验收与复核 → 交付同一文件。助手读取当前音色列表并按内容选择，用户明确音色优先；全流程不要求播放视频、连续收听声音或试听音色，按类型使用静帧/时间标注帧序列、路径与画面量测、字幕及时间戳核对和自动音频信号分析。用户无需试听确认；有自身旁白但缺少 `tts.voice` 时 `prepare` 会阻断，也可用 `--voice` 手动指定。无旁白作品无需选音。字段、溯源与迁移见[配音音色与节奏](.agents/skills/material2video/references/voice-and-rhythm.md#配音音色与语速)。

作品及其全部 `outputs/` 产物按类型分层存放于 `videos/<type>/<slug>/`。`init` 的相对参数填写 `<slug>`，也可传入完整的 `videos/<type>/<slug>`；使用仓库外内容根时，传入 `--content-root` 或设置 `M2V_CONTENT_ROOT`。`relocate` 面向已有的 `videos/<slug>/` 统一契约作品，逐个备份后迁移源文件和产物；同名冲突文件不覆盖目标，解决后可重试。无 `project.json` 的旧文章内容不属于此迁移命令。目录归属、内容根与默认输出见[目录约定与输出路径](.agents/skills/material2video/references/paths.md)。

`init` 会生成材料模板，通用类型还会按类型目录写入起步场景 `scenes/opening.tsx`。通用作品先确定画幅与视觉设计（作品 `DESIGN.md`）、写 `scenes/` 下的本地场景，再完成源文审查与分镜；金融与住宅分别沿用各自的材料契约。三类各自的材料、编排与画面规则见[文档导航](#文档导航)。

可选风格机制独立于视频类型：`uv run m2v styles` 查询注册包，作品通过 `project.json` 的 `style.id` 选择；当前已登记 `vibe-night`（C 夜曲）。general 场景可显式使用参数、组件和资产，选择风格不会自动换肤。无旁白作品可在字幕安全区内自绘屏幕字幕；讲解方法与六种画法见[讲解设计](.agents/skills/material2video/references/explainer-design.md)。契约见[风格接入](.agents/skills/material2video/references/style-pack.md)。

## 命令

运行 `uv run m2v --help` 查看当前命令；类型专属材料和制作流程见 [material2video Skill](.agents/skills/material2video/SKILL.md)。

仅当用户明确要求复用整条参考音轨时，使用 `m2v ref audio <参考目录> --project <作品目录> --user-authorized "<授权说明>"` 并在作品材料记录授权；参考作品默认不进入成片。

架构边界与模块职责见 [ARCHITECTURE.md](ARCHITECTURE.md)。

通用视频支持键盘、火花、电流、掠过、碰撞和提示等常见音效：代码合成与第三方直链／本地文件导入统一登记，通过音效 ID 按帧定位，支持裁切、循环、淡化与左右声像。第三方素材须提供来源、作者及明确许可，准备与渲染离线执行。命令为 `m2v general sounds catalog|import|audit`；配方、分镜字段和制作检查见[媒体与音效](.agents/skills/material2video/references/article-media-and-sound.md#统一音效库)，[键盘与火花演练](examples/american-science-milestones/assets/SOUND_EXERCISE.md)提供可复现配方。

## 从旧名称迁移

本次为全面改名，不提供旧入口兼容别名。重新执行 `uv sync`、`pnpm -C web install` 和 `pnpm -C web build` 后，更新调用方：

| 旧名称 | 新名称 |
| --- | --- |
| `article2video` / `article2video-web` | `material2video` / `material2video-web` |
| `a2v` 命令及 Python 模块 | `m2v` |
| `A2V_*` 环境变量（含 `A2V_CONTENT_ROOT`） | `M2V_*`（含 `M2V_CONTENT_ROOT`） |
| `.agents/skills/article2video/` | `.agents/skills/material2video/` |
| `window.__A2V__`、`a2v-storyboard`、`/__a2v_web__/` | `window.__M2V__`、`m2v-storyboard`、`/__m2v_web__/` |
| `a2v-` / `data-a2v-` / `--a2v-` 样式与属性前缀 | `m2v-` / `data-m2v-` / `--m2v-` |

通用作品当前使用 `general` 类型和 v8 `storyboard.json`，画面入口是作品 `scenes/` 下的 TSX。旧通用材料不自动迁移，须按当前材料契约重新编排；修改材料后重新 `prepare`，再执行 `render`。

## 文档导航

- [material2video Skill](.agents/skills/material2video/SKILL.md)：统一制作流程、命令和按类型组织的参考资料。
- [视觉创意导演方法](.agents/skills/material2video/references/visual-creative-direction.md)：镜头等级、时间结构、导演卡与视觉事件方法。
- [视觉素材选择与使用](.agents/skills/material2video/references/visual-material-selection.md)：载体判断、素材检索、入片编排与替换复核。
- [ARCHITECTURE.md](ARCHITECTURE.md)：代码模块职责与依赖边界。
- [OpenSpec 规格](openspec/specs/)：已实现能力契约；[项目规划](docs/PROJECT_PLAN.md)：未来路线。

## 制作证据与状态

已有视频可通过制作助手的[修订入口](.agents/skills/material2video/references/video-revision.md)按修改意图继续制作：定位受影响场景与时间轴、保护旧版、复用有效方案和证据，再执行局部检查与最终全片复核。入口串联现有命令，未新增修订 CLI 或自动影响分析器。

general 提供 G0–G6 检查点门、指定帧采集、DOM 状态/布局量测、隔离评审包、缓存粗片播放器、追加式制作历史与显式基线清理。`m2v status --history --json` 在既有技术状态之外显示 production 制作状态；门不新增导出硬门禁。合同格式、覆盖局限与操作见[检查点制作门](.agents/skills/material2video/references/checkpoint-gates.md)。新作品/后续重制适用制作合同 v2，v1 明确拒绝、不自动迁移；缺失独立证据不自动放行。

v2 合同以 `reviewPlan.risks` 声明六类适用风险，审核人数和轮次由唯一策略派生：无核心未决风险的普通作品只需全片粗片与最终成片两次独立调用；有核心风险时增加一轮核心样片。每轮一份覆盖表绑定适用门，不再按检查点重复登记视觉事件或五维设计兑现凭据；状态查询分列自身结果、等待前置及真实过期。见[检查点契约](.agents/skills/material2video/references/checkpoint-gates.md)。

核心盲审覆盖表分别验证理解、表现与样片代表性；有目标图的核心实际片段须先盲审、后同轮独立对照，缺少或失败不授权扩展。独立评审必改项须凭当前同范围独立复查报告关闭。`status` 保留技术 `stage/candidate`，另用 `summary`、`production.complete` 和 `production.expansion` 区分候选生成、制作完成与可扩展检查点；这些条件不新增渲染硬门禁或用户审批。旧核心报告缺少新凭据时仅作历史，不自动补造通过。
