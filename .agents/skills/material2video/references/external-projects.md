# 外部参考项目登记

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
| `guide` | [vibe-knowledge-film 制作指引](vibe-knowledge-film.md) |

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
