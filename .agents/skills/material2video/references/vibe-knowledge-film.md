# vibe-knowledge-film 制作指引

> 状态：C 夜曲已转成正式风格包 `styles/vibe-night`（2026-10-27）；B 寓言仍为临时登记、只读来源。
> 来源、许可与可用范围以[外部参考项目登记](external-projects.md)为准。
> 本文只说明如何查阅与转译，不改变制作阶段、评审职责或验收条件。

## 什么时候读

- 用户说「Vibe 知识大赏」「夜曲」「寓言」「无旁白字幕知识片」，或要求做「字幕把这句话演出来」的代码直出知识短片。
- 用户要求 `general` 作品借鉴 C 夜曲或 B 寓言的外观或观看方式。
- 只是普通参考视频拆解时，先按[参考视频逆向拆解](reference-video-analysis.md)；明确要求外观相似时，再按[参考风格契约](reference-style.md)执行，并叠加本文。

## 读取顺序

1. [外部参考项目登记](external-projects.md)：确认固定 commit、许可、受限项与可用文件。
2. 外部 `references/worlds.md`：读对应世界的底、色、版式、字幕、片名卡与声音。
3. 外部 `references/visual-grammar.md`：句型→画面、三区版式、颜色词汇、转场与动效手感。
4. 需要方法时读外部 `references/visualization.md` 的〇、二、三、四、五、六、八节，以及 `references/script.md`。
5. 需要样片证据时读 `examples/fold_C/storyboard.md` 或 `examples/pigeon_B/storyboard.md`。

不要把 `visualization.md` 第一节（四条参考片逐句拆解）或 `prompts.md` 第二节当作可用素材。

## 两套外观

### C 夜曲

已落地为正式风格包 `styles/vibe-night`：作品在 `project.json` 写 `style.id: "vibe-night"`，
按 [GUIDE](../../../../styles/vibe-night/GUIDE.md) 显式导入组件与资产。下列数值是包内
`tokens.json` 的语义来源，运行时以包内参数为准。

适合抽象概念或看不见的机制：把一个概念拆成几个当场可演的小实验。

- 底 `#010104`，中央深蓝光池 `#0B1830`（透明度 0.62）、细星点、暗角；金 `#F8D893`、冰蓝 `#64E3F6`、玫红 `#E84B75`、紫 `#8477D0`。
- 主体是认得出的东西：大字、数轴、波形，以及画得像实物的珠子、细胞、探测器。光点与连线只作底和片名卡装饰，不能代替讲解。
- 一个光点母题沿细线走、沿环绕或在字之间弹；镜头只做慢推与慢移。
- 外部的字幕 41px、字距 0.12、基线 87% 只作气质参考，不覆盖本项目的共享字幕层。

### B 寓言

适合心理或行为机制：从动物实验或生活场景讲到「你该怎么办」。

- 每场一幅代码画的扁平插画：大色块、少量细节、柔和渐变、不描边；远景、角色层、前景三层视差。
- 左上「本能读数」仪表是全片的尺子：0–150，100 以上为红区「超常」，每个例子都用同一把尺子量。
- 暖色场景盘、角色只做必要动作、规则卡与片名卡沿用金字暗场。
- 外部的字幕 48px、字距 0.07、基线 89.4%、逐字亮起只作气质参考，不覆盖本项目的共享字幕层。

## 视频参考

只使用自有样片；`info_C`、`stim_B` 等参考片复刻不纳入。

| 样片 | 可学做法 | 注意 |
|---|---|---|
| `examples/fold_C` | 一台摄影机用对数缩放从血管推进到珠串再拉出；有体积的实物画在底层不吃辉光；第 3 镜与第 8 镜回到同一画面，第一次是结果、第二次是原因 | 不复制珠子、细胞、镰刀等具体形象与文案例子 |
| `examples/pigeon_B` | 计时器按真实时间走；六镜六景别；字幕出现后 0.3 秒内有动作；保留无字幕的纯画面段 | 不复制鸽子、食槽、幸运袜等具体形象与文案例子 |

拆解方法按[参考视频逆向拆解](reference-video-analysis.md)；外观转译按[参考风格契约](reference-style.md)。样片画面、GIF、JPG 只能看，不得进入成片、评审包或风格包资产。

## 转译到 material2video

| 项目 | 规则 |
|---|---|
| 视频类型 | 仅 `general`；外部项目没有其他类型。 |
| 画幅 | 外部只做 1920×1080、30fps；横屏作品可直接对应。竖屏作品必须按[参考风格契约](reference-style.md)的画幅转译规则重新安置主体与文字。 |
| 字幕 | 共享字幕层（`web/src/frames.json`，横屏 40px、白字、深色底板）优先；外部字号、基线、逐字动效只作指导值，不覆盖共享层。无旁白作品可由场景在 `subtitleSafeArea` 内自绘屏幕字幕，按 [C 夜曲 GUIDE](../../../../styles/vibe-night/GUIDE.md#7-无旁白屏幕字幕约定) 执行。 |
| 外观采纳 | C 夜曲可直接选择正式风格包 `vibe-night`；仍须按 [参考风格契约](reference-style.md) 的 L1/L2/L3 与八项指标写入作品 `outputs/style-reference.md`，并在 `DESIGN.md` 记录来源项目、固定 commit、采用世界与不借清单。B 寓言尚未安装，只能按指导值转译。 |
| 只借方法 | 不采用外观时，在 `DESIGN.md` 标注「仅方法，不采用外观」，不要只写「参考了 vibe 风格」。 |
| 能力边界 | 不把外部 Canvas 引擎、字体或组件当作本项目组件；C 夜曲使用 `styles/vibe-night`，B 寓言未并入前 `project.json` 不得写 `style.id`。 |

## 不借清单

- 参考片的画面、字幕、贴图、片名卡母题、角色与具体场景。
- `examples/stim_B`、`examples/info_C`、`look_stim_B.jpg`、`look_info_C.jpg` 及其中的任何设计。
- 外部 `engine/`、`engine/fonts/`、GIF/JPG、样片 `film.js`。
- 外部字幕的逐字动效与字号基线，不得覆盖共享字幕层。
- 不新增 CSS 主题作用域、`themes.json` 或其他并行主题机制。

## 记录与验收

| 结论 | 落到哪里 |
|---|---|
| 来源项目、固定 commit、采用世界 | `DESIGN.md` 与 `outputs/style-reference.md` |
| L1/L2/L3、八项指标、画幅转译 | `outputs/style-reference.md` |
| 采用规则与不借清单 | `DESIGN.md` |
| 只借方法、不采用外观 | `DESIGN.md` 明确标注 |

采用外观时仍按[参考风格契约](reference-style.md)做风格基准与同族冷审；本文不新增审核轮次或门禁。

## 未来合并

C 夜曲已转成正式风格包，组件以 TSX 重写并随包登记宋体资产；B 寓言仍未安装。B 寓言需要时
按[风格接入契约](style-pack.md)另建 `styles/vibe-fable` 并评估角色、视差与仪表组件；
涉及新风格包、组件或契约变化时另走 OpenSpec 评估。B 寓言合并前，`project.json` 不得写指向
本登记的 `style.id`；C 夜曲作品写 `style.id: "vibe-night"`。
