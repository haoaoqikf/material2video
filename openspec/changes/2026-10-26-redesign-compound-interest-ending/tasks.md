## 1. 规格与设计合同

- [x] 1.1 新建本变更的 proposal/design/tasks 与规格增量，记录 S5 可数圆片堆与结尾方向；后续按用户反馈改为“结果屏直接收束”。
- [x] 1.2 更新 `examples/compound-interest/DESIGN.md` 五段时间表、S5 事件与收束、A 级时间结构与唯一 `m2v-checkpoints` 块。
- [x] 1.3 在问题表登记结果构成不清、结尾多余两项，并保留旧问题历史。

## 2. 数学、布局与场景

- [x] 2.1 `compoundMath.ts` 新增 `comparison`；TS 测试覆盖 40,000/174,494/134,494 与零收益差额；删除未使用的 `firstGainJourney`。
- [x] 2.2 `discs.tsx` 新增 40 枚块行布局；保持 `hillPositions` 与 `FIRST_DISC_INDEX` 不变。
- [x] 2.3 `compound.tsx` 重做 S5 左侧过渡、结果文字、结论与片名收束、相机；删除 S6/S7 与回扣组件。
- [x] 2.4 S5 正文在 1920 下 ≥59px；说明文字合计不超过 140 字；表头 25.8 秒隐去以控制预算。
- [x] 2.5 `storyboard.json` 改为 870 帧、25 个事件音，结论/片名各补一个轻响；环境床改为 29 秒；结果落定音移到 21.0 秒。
- [x] 2.6 快进段延长到 19.0–21.0 秒；结果屏 21.0–25.8 秒，表头保留到片尾，片名放大到 96px；动画短片的 animatic 改为逐段循环精确时长编码，修复 29 秒素材被编成 32 秒的问题。

## 3. 目标静帧与粗片

- [x] 3.1 `render_design_keyframes.py` 重画 S3/S5 的 establish/reveal/result 1920/852/393 静帧，并新增 `s5-closing`（hold）收束帧；S3 去掉重复算式。
- [x] 3.2 生成 S5 代表性帧，核对数量、差额、393 字号与重叠；G4 `S5-result` 通过。
- [x] 3.3 检查 19–29 秒的过渡、结果屏保持与收束时序。

## 4. 最终验收

- [x] 4.1 `validate`、`prepare`、`render`、`qa` 通过；响度−14.8 LUFS、true peak−1.4 dBFS、音画差0.00172秒、最长静止1.0秒。
- [x] 4.2 `S5-result` G4 通过；G1/G2/G3 技术检查通过。S1–S4 的既有 G4 量测问题仍开放，不属于本次改版。
- [x] 4.3 独立子代理对 S5 静帧与最终成片做隔离评审并导入：G6 结构 pass；G2/G3/G4/G5/G6 视觉文案 fail，必改项保持开放并披露。
- [x] 4.4 更新 README/SOURCES/VERIFICATION/visual-notes 与 Skill 复利示例，绑定新 SHA-256 `520333bd…` 与 preparedFingerprint `dfdaa2c2…`。
- [x] 4.5 运行 Python 与前端相关测试：前端96项、复利示例与严格示例37项通过；另外两个示例未改。

## 5. 提交与归档

- [x] 5.1 检查暂存内容，提交本次实现与文档（`0828ad6`），不夹带生成媒体。
- [ ] 5.2 同步主规格并把本变更移入 `openspec/changes/archive/`，提交归档结果；仅在评审关闭后执行。
