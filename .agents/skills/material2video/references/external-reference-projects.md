# 外部参考项目与转译指南


本文件登记 material2video 制作时可以查阅的外部参考项目。登记只保存来源、许可、可用范围与使用方式，不复制外部代码、字体或媒体。

**不是风格包**：本登记不被 `m2v styles` 读取，不通过 `project.json` 的 `style.id` 选择，渲染链路也不读取。风格包的清单与接入方式见[风格接入契约](style-pack.md)。

## 使用规则

- 只在制作 `general` 视频、且用户明确要求借鉴对应风格或视频参考时查阅。
- 外观借鉴仍按[参考风格契约](reference-style.md)执行：L1/L2/L3、八项指标、画幅转译、同族冷审与 `outputs/style-reference.md`。
- 参考画面、字幕、贴图不得进入成片；渲染链路不读取外部目录或 `refs/`。
- 外部项目仍是来源事实的权威；本仓库只登记固定 commit 下的可用范围。
- 上游 commit、许可或目录结构变化时，先核对再更新本表与对应项目指引。

## 登记格式

| 字段 | 含义 |
|---|---|
| `id` | 稳定标识，与项目指引文件名一致 |
| `status` | `temporary` 指项目登记本身；其中两套外观 C 夜曲与 B 寓言均已转成正式风格包 |
| `localPath` | 本机路径，仅作定位提示；其他机器按上游与固定 commit 获取 |
| `upstream` / `pinnedCommit` | 来源仓库与核验过的提交 |
| `verifiedAt` | 最近一次核对来源、许可与路径的日期 |
| `license` / `licenseExcluded` | 可用许可范围与明确排除项 |
| `styles` / `videoReferences` | 可查阅的风格与视频参考 |
| `applicableTypes` / `frames` | 适用的视频类型与画幅 |
| `guide` | 本仓库内的项目制作指引 |

## 已登记项目

### `vibe-knowledge-film`

| 字段 | 值 |
|---|---|
| `id` | `vibe-knowledge-film` |
| 显示名 | vibe-knowledge-film（抖音「Vibe 知识大赏」式无旁白知识短片） |
| `status` | `temporary`：C 夜曲已作为 `styles/vibe-night` 落地（2026-10-27），B 寓言已作为 `styles/vibe-fable` 落地（2026-10-28） |
| `localPath` | `C:\D_Merged_From_D\project\third-party\vibe-knowledge-film`（仅本机） |
| `upstream` | `https://github.com/HeyChengC/vibe-knowledge-film.git` |
| `pinnedCommit` | `62d51508aad00003dc6209afa80c4b5dc540de59`（2026-10-13） |
| `verifiedAt` | 2026-10-27 |
| `license` | MIT：引擎、脚本与方法文档；排除项见下 |
| `applicableTypes` | `general` |
| `frames` | 1920×1080、30fps；无旁白、底部单行字幕 |
| `guide` | [vibe-knowledge-film 制作指引](external-reference-projects.md#vibe-knowledge-film-项目使用指引) |

#### 可用风格

只登记 **C 夜曲** 与 **B 寓言**。上游的 A 鎏金暗场已不再作为可选外观，不登记。

| 世界 | 来源 | 适用 | 关键指导值 |
|---|---|---|---|
| C 夜曲 | `references/worlds.md` 的「C 夜曲」、`references/visual-grammar.md`、`engine/vk-kit.js` 的 `PAL.night`/`SUB.night`、`engine/vk.js` 的 `BG.night` | 抽象概念、看不见的机制，拆成当场可演的小实验 | 底 `#010104`，中央深蓝光池 `#0B1830`（透明度 0.62）；主体字 `#F8F9F8`；金 `#F8D893`、冰蓝 `#64E3F6`、玫红 `#E84B75`、紫 `#8477D0`；宋体大字、光点母题、慢推慢移。字幕 41px、字距 0.12、基线 87% 仅作指导 |
| B 寓言 | `references/worlds.md` 的「B 寓言」、`references/visual-grammar.md`、`engine/vk-kit.js` 的 `PAL.flat`/`SUB.flat` | 心理、行为机制，从动物或生活场景讲到「你该怎么办」 | 代码画的扁平插画、三层视差、左上「本能读数」仪表、暖色场景盘、角色与规则卡。字幕 48px、字距 0.07、基线 89.4%、逐字亮起仅作指导 |

这些数值是**转译后的指导值**。C 夜曲已转成可安装的正式风格包 `styles/vibe-night`，
运行时以包内 `tokens.json`、组件与 `GUIDE.md` 为准；两套均已安装为正式风格包，本表数值只作来源对照。
外部字幕外观与 material2video 共享字幕层（`web/src/frames.json`，横屏 40px、白字、深色底板）
不兼容；共享层优先，不得覆盖。无旁白作品可由场景自绘屏幕字幕，约定见
[C 夜曲 GUIDE](../../../../styles/vibe-night/GUIDE.md#7-无旁白屏幕字幕约定)。

#### 视频参考（仅自有样片）

| 样片 | 世界 | 内容 | 可查阅文件 | 可学做法 |
|---|---|---|---|---|
| `examples/fold_C` | C 夜曲 | 《折叠》开头 33 秒 | `storyboard.md`、`film.js`、`fold_C.gif`、`look_fold_C.jpg` | 对数缩放推拉；实物绘制在底层不吃辉光；同一画面首尾回场 |
| `examples/pigeon_B` | B 寓言 | 《鸽子的迷信》开头 33 秒 | `storyboard.md`、`film.js`、`pigeon_B.gif`、`look_pigeon_B.jpg` | 计时器按真实时间走；六镜六景别；无字幕纯画面段 |

GIF/JPG 只作分析：不复制进本仓库，不作为素材或风格包资产，不进入成片。样片 `film.js` 只读，不整段移植。

#### 方法文档可用范围

| 文件 | 可用范围 |
|---|---|
| `references/visualization.md` | 〇、二、三、四、五、六、八节：配图与讲解、六种画法、何时画/不画、找形象、文案与分镜表、看图改图 |
| `references/script.md` | 全篇：无旁白字幕稿的量、骨架、句式与事实 |
| `references/visual-grammar.md` | 全篇：句型→画面、三区版式、颜色词汇、转场与动效手感 |
| `references/prompts.md` | 第一、三、四、五节：完整 brief 模板、分步提示词、返工话术、一句话版 |
| `references/engine.md` | 可读引擎 API 与常见坑，不复制引擎代码 |

#### 许可排除项（不得复制、发布或入片）

- `references/analysis.md`
- `references/prompts.md` 第二节（三条参考片的逆向 brief）
- `references/visualization.md` 第一节（四条参考片逐句拆解）及按参考片记下的字幕与画面
- `examples/stim_B`、`examples/info_C`
- `examples/look_stim_B.jpg`、`examples/look_info_C.jpg`
- 外部项目分析的参考片：《运气的形状》《超常刺激》《信息论·惊奇之学》《自指·我是个怪圈》。版权属原作者，只供学习对照。

#### 不复制清单

- `engine/`（Canvas 运行时）
- `engine/fonts/`（TTF；OFL 许可，由上游 `get_fonts.py` 下载，约 45MB）
- `examples/*.gif`、`examples/*.jpg`
- `examples/*/film.js`（样片实现，只读）
- `scripts/new_film.py`

#### 后续合并

- C 夜曲已按[风格接入契约](style-pack.md)转成 `styles/vibe-night`，组件以 TSX 重写并随包登记宋体资产。
- B 寓言已转成 `styles/vibe-fable`：扁平插画舞台、三层视差、本能读数仪表、对照计数、引线标注、规则卡与逐字亮起的屏幕字幕以 TSX 重写；不随包携带字体，使用宿主已注册的 `M2V Sans`。
- 两套风格各配一个示例：`styles/examples/vibe-night/fold/` 与 `styles/examples/vibe-fable/pigeon/`，按本页登记的 `fold_C`、`pigeon_B` 选题与分镜重写，实现与媒体自绘。示例放在保留目录 `styles/examples/`，不进包内（否则改示例会让所有使用该风格的作品准备失效），也不占用 `examples/` 的三个固定名额。
- 共享字幕层仍以 `web/src/frames.json` 为准，不复制外部字幕外观；无旁白屏幕字幕按各包 GUIDE 的约定由作品自绘。
- 作品选择风格应写 `style.id: "vibe-night"` 或 `style.id: "vibe-fable"`；指向外部登记的 ID 不被接受。
- 创建新风格包、组件或改变契约时另走 OpenSpec 评估。

#### 维护

```powershell
git -C "C:\D_Merged_From_D\project\third-party\vibe-knowledge-film" rev-parse HEAD
# 期望 62d51508aad00003dc6209afa80c4b5dc540de59
```

上游 HEAD 变化或重新克隆后，重新核对 `LICENSE`、许可排除项与目录结构，再更新 `pinnedCommit` 与 `verifiedAt`。许可条款变化时先停用登记，不沿用旧结论。


## vibe-knowledge-film 项目使用指引



> 状态：C 夜曲与 B 寓言已分别转成正式风格包 `styles/vibe-night`（2026-10-27）与 `styles/vibe-fable`（2026-10-28）。
> 来源、许可与可用范围以[外部参考项目登记](external-reference-projects.md)为准。
> 本文只说明如何查阅与转译，不改变制作阶段、评审职责或验收条件。

正式风格包表示已注册可接入，不代表完整吸收原作讲解与镜头机制。四种机制的制作方法见
[讲解设计](explainer-design.md#四种讲解机制的执行方法)，包的技术与表现验证边界见
[GUIDE](../../../../styles/vibe-night/GUIDE.md#可用范围与表现验证)。参考采用项须关联作品的完整证据窗口，
不能以外观组件或制作指导替代实际表现验证。

### 什么时候读

- 用户说「Vibe 知识大赏」「夜曲」「寓言」「无旁白字幕知识片」，或要求做「字幕把这句话演出来」的代码直出知识短片。
- 用户要求 `general` 作品借鉴 C 夜曲或 B 寓言的外观或观看方式。
- 只是普通参考视频拆解时，先按[参考视频逆向拆解](reference-video-analysis.md)；明确要求外观相似时，再按[参考风格契约](reference-style.md)执行，并叠加本文。

### 读取顺序

1. [外部参考项目登记](external-reference-projects.md)：确认固定 commit、许可、受限项与可用文件。
2. 外部 `references/worlds.md`：读对应世界的底、色、版式、字幕、片名卡与声音。
3. 外部 `references/visual-grammar.md`：句型→画面、三区版式、颜色词汇、转场与动效手感。
4. 需要方法时读外部 `references/visualization.md` 的〇、二、三、四、五、六、八节，以及 `references/script.md`。
5. 需要样片证据时读 `examples/fold_C/storyboard.md` 或 `examples/pigeon_B/storyboard.md`。

不要把 `visualization.md` 第一节（四条参考片逐句拆解）或 `prompts.md` 第二节当作可用素材。

### 两套外观

#### C 夜曲

已落地为正式风格包 `styles/vibe-night`：作品在 `project.json` 写 `style.id: "vibe-night"`，
按 [GUIDE](../../../../styles/vibe-night/GUIDE.md) 显式导入组件与资产。下列数值是包内
`tokens.json` 的语义来源，运行时以包内参数为准。

适合抽象概念或看不见的机制：把一个概念拆成几个当场可演的小实验。

- 底 `#010104`，中央深蓝光池 `#0B1830`（透明度 0.62）、细星点、暗角；金 `#F8D893`、冰蓝 `#64E3F6`、玫红 `#E84B75`、紫 `#8477D0`。
- 主体是认得出的东西：大字、数轴、波形，以及画得像实物的珠子、细胞、探测器。光点与连线只作底和片名卡装饰，不能代替讲解。
- 一个光点母题沿细线走、沿环绕或在字之间弹；镜头只做慢推与慢移。
- 外部的字幕 41px、字距 0.12、基线 87% 只作气质参考，不覆盖本项目的共享字幕层。

#### B 寓言

适合心理或行为机制：从动物实验或生活场景讲到「你该怎么办」。

- 每场一幅代码画的扁平插画：大色块、少量细节、柔和渐变、不描边；远景、角色层、前景三层视差。
- 上游用左上「本能读数」仪表贯穿全片：0–150、100 以上为红区「超常」是其视觉设计，不构成实际测量依据。本项目只有核实对象、单位、来源及比较口径后才能使用量化读数；无依据时改用定性状态或有来源的时间、次数。
- 暖色场景盘、角色只做必要动作、规则卡与片名卡沿用金字暗场。
- 外部的字幕 48px、字距 0.07、基线 89.4%、逐字亮起只作气质参考，不覆盖本项目的共享字幕层。

### 视频参考

只使用自有样片；`info_C`、`stim_B` 等参考片复刻不纳入。

| 样片 | 可学做法 | 注意 |
|---|---|---|
| `examples/fold_C` | 一台摄影机用对数缩放从血管推进到珠串再拉出；有体积的实物画在底层不吃辉光；第 3 镜与第 8 镜回到同一画面，第一次是结果、第二次是原因 | 不复制珠子、细胞、镰刀等具体形象与文案例子 |
| `examples/pigeon_B` | 计时器按真实时间走；六镜六景别；字幕出现后 0.3 秒内有动作；保留无字幕的纯画面段 | 不复制鸽子、食槽、幸运袜等具体形象与文案例子 |

拆解方法按[参考视频逆向拆解](reference-video-analysis.md)；外观转译按[参考风格契约](reference-style.md)。样片画面、GIF、JPG 只能看，不得进入成片、评审包或风格包资产。

### 转译到 material2video

| 项目 | 规则 |
|---|---|
| 视频类型 | 仅 `general`；外部项目没有其他类型。 |
| 画幅 | 外部只做 1920×1080、30fps；横屏作品可直接对应。竖屏作品必须按[参考风格契约](reference-style.md)的画幅转译规则重新安置主体与文字。 |
| 字幕 | 共享字幕层（`web/src/frames.json`，横屏 40px、白字、深色底板）优先；外部字号、基线、逐字动效只作指导值，不覆盖共享层。无旁白作品可由场景在 `subtitleSafeArea` 内自绘屏幕字幕，按 [C 夜曲 GUIDE](../../../../styles/vibe-night/GUIDE.md#7-无旁白屏幕字幕约定) 执行。 |
| 外观采纳 | C 夜曲选 `style.id: "vibe-night"`，B 寓言选 `style.id: "vibe-fable"`；仍须按 [参考风格契约](reference-style.md) 的 L1/L2/L3 与八项指标写入作品 `outputs/style-reference.md`，并在 `DESIGN.md` 记录来源项目、固定 commit、采用世界与不借清单。 |
| 只借方法 | 不采用外观时，在 `DESIGN.md` 标注「仅方法，不采用外观」，不要只写「参考了 vibe 风格」。 |
| 能力边界 | 不把外部 Canvas 引擎、字体或组件当作本项目组件；两套外观分别使用 `styles/vibe-night` 与 `styles/vibe-fable`，不得写指向外部登记的 `style.id`。 |

### 不借清单

- 参考片的画面、字幕、贴图、片名卡母题、角色与具体场景。
- `examples/stim_B`、`examples/info_C`、`look_stim_B.jpg`、`look_info_C.jpg` 及其中的任何设计。
- 外部 `engine/`、`engine/fonts/`、GIF/JPG、样片 `film.js`。
- 外部字幕的逐字动效与字号基线，不得覆盖共享字幕层。
- 不新增 CSS 主题作用域、`themes.json` 或其他并行主题机制。

### 记录与验收

| 结论 | 落到哪里 |
|---|---|
| 来源项目、固定 commit、采用世界 | `DESIGN.md` 与 `outputs/style-reference.md` |
| L1/L2/L3、八项指标、画幅转译 | `outputs/style-reference.md` |
| 采用规则与不借清单 | `DESIGN.md` |
| 只借方法、不采用外观 | `DESIGN.md` 明确标注 |

采用外观时仍按[参考风格契约](reference-style.md)做风格基准与同族冷审；本文不新增审核轮次或门禁。

### 未来合并

两套外观都已转成正式风格包：C 夜曲为 `styles/vibe-night`，B 寓言为 `styles/vibe-fable`；
组件以 TSX 重写，夜曲随包登记宋体资产，寓言复用宿主已注册的无衬线字体。涉及新风格包、
新组件或契约变化时另走 OpenSpec 评估。作品选择外观写 `style.id: "vibe-night"` 或
`style.id: "vibe-fable"`，不写指向本登记的 ID。
