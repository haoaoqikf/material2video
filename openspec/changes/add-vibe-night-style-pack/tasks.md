## 1. 风格包与规格

- [x] 1.1 创建 `styles/vibe-night/style.json`、`tokens.json`、`GUIDE.md`；清单声明 `types: ["general"]`、`frames: [{"width":1920,"height":1080}]`，tokens 写入 C 夜曲的底色、光池、色板语义、三区版式、字号/字距/基线、转场与动效参数；验证 `uv run m2v styles --json` 返回 `vibe-night`，字段非法、类型或画幅不匹配时明确失败。
- [x] 1.2 实现 C 夜曲组件：`night-backdrop`、`spark`、`comet`、`glow-text`、`chapter-mark`、`title-night`、`flash`、`dip`、`number-line`、`screen-subtitle`；全部由帧号与固定种子驱动，字体和资产就绪后调用 `ready()`；验证同一帧两次录制一致，包外导入与符号链接越界失败。
- [x] 1.3 加入宋体资产与许可：包内放置可零依赖检查的 Noto Serif SC TTF 子集与 OFL 许可，`style.json` 的 `assets` 声明 `source` 与 `license`；验证资产可被 `m2v/style/assets/*` 导入、加载失败会阻断录制。
- [x] 1.4 同步规格与文档：修改 `openspec/specs/style-registry/spec.md`、`styles/README.md`、[风格接入契约](../../.agents/skills/material2video/references/style-pack.md) 与 [外部参考项目登记](../../.agents/skills/material2video/references/external-projects.md) 的状态；README 的“当前风格目录为空”改为已登记 `vibe-night`；验证相对链接、JSON 示例与 `sync_docs.py --check` 无漂移。
- [x] 1.5 风格要求声明：清单新增可选 `requires.narration`，`vibe-night` 声明 `none`；`validate` 与 `prepare` 对有旁白作品明确失败；验证未知键、非法值与无约束风格的行为。
- [x] 1.6 严格缺字检查：`prepare` 用风格包字体自身 cmap 检查屏幕字幕与场景字面量，不与全局字体取并集；字体格式不可解析时明确失败；验证全局字体有字、包内字体缺字仍报错。

## 2. 讲解设计与屏幕字幕

- [x] 2.1 新增 `.agents/skills/material2video/references/explainer-design.md`：六种画法、找形象决策树、三问、五分之一不画、数量可数化、无旁白字幕稿的量与句式、看图改图检查表；在 [通用作品创作](../../.agents/skills/material2video/references/article-to-storyboard.md) 与 [视觉复核](../../.agents/skills/material2video/references/visual-review-rubric.md) 增加引用，不改门禁与审核轮次。
- [x] 2.2 把屏幕字幕约定写入 `styles/vibe-night/GUIDE.md` 与 `explainer-design.md`：`content.props.screenSubtitles` 的字段、时段、单行上限、安全区、无底板、与共享字幕层的互斥；验证有旁白作品声明该字段会被拒绝、共享字幕层与分镜 schema 未改动。
- [x] 2.3 屏幕字幕进入证据链：组件默认输出 `data-m2v-role="subtitle"`；`measurement` 新增可选 `subtitleRoles`，检查安全区、单行与横向溢出；验证 `textPlan` 窗口、越界与溢出用例。
- [x] 2.4 安全区单一真源：tokens 删除复制几何，组件从场景上下文 `subtitleSafeArea` 取值；验证 GUIDE 示例与测试不再固化安全区数值。
- [x] 2.5 帧率与注释约定：`screenSubtitleFadeMs` 按 fps 换算；GUIDE 明确 30fps 设计基准、`chapter-mark.latin` 只用于有语义英文名；`explainer-design.md` 标注五分之一为参考比例。

## 3. C 夜曲试制片

- [ ] 3.1 在 `videos/general/<slug>/` 初始化作品，确定 30–45 秒原创选题与事实表，编写 `DESIGN.md` 与 `outputs/style-reference.md`；声明 `style.id: "vibe-night"`；验证作品目录被 Git 忽略、事实出处可核、未使用 `fold_C`/`pigeon_B` 的主题或形象。
- [ ] 3.2 编写 v8 分镜与屏幕字幕：每句标注一种画法，约五分之一不画，每个场景撑两句以上，屏上数字可复算；验证遮住字幕仍能读出讲解、每句名词在屏上找得到、屏幕字幕不超过 28 字且在安全区内。
- [ ] 3.3 按分镜实现场景与运动，先做最难一镜；用关键帧、完整动态窗口与 393 宽截图复核主体尺度、遮挡、色彩语义与手机可读性；验证屏幕字幕换行、溢出与遮挡风险已被检查，发现即改。
- [ ] 3.4 编排声音：只用原创合成音效或已登记许可素材，事件与画面变化同步；验证自动音频信号检查通过、无未授权外部音轨。
- [ ] 3.5 执行 validate、prepare 与一次完整 render；按 v2 制作合同完成核心样片、全片粗片与最终独立评审，评审包按隔离要求提供；验证技术 QA、帧证据、字幕时段与同一候选绑定，未关闭项如实披露。

## 4. 验证与交付

- [ ] 4.1 运行回归：`uv run pytest`、`uv run pytest -m "not slow"`、`pnpm -C web test`；验证三个固定示例、金融与住宅类型、共享字幕层和既有无风格作品不受影响。
- [ ] 4.2 核对文档一致性与许可：`explainer-design.md`、GUIDE、README、外部登记中的相对链接、JSON 示例与状态描述一致；字体 OFL 许可以及外部项目固定提交记录齐全。
- [ ] 4.3 检查暂存范围：只包含风格包、文档、测试与验证记录，排除 `videos/` 作品产物、媒体、缓存与凭据；提交并记录 commit。
- [ ] 4.4 同步主规格并归档：把 `style-registry`、`font-coverage`、`checkpoint-based-visual-acceptance` 与 `vibe-night-style` 的修改写入 `openspec/specs/`，将变更移入 `openspec/changes/archive/`，提交归档结果。
