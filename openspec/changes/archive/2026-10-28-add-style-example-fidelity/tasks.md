## 1. 共享相机原语

- [x] 1.1 新建 `web/src/code-scene/painter/camera.ts`：导出 `cameraAt(keys, progress)`，缩放按对数空间插值、焦点按缩放反比加权、缓动缺省 `sineInOut`；纯函数，不读挂钟与随机源。在 `painter/index.ts` 导出并同步 `references/code-scene-runtime.md`。
- [x] 1.2 新建 `web/src/code-scene/painter/camera.test.ts`：同输入两次求值相等、进度 0/1 精确落在端点、`scale=1→4` 的中点返回 2、空表与越界进度明确报错。`pnpm -C web test` 全通过，既有 `painter.test.ts` 不回归。

## 2. vibe-night 色板与 fold 重制

- [x] 2.1 `styles/vibe-night/tokens.json` 增加 `colors.blood` 与 `colors.oxygen` 语义色，同步 `styles/vibe-night/GUIDE.md` 色板表与 `style-reference` 的取色说明。
- [x] 2.2 `fold.tsx` 改为固定世界坐标（珠间距 31.5、细胞半径、团半径）+ 一条覆盖九幕的连续相机表；屏幕位置由 `cameraAt` 求得，九幕共享同一套几何，0 硬切。
- [x] 2.3 `bead()` 改四段径向渐变球体；`cell()` 改五段渐变深红圆盘 + 内凹叠边 + 左上高光弧；氧气改暖红。
- [x] 2.4 折叠目标改六角格密排（六角格上走遍 146 格），折完是一团而非螺旋环；`rod`/`push` 幕补内部空间感。
- [x] 2.5 补参考的顶部微型注释（中 27 + 西 26 等宽、字距 5–6）与珠下方字母行；`chapterStart` 改用幕内帧，删掉 `total * 0.16`。
- [x] 2.6 底色改为保留蓝色信息的近黑（不再用 `P.clear('#010104')` 压成绝对黑），确认 `NightBackdrop` 的光池可见。

## 3. vibe-fable pigeon 重制

- [x] 3.1 建立按幕的镜头表（全景 / 计时器特写 / 中景 / 近景 / 慢推 / 计时器前置），每幕帧区间内缓动，幕内不硬切。
- [x] 3.2 `bird()` 改为多层色块（尾、身、翅、翅纹、颈三色、头、喙、眼），比例对齐参考的身体长:高≈1.5。
- [x] 3.3 修复米墙亮度溢出（实测 253.7）：调 `WALL` 与 `bloom`，在场景内补暗角；目标落在 175–195 的中间调。
- [x] 3.4 修复 `feedPhase`：以「上一次喂食 = max(FEED_TIMES ≤ t)」判定 `drop`，跨幕不再漏事件。
- [x] 3.5 收束幕的组件取舍：原版 33 秒未使用规则卡与对照计数，本轮**不启用**，理由写入 GUIDE；仅当冷审认为缺少它们导致「不是同一部片的视觉系统」时才补。

## 4. 声音

- [x] 4.1 用 `uv run m2v general sounds catalog` 选定拟音，`sounds import` 把 4–6 个合成音效登记进两个示例的 `assets/sound-sources.json`。
- [x] 4.2 两份 `storyboard.json` 增加 `soundtrack.effects`，按关键揭示点用 `offsetFrames` 对齐（数珠子、第 6 颗翻转、氧分子落点、分子接上、投食、转圈起笔、收尾），增益落在 `-16` 到 `-30 dB`。
- [x] 4.3 prepare 后确认 `prepared.json` 的 `audio.segments` 不再是静音母带，`ffmpeg volumedetect` 的 `mean_volume` 显著高于 -91 dB。

## 5. 增补：跨幕时间、事件与分层范式

- [x] 5A.1 全片时间基准：两个示例都用作品声明的 `clock.startSeconds` 换算全片时间；fold 的相机表覆盖全片、幕边界不跳变。不为两个示例抽共享时间工具，机制已存在。
- [x] 5A.2 画面事件与声音对齐：音效 `offsetFrames` 对准画面动作帧号，事件对照表写进示例 README。先文档约定，不建抽象。
- [x] 5A.3 连续对象与形态变化：《折叠》的镰刀由同一参数域连续插值，珠子折前折后保持索引与颜色身份；结论写入示例 README，暂不抽通用工具。
- [x] 5A.4 完整行为编排：《鸽子》需清楚演出「找食物 → 转圈 → 进食 → 再转圈」；两个示例若出现同构关键帧表，再评估通用动作工具。
- [x] 5A.5 设计指导范例：在 `references/explainer-design.md` 补一段「对象状态 → 动作 → 结果 → 声音」四栏范例，用《折叠》第 6 颗珠子作例。
- [x] 5A.6 分层绘制范式：把 `background → under → paint → overlay` 的四层分工（实物不吃辉光、发光体吃辉光、文字锐利）写进 `code-scene-runtime.md`。

## 6. 证据与验收

- [x] 5.1 新增并排图与八项指标量测脚本（可复算），参考侧取 `fold_C/review/*.png`、`pigeon_B/review/*.png`，本片侧取同叙事位置的 still。
- [x] 5.2 重跑 `lookdev`，代表帧覆盖每幕，且 `lookdev.json` 与接触表同源。
- [x] 5.3 两个示例各产出 `outputs/style-reference.md`（八项指标的参考值/实际值/差值）与并排基准图（不入库）。
- [x] 5.4 独立子代理冷审：隔离投喂并排图与时间码帧序列，结论回应「是否同一部片的视觉系统」；不一致项写入 `verification.md`。

## 7. 文档与交付

- [x] 7.1 修正文档滞后：`styles/vibe-night/GUIDE.md` 删去「B 寓言不在包内」等过期表述；`references/explainer-design.md` 补 B 寓言链接；两份示例 `README.md` 记录重制后的画法与已知限制。
- [x] 7.2 补勾 `openspec/changes/archive/2026-10-28-add-vibe-fable-style-and-examples/tasks.md` 的 4.2/4.3 并说明对应提交。
- [x] 7.3 验证：`uv run m2v validate`、`prepare`、`lookdev`、`pnpm -C web test`、`uv run pytest tests/test_vibe_fable_style.py tests/test_vibe_night_style.py`，确认 `examples/` 三个固定示例不回归。
- [x] 7.4 检查暂存范围（排除示例 `outputs/`、参考采样帧、生成媒体），提交实施；同步主规格并归档变更。
