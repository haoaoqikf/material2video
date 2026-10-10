# 缓冲区标杆示例

这个例子把“缓冲吸收短期波动”表达为**单场景动态叙事**：同一套入口管道、水箱与限流出口贯穿全片，水位、溢出口与水滴的变化推动论证。产品表达是“一个观点，一个场景，一段动态叙事”。

## 文件

- `article.md`：标准篇幅的观点型输入（正文计 152 字）。
- `storyboard.json`：v4 单一 world、五个叙事阶段、全局动作、十个状态轨道与六段镜头声明。
- `scenes/water-tank.tsx`：同一个 code 世界的帧驱动画面（水位只读剧本声明的对象状态）。
- `assets/`：早期版本使用的 CC0 背景音与节拍音效素材（许可见 `assets/LICENSE.md`）；当前 v4 分镜未声明 `soundtrack`，`prepare.py` 只产出旁白音轨。
- `script-design.md`：五幕口播设计与解释职责。
- `motion-design.md`：持续身份、状态变化与示意边界。
- `review.md`：本轮标杆验收记录（材料摘要、结论与本轮修掉的问题）。
- `production.template.json`：抽象制作记录模板，所有结论为 pending，不构成本作品的通过记录。

## 当前验收状态

已通过：Python v4 严格校验（5 个阶段 / 1290 帧 / 43.0 秒声明）、输入语义审查（152 字，`lengthStatus pass`）、语音准备与实际时长（口播计 154 字 / 42.00 秒，`durationStatus pass`）、关键幕（`pulse`／`smooth`／`overload`）与全片静态/有声动态评审、五项口播内容评审、五项连续性评审、`--check-determinism`（5 帧中 4 帧完全一致、1 帧 91.0 dB，阈值 60 dB）、1080×1920 @30fps 正式 MP4 解码验收（1260 帧 / 42.00 秒，H.264 High yuv420p(tv,bt709) + AAC-LC 44.1kHz 立体声，22 条字幕 cue）。计数口径按 `article_text`：不含标题、标点与空白（正文 180 个码点 / 计 152 字），声明时长 43.0 秒，实际时长 42.00 秒。

验收摘要与材料摘要在 `review.md`；带每项证据的本地制作记录在 `videos/examples/buffer-smoothing/production.json`（不入库）。声音听感本轮未试听，见 `review.md` 的遗留限制。

## 本地制作

从项目根目录运行 `validate.py`，先按 Skill 的输入审查流程检查 `article.md`，通过后再准备媒体和真实评审材料。生成的制作记录、评审材料与 MP4 位于忽略 Git 的 `videos/examples/buffer-smoothing/` 下，不加入仓库。
