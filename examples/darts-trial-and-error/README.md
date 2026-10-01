# 飞镖试错示例

这个例子把“低成本、高频试错”表达为**单场景动态叙事**：投掷者、飞镖和靶构成持续存在的视觉世界，投掷与落点变化推动论证。产品表达是“一个观点，一个场景，一段动态叙事”。

## 文件

- `article.md`：标准篇幅的观点型输入。
- `storyboard.json`：v4 单一 world、四个叙事阶段、全局动作与镜头声明。
- `scenes/darts-trial-and-error.tsx`：同一个 code 世界的帧驱动画面。
- `motion-design.md`：持续身份、变化与示意边界。
- `review.md`：本轮标杆验收记录（材料摘要、结论与本轮修掉的问题）。
- `production.template.json`：抽象制作记录模板，所有结论为 pending，不构成本作品的通过记录。

## 当前验收状态

已通过：Python v4 严格校验（4 个阶段 / 1200 帧 / 40.0 秒）、输入语义审查、语音准备与实际时长（正文 149 字 / 口播 149 字 / 40.43 秒）、关键幕与全片静态/有声动态评审、五项口播内容评审、五项连续性评审、`--check-determinism`（PSNR ≥ 60 dB）、1080×1920 @30fps 正式 MP4 解码验收（1213 帧 / 40.43 秒，音轨 AAC-LC 44.1kHz 立体声）。计数口径按 `article_text`：不含标题、标点与空白（正文 171 个码点 / 计 149 字），声明时长 40 秒，实际时长 40.43 秒。

验收摘要与材料摘要在 `review.md`；带每项证据的本地制作记录在 `videos/examples/darts-trial-and-error/production.json`（不入库）。声音听感本轮未试听，见 `review.md` 的遗留限制。

## 本地制作

从项目根目录运行 `validate.py`，先按 Skill 的输入审查流程检查 `article.md`，通过后再准备媒体和真实评审材料。生成的制作记录、评审材料与 MP4 位于忽略 Git 的 `videos/examples/darts-trial-and-error/` 下，不加入仓库。
