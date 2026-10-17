## Context

当前 general v8 已经具备：本地 React 代码场景、逐帧受控录制、真实 TTS、烧录字幕、素材导入留证、音床/音效混音、准备指纹、完整预演自动验收、正式导出与溯源。技术底座是可靠的；问题在于它只定义「画面是否正确」，没有定义「画面是否好看」。

太阳系示例暴露了这套工作流的边界：16 段等权旁白、约 10.9 秒一段；每段从同一个总览机位飞近目标再飞回；光照是 ambient 0.22 + decay 0 的点光；颜色贴图多为 2048×1024，土星环只有 2048×125；没有 Bloom/DOF/grain/LUT/运动模糊；没有配乐；字幕、左栏、导航与免责声明长期同屏。技术上全部通过，视觉上仍像动态图谱。

同时存在三处过时口径：

- `references/article-to-storyboard.md` 与 `AGENTS.md` 的固定示例仍写 keynote-baseline，实际是 solar-system-journey。
- `references/media-contract.md` 写「节拍音效当前不渲染」，但 `src/m2v/types/general/soundtrack.py` 与 `src/m2v/engine/audio.py` 已经实现 effects 混音。
- `docs/PROJECT_PLAN.md` 把复杂转场与第二套渲染引擎排除在路线外，并把自动选曲列为不做；本次用户明确要求电影级，需要重新界定范围。

另外，进行中的 `fix-code-scene-frame-capture` 正在替换录制链路。本变更不重复实现逐帧采集；实施时以该变更归档后的录制契约为前置。

## Goals / Non-Goals

**Goals:**

- 新增可选 cinematic 档位，使「电影级」成为可执行、可留证、可验收的制作方式。
- standard 档保持现有快速链路：自动验收、默认编码、无新增用户确认。
- 把镜头、look、后期、声音、资产质量、编码母版与感知评分卡定义成明确契约。
- 将太阳系示例改写为约 60 秒的电影级参考片，作为 cinematic 档的第一份样板。
- 修正现有文档口径，避免 Skill 继续给出过时事实。
- 保持确定性、溯源、素材留证、离线制作与现有兼容编码路径。

**Non-Goals:**

- 不引入第二套渲染引擎，不替换 Remotion/React/R3F 底座；后期在代码场景或共享 composition 内完成。
- 不默认给所有作品加电影级开销；cinematic 必须显式选择。
- 不自动选曲、不接入第三方音乐服务；配乐来自本地素材或确定性程序化音床。
- 不新增固定示例，不把缓冲与试错改成 cinematic；它们继续作为 standard 回归。
- 不承诺任意异步、随机作品的逐像素复现；确定性仍以同帧画面等价为准。
- 不在本提案阶段修改成片、README 当前能力或主规格；这些在 apply 阶段完成。

## Decisions

### 1. 档位模型：standard / cinematic

`project.json` 新增可选 `productionProfile: "standard" | "cinematic"`，默认 standard。分镜不重复声明档位；准备记录、预演与溯源自上而下继承。用户明确说「电影级 / 极致 / 惊艳 / 发布级 / 品牌片」时，助手 MUST 使用 cinematic，不得静默按 standard 交付。

| 项 | standard | cinematic |
|---|---|---|
| look-dev | 可选 | 必须：3–5 张 4K 静帧 + 20–30 秒有声样片 |
| 镜头 | 作品自由 | 必须提交 shot list；hero ≥ 3 |
| 资产 | 2K 可用 | hero ≥ 4K，normal/roughness/emissive 齐全 |
| 后期 | 无 | Bloom/DOF/grain/vignette/CA/LUT |
| 声音 | TTS + 可选音床 | 配乐 + 音效 + 母版混音 |
| 编码 | H.264 CRF18、8bit、44.1k/128k | ProRes/DNxHR 母版 + H.264/HEVC 交付、48k/24bit |
| 质检 | 自动字幕 + 抽帧观看 | 技术 QA + 感知评分卡 + hero 实看 |
| 门禁 | 自动验收 | look-dev 批准 + 20 秒样片 + 全片 QA |
| 成本 | 1× | 2–4× |

cinematic 的「look-dev 批准」是现有「不新增用户逐次确认」的唯一例外：standard 保持自动；cinematic 必须在关键静帧与代表片段上停下来给用户看，避免整片渲完才发现方向错了。

### 2. 分镜字段：可选扩展，不升级 v8

为避免重写三个示例，本变更不升级分镜版本，只在 v8 上增加可选字段；未声明时行为与当前一致：

- scene 级：`leadInFrames`（0–1800）、`tailFrames`（0–1800）、`readingHoldFrames`（0–360，默认 24）。
- `content.props.shots`：镜头数组，每项包含 id、target、tier（hero/major/minor）、时间窗、camera（path/fov/roll/easing/keyframes）、focus、exposure、post。
- `content.props.look`：profile、LUT、grain、bloom、DOF、vignette、曝光策略。
- narration segment 可选 `claims`：本段旁白声称的画面特征，用于预览时检查该时间窗内特征是否可见。

这些字段由准备阶段校验，进入准备指纹和代码片段缓存键。字段非法时明确失败；standard 作品不写这些字段时，准备记录与缓存键不因本变更而变化。

长期若要提供一等镜头/音频契约，再评估 v9；按项目规则，版本升级必须彻底重写，不保留 v8 兼容分支，所以不在本次半升版。

### 3. 60 秒太阳系：9 章、3 个 hero、单程向外

- 保留 9 个章节导航：太阳、内行星、地月、小行星带、木星、土星、冰巨星、柯伊伯带、边缘。
- 9 段旁白，每段约 20–30 个汉字，总量约 230–260 字；实际时长以 TTS 为准，验收范围 55–65 秒。
- 冷开场 5–6 秒无旁白；结尾 6–8 秒无旁白；两者依赖 `leadInFrames` / `tailFrames`。
- 镜头从太阳一路向外，不再每段回到同一个总览机位；只在 3 个章节转折回望。
- 3 个 hero：地球（夜面灯光→日出→海面高光）、土星（环面从侧刃到展开、逆光）、奥尔特云（拉远到太阳成点）。太阳作为冷开场的第四个视觉重点。
- 每个 hero 必须有一个 8–12 秒的连续镜头；其余章节 4–7 秒，允许掠过。
- 旁白提到的大红斑、冥王星心形区域、木卫二冰纹、土卫六雾霾必须在该段可见；用 `claims` 与镜头朝向保证。
- 资产升级：太阳/地球/土星/木星/冥王星/土卫六 hero 资产 4K+；normal/roughness/emissive 齐全；土星环径向纹理 ≥ 4K×512。
- 声音：60–70 BPM 环境底、低频 drone、飞近 whoosh、土星环 shimmer、冰裂、风、结尾深空静默；旁白 −16 LUFS，母版 −14 LUFS / −1 dBTP。
- UI：左栏按镜头淡入淡出；顶部导航改为章节进度轨；免责声明只在片头/片尾；字幕改为渐变 scrim；加距太阳 AU 读数。
- 旧 16 段旁白、旧 article.md、旧 storyboard、旧成片全部失效；不保留旧版本入口。

### 4. 镜头与后期契约

- `shots` 是数据，不是散落在作品代码里的魔法数字；准备阶段校验每个 shot 的时间窗落在所属旁白段内，hero 至少 3 个。
- 共享 SDK 提供 `CameraRig`：CatmullRom 路径、quintInOut 等缓动、每镜头 FOV/滚转/曝光、焦点拉移、穿球与背景裁切检查。
- 共享 SDK 提供 `PostFX`：Bloom、DOF、grain、vignette、chromatic aberration、LUT；只作用于 canvas，不影响共享字幕 DOM 层。
- 后期参数必须由 `elapsedSeconds`/帧号驱动，不得使用挂钟、`Math.random`、CSS animation 或组件计时器；源码闸门继续拒绝这些写法。粒子噪声使用「帧号 + shot id」的确定性种子。
- 运动模糊用 2–4 个子帧平均，等效 180° 快门；hero 镜头 2× SSAA 后降采样。总览保持 1×、深景深，不做 DOF。
- `postprocessing` / `@react-three/postprocessing` 加入批准依赖；`package.json` 与锁文件变化会让 bundle cache 失效。缺依赖时在打包前明确失败。

### 5. 编码与音频母版

- standard 档编码完全不变：H.264、yuv420p(tv, bt709)、CRF 18、medium、44.1kHz/立体声/128k AAC；保持 Media Foundation 可播放。
- cinematic 档新增：ProRes 422 HQ 或 DNxHR HQX 母版，10bit；H.264 CRF 14–16（或 12–20 Mbps）交付；可选 HEVC 10bit；音频 48kHz/24bit 母版、AAC 320kbps 交付。
- 母版与交付都写 provenance；交付仍保留 H.264 兼容版，避免只给不能播放的 10bit 文件。
- 暗部渐变使用 10bit 或细颗粒抖动，避免深空 banding；成片验收增加 banding/aliasing 抽检。
- 音频母版：对白 −16 LUFS，音乐 −28 至 −32 dB，音效 −24；母版 −14 LUFS / −1 dBTP；保留闪避与真峰值限制。

### 6. 资产质量与许可

- 新增 `m2v assets audit`：按镜头计算屏幕像素/纹素比；hero 特写颜色图 < 4K 时告警；检查 normal/roughness/emissive、环径向分辨率、色彩空间、alpha、许可。
- hero 资产许可未知时阻断；standard 资产许可未知时保留现有「未知」记录但不阻断。
- `useMediaAsset` 返回 colorSpace、alpha 与登记许可，作品可据此设置材质和片尾署名。
- 优先 NASA/USGS/ESA/CC BY 来源；每支作品维护 `SOURCES.md`，新增素材同步。
- 不把 2K 贴图放大冒充 4K；审计按实际文件尺寸与屏幕占比判断。

### 7. QA 与感知评分

新增命令：

- `m2v lookdev --project <dir>`：按最终画质渲染 3–5 张 4K 静帧与一张接触表。
- `m2v qa --project <dir>`：接触表、冻结/重复帧、banding、aliasing、字幕对比度、响度/真峰值、音画同步、claims 可见性；输出 `outputs/qa.json`。
- `m2v assets audit --project <dir>`：资产质量与许可。
- `m2v master --project <dir>`：ProRes/DNxHR 母版与交付版。
- `m2v render --profile cinematic`：高质量渲染入口。

cinematic 评分卡十项，每项 0–4 分，低于 34/40 不通过：镜头语言、光影、材质细节、构图、节奏剪辑、声音设计、信息清晰、图文关系、旁白同步、技术质量。hero 镜头与 20 秒样片必须实际观看，记录时间码、问题和复查结果；不能观看时如实说明，不能声称电影级。

### 8. 文档与流程

- 修正固定示例名单、effects 渲染口径、路线图范围。
- 新增 `references/cinematic-video.md`：参考板、look bible、shot grammar、材质/后期/声音清单、20 项检查表、反模式与成本。
- SKILL.md 增加档位表、cinematic 触发词、阶段门禁（Brief → Look-dev → Hero → Full film → QA/Master）。
- `production-workflow.md` 增加 cinematic 分支；`visual-review-rubric.md` 增加十项评分卡。
- `storyboard-schema.md` 增加可选字段；`render-contract.md` 增加后期/母版契约；`media-contract.md` 增加音频母版与资产审计；`design-tokens.md` 说明 cinematic look 不替代作品自由设计。
- 更新 `openspec/config.yaml` 的 context；更新 `PROJECT_PLAN.md` 与 README 的路线/能力。
- 运行 `python .agents/skills/material2video/scripts/sync_docs.py --check` 与相对链接检查。

## Risks / Trade-offs

- **渲染成本**：后期 + SSAA + 运动模糊会让 hero 镜头成倍变慢。按镜头分级，只对 hero 开高质量；在 `lookdev` 阶段先量一次单帧成本，避免整片渲完才发现预算失控。
- **确定性**：后期库可能内部使用时间或随机数。所有 uniform 必须帧驱动，新增同帧 PSNR ≥ 60dB 测试；源码闸门继续扫描。
- **兼容性**：cinematic 母版 10bit/HEVC 不是所有播放器都支持。交付始终保留 H.264 兼容版；母版只作为归档与后续调色源。
- **流程冲突**：cinematic 的 look-dev 批准与现有「不新增用户确认」冲突。只在 cinematic 档显式增加，standard 不变；用户未选择 cinematic 时不触发。
- **示例数量**：固定示例仍为三个，不新增；太阳系改为 cinematic 样板，缓冲与试错保持 standard 回归，避免全部示例一起变慢。
- **依赖进行中变更**：`fix-code-scene-frame-capture` 正在改录制链路。本变更的录制相关任务在其归档后执行；不并行改同一批文件。
- **资产许可**：4K/8K 纹理、配乐与音效需要逐项留证；未知许可的 hero 资产阻断，避免把版权风险带进成片。
- **60 秒信息量**：9 段、约 230–260 字会牺牲部分天体细节。以「每章一个可识别主体 + 3 个 hero」为取舍，不追求 16 个天体逐一近景。

## Delivery

本提案只交付 OpenSpec 规划材料，不改代码、不改太阳系当前成片。apply 阶段的顺序：

1. 修正口径与文档，补 cinematic 参考文档。
2. 加档位、可选字段、CLI 与指纹。
3. 搭共享电影套件与确定性测试。
4. 太阳系 look-dev：60 秒脚本、shot list、4K 资产、3–5 张 4K 静帧、20 秒有声样片、音色 A/B。
5. 实现 hero 与全片、声音设计、UI 与渲染。
6. QA、母版、文档、验证、归档。

任务全部完成后按项目约定同步主规格、更新 README/规划/Skill、归档并提交。
