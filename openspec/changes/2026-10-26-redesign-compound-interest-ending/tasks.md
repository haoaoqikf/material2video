## 1. 规格与设计合同

- [x] 1.1 新建本变更的 proposal/design/tasks 与规格增量，记录用户已选的 S5 可数圆片堆与 S6 回扣第一笔方向。
- [x] 1.2 更新 `examples/compound-interest/DESIGN.md` 七段时间表、S5/S6/S7 事件、A 级时间结构与唯一 `m2v-checkpoints` 块。
- [x] 1.3 在问题表登记结果构成不清、结尾未回答开场问题两项，并保留旧问题历史。

## 2. 数学、布局与场景

- [x] 2.1 `compoundMath.ts` 新增 `comparison` 与 `firstGainJourney`；TS 测试覆盖 40,000/174,494/134,494、1,000→15,863.09、零收益。
- [x] 2.2 `discs.tsx` 新增 40 枚块行布局与结尾 4×4 布局；保持 `hillPositions` 与 `FIRST_DISC_INDEX` 不变。
- [x] 2.3 `compound.tsx` 重做 S5 左侧过渡、结果文字、S6 小舞台、S7 片名与相机；S5/S6 过渡无硬切。
- [x] 2.4 S5–S7 正文在 1920 下 ≥59px；S6/S7 背景 opacity 归零后只计 16 白 + 1 暗。S1–S4 沿用原字号，避免扩大改版范围。
- [x] 2.5 `storyboard.json` 更新 S6 事件偏移为 720/738/774，保持 28 个事件音与最后 840。

## 3. 目标静帧与粗片

- [x] 3.1 `render_design_keyframes.py` 重画 `s5-scale`，新增 `s6-ending` 与 `s7-closing` 的 1920/852/393 静帧；393 改由 ffmpeg 缩放。
- [x] 3.2 生成 S5/S6/S7 代表性帧，核对数量、差额、393 字号与重叠；S5/S6 布局迭代后 G4 通过。
- [x] 3.3 `preview` 19–30 秒检查过渡、第一枚飞行、16 枚长出与文字时序。

## 4. 最终验收

- [x] 4.1 `validate`、`prepare`、`render`、`qa` 通过；S7 无冻结，响度−14.86 LUFS、true peak−1.38 dBTP、音画差通过。
- [ ] 4.2 受影响检查点 `S5-result`、`S6-result`、`S7-result` 通过；G1 通过。G2 仅有 result 阶段独立静帧，establish/reveal 缺失，state=unverified；G3 因缺 establish 图未生成 animatic，尚未完成。
- [ ] 4.3 独立子代理对 S5/S6 静帧与最终成片做隔离评审；本轮未执行，已披露且不关闭评审项。
- [x] 4.4 更新 README/SOURCES/VERIFICATION/visual-notes 与 Skill 复利结尾示例，绑定新 SHA-256 `dc37d1ef…` 与 preparedFingerprint `7677d486…`。

## 5. 提交与归档

- [x] 5.1 运行 Python 与前端相关测试：前端96项、示例契约37项通过；另外两个示例未改。
- [ ] 5.2 检查暂存内容，提交本次实现与文档，不夹带生成媒体。
- [ ] 5.3 同步主规格并把本变更移入 `openspec/changes/archive/`，提交归档结果。因 4.2/4.3 未完成，暂不归档，变更保留在 `openspec/changes/`。
