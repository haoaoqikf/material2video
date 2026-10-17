## Why

当前通用作品在技术上正确、可复现、可溯源，但视觉上停留在「科学可视化」：镜头从同一个总览机位反复飞近再飞回，光照均匀、材质多为 2K 颜色贴图、没有后期与声音设计；太阳系成片 174.6 秒、16 段等权讲解，节奏更像目录而不是旅程。

制作 Skill 也只把「完整预演自动验收」当作导出依据，视觉设计、参考板、镜头语言、材质、后期和声音都没有可验收的标准；审美评审是可选项，导致「能导出」被当成「够好」。同时 Skill 与契约里还有三处过时口径：固定示例名单仍含 keynote-baseline、`soundtrack.effects` 被写成不渲染、路线图把复杂画面与配乐排除在当前范围外。

本变更新增可选的 **cinematic 制作档位**：standard 档保持现有快速链路不变，cinematic 档把 look-dev、镜头清单、材质/后期、声音设计与感知验收变成可执行、可留证的步骤；并把太阳系示例改写为 **60 秒电影级参考片**，作为该档位的验收样板。

## What Changes

- 新增 **standard / cinematic** 双档位。standard 维持现有自动验收与默认编码；cinematic 增加 look-dev、镜头与 look 契约、后期、声音设计、高质量母版和感知评分卡。用户明确要求「电影级、极致、惊艳、发布级」时 MUST 使用 cinematic。
- 扩展 general v8 分镜的可选字段：`leadInFrames`、`tailFrames`、`readingHoldFrames`、`content.props.shots`、`content.props.look`、旁白段 `claims`。未声明时行为与当前完全一致，不升级分镜版本。
- 代码场景 SDK 新增镜头路径、焦段/滚转、曝光、焦点、后期（Bloom/DOF/grain/vignette/CA/LUT）与星空、粒子带、大气、环、日面、日珥、奥尔特云等电影级组件；批准 `postprocessing` / `@react-three/postprocessing` 依赖。
- 渲染新增 `--profile cinematic`：ProRes 422 HQ 或 DNxHR HQX 母版，H.264/HEVC 交付，10bit，48kHz/24bit 音频，hero 镜头 2× SSAA，2–4 子帧运动模糊；default 档编码参数保持不变。
- 资产新增质量与许可审计：hero 资产 4K+、normal/roughness/emissive、土星环径向分辨率、色彩空间、许可；声音新增配乐/环境/音效/母版混音与响度目标。
- 新增 `m2v lookdev`、`m2v qa`、`m2v assets audit`、`m2v master` 与 `render --profile cinematic`；新增 cinematic 十项评分卡与 hero 实看门禁。
- lookdev 静帧从当前源码按原生 2× 像素密度采集，以 PNG 合成字幕和转场；不将 1080p 缓存视频放大作为 4K 细节证据，有声样片保留现有流程。
- 修正现有口径：固定示例名单改为 buffer-smoothing、darts-trial-and-error、solar-system-journey；`soundtrack.effects` 明确为已渲染；路线图加入 cinematic 档位，明确不引入第二套渲染引擎。
- **BREAKING（示例内容）**：太阳系示例从 174.6 秒、16 段改写为约 60 秒、9 个章节、3 个 hero、单程向外镜头；旧分镜、旧旁白与旧成片失效，不保留旧版本兼容。三个固定示例数量不变，不新增示例。
- 太阳系示例的 60 秒版本同时作为 cinematic 验收样板：4K 资产、真实后期、配乐与音效、hero 镜头实看记录、ProRes 母版与 H.264 交付。

## Capabilities

### New Capabilities

无，复用现有能力目录。

### Modified Capabilities

- `article-explainer`：60 秒太阳系示例、可选静音前后段与镜头字段、电影级示例验收。
- `general-video-composition`：cinematic 档位与电影级画面约束。
- `react-code-scenes`：镜头/后期 SDK、确定性后期、电影级组件与资产元数据。
- `remotion-renderer`：分档编码、母版、运动模糊、SSAA 与后期确定性。
- `video-production-workflow`：档位、look-dev、参考板、镜头清单、claims 与感知评分卡。
- `article-media-assets`：资产质量与许可审计。
- `article-sound-effects`：配乐、音效、母版混音与响度。
- `render-provenance`：profile / look / post / audio master 溯源。
- `modular-video-production`：lookdev / qa / assets audit / master 命令入口。

## 60 秒太阳系示例

目标时长 60 秒，验收范围 55–65 秒；保留 9 个章节和 9 段中文旁白，改为「冷开场 + 单程向外 + 3 个 hero + 奥尔特云收尾」：

| 时间（约） | 章节 | 镜头与声音重点 |
|---|---|---|
| 0–5s | 冷开场（无旁白） | 日面边缘极特写，日珥升起，低频环境底 |
| 5–11s | 太阳 | 从日面拉到总览，日冕与轨道渐显 |
| 11–16s | 内行星 | 水星陨坑、金星云顶，侧向太阳光 |
| 16–24s | 地月 | hero：夜面灯光 → 晨昏线日出 → 海面高光；月球前景虚化 |
| 24–29s | 小行星带 | 火星红色尘土，穿越稀疏小行星带 |
| 29–35s | 木星 | hero：大红斑正对，云带流动，木卫二冰纹 |
| 35–43s | 土星 | hero：环从侧刃到展开，逆光冰晶，土卫六雾霾 |
| 43–49s | 冰巨星 | 天王星侧躺、海王星风暴 |
| 49–53s | 柯伊伯带 | 冥王星心形区域，柯伊伯带粒子 |
| 53–60s | 边缘 | 日球层顶气泡边界，奥尔特云拉远到太阳成点 |

旁白总量控制在约 230–260 个汉字（按实际 TTS 语速调整），每章约 20–30 字；冷开场与结尾保留无旁白留白。旧 16 段旁白与旧 article.md 不再保留。

## Impact

- 影响 `src/m2v` 的分镜校验、准备/渲染/编码、音频母版、资产审计、溯源与 CLI；影响 `web/` 的 SDK、代码场景录制页、composition 与依赖。
- 影响 Skill 主文档、制作流程、分镜结构、渲染契约、媒体契约、音效契约、评审量表、项目规划、README、AGENTS 与三个示例中的太阳系示例；缓冲与试错保持 standard 回归。
- 新增后期与高质量编码会显著增加渲染时间；按 hero 镜头分级渲染，不承诺全片同等开销。
- 后期、镜头、look、音乐、母版参数必须进入准备指纹与 bundle key；改任一参数都要求重新准备与完整预演。
- 旧太阳系成片、旧准备与旧预演失效；不提供兼容分支或旧版视频保留。缓冲、试错与金融/住宅类型不改为 cinematic。
- 本变更依赖进行中的 `fix-code-scene-frame-capture` 先完成逐帧采集；若该变更未归档，实施顺序应先归档它与本变更的前置字段，不并行修改同一录制链路。

## Delivery

本次只提交规划材料：提案、设计、任务与规格增量。严格校验后提交，不执行代码任务，不改写太阳系当前 174.6 秒成片。用户明确 apply 后再按任务实施、验证、审查并提交；任务全部完成后按项目约定同步主规格、更新 README/规划/Skill、归档并提交。
