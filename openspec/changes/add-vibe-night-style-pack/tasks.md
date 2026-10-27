## 1. 风格包与规格

- [ ] 1.1 创建 `styles/vibe-night/style.json`、`tokens.json`、`GUIDE.md`；清单声明 `types: ["general"]`、`frames: [{"width":1920,"height":1080}]`，tokens 写入 C 夜曲的底色、光池、色板语义、三区版式、字号/字距/基线、转场与动效参数；验证 `uv run m2v styles --json` 返回 `vibe-night`，字段非法、类型或画幅不匹配时明确失败。
- [ ] 1.2 实现 C 夜曲组件：`night-backdrop`、`spark`、`comet`、`glow-text`、`chapter-mark`、`title-night`、`flash`、`dip`、`number-line`；全部由帧号与固定种子驱动，字体和资产就绪后调用 `ready()`；验证同一帧两次录制一致，包外导入与符号链接越界失败。
- [ ] 1.3 加入宋体资产与许可：包内放置子集化 Noto Serif SC woff2 与 OFL 许可，`style.json` 的 `assets` 声明 `source` 与 `license`；验证资产可被 `m2v/style/assets/*` 导入、加载失败会阻断录制、常用字在字体 cmap 中齐全。
- [ ] 1.4 同步规格与文档：修改 `openspec/specs/style-registry/spec.md`、`styles/README.md`、`openspec/specs/README` 或索引相关说明、[风格接入契约](../../.agents/skills/material2video/references/style-pack.md) 与 [外部参考项目登记](../../.agents/skills/material2video/references/external-projects.md) 的状态；README 的“当前风格目录为空”改为已登记 `vibe-night`；验证相对链接、JSON 示例与 `sync_docs.py --check` 无漂移。

## 2. 讲解设计与屏幕字幕约定

- [ ] 2.1 新增 `.agents/skills/material2video/references/explainer-design.md`：六种画法、找形象决策树、三问、五分之一不画、数量可数化、无旁白字幕稿的量与句式、看图改图检查表；在 [通用作品创作](../../.agents/skills/material2video/references/article-to-storyboard.md) 与 [视觉复核](../../.agents/skills/material2video/references/visual-review-rubric.md) 增加引用，不改门禁与审核轮次。
- [ ] 2.2 把屏幕字幕约定写入 `styles/vibe-night/GUIDE.md` 与 `explainer-design.md`：`content.props.screenSubtitles` 的字段、时段、单行上限、安全区、无底板、与共享字幕层的互斥；验证有旁白作品不读取该字段、共享字幕层与分镜 schema 未改动。

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
- [ ] 4.4 同步主规格并归档：把 `style-registry` 的修改与 `vibe-night-style` 新规格写入 `openspec/specs/`，将变更移入 `openspec/changes/archive/`，提交归档结果。
