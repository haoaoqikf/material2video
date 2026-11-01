## 1. 规格收口

- [x] 1.1 主规格移除「视觉创意七段式」要求，五块式要求吸收仍有效的约束并加入运动计划的镜头级记录与 `linear` 例外。
- [x] 1.2 主规格「通用作品必须分层决定载体来源」把"七段式定稿"改为五块式设计记录，不改其判据与硬边界。
- [x] 1.3 验收规格新增「动态证据必须覆盖关键运动节拍」，明确复用事件与 `minEventFrames`、不新增字段与风险 kind。

## 2. 策略与生成文本

- [x] 2.1 `policy.py` 的 `structure-timing` evidence 补关键运动窗口的加密帧或过程片段，门位与人数不变。
- [x] 2.2 运行 `sync_docs.py` 重新生成 `checkpoint-gates.md` 的风险表，确认生成区一致。

## 3. 设计记录与逐场表

- [x] 3.1 `visual-creative-direction.md` 五块模板扩写运动计划：人格、签名动作、层、时长与缓动起点，及按 scene/shot 的运动表（起止帧、命名曲线、`linear` 用途）。
- [x] 3.2 `visual-creative-direction.md` 逐场设计表增加运动行为列，并写明与运动计划的对应关系。
- [x] 3.3 `visual-review-rubric.md` 视觉创意复核条目由"七段是否齐全"改为按五块核对可观察兑现，保留形式标签不否决。

## 4. 阶段与证据口径

- [x] 4.1 `stage-plan.md` 写清运动计划要落到镜头，并把"有明确时长与落点"改为可核对的判据。
- [x] 4.2 `stage-iterate.md` 补运动节拍登记为事件与按最短运动取采样，说明 `look.motion` 子帧不是运动证据。
- [x] 4.3 `stage-final.md` 终检门槛表补运动节拍证据与 `linear` 例外的核对点。
- [x] 4.4 `production-workflow.md` 的五块式段落与精修顺序改为链接加项目特有判断，不复述 skill 理论。

## 5. 类型专用指南

- [x] 5.1 `driving-route-video.md` 与 `vehicle-showcase-video.md` 增加指向两个 skill 的链接，点明镜头与匀速跟踪的适用范围。
- [x] 5.2 `financial-timeseries-video.md`、`building-construction-video.md`、`road-trip-video.md` 同步加链接，点明各自适用的视觉与运动章节。

## 6. 示例

- [x] 6.1 `styles/deep-journey/examples/solar-system-journey/DESIGN.md` 增补五块式设计记录（标记非重制回看），含可执行的运动计划与一镜到底 `linear` 例外。
- [x] 6.2 确认示例的相对链接可达、历史七段记录保留、风格包指纹不变。

## 7. 测试

- [x] 7.1 新增测试：五份类型专用指南都链接两个项目级 skill。
- [x] 7.2 新增或更新测试：项目指导不再引用已删除的七段式模板与十项自检（示例历史段落除外），且不复述上游缓动配方。
- [x] 7.3 运行 `uv run pytest`：默认套件 800 余项通过，5 项按环境跳过。

## 8. 验证与归档

- [x] 8.1 运行 `python .agents/skills/material2video/scripts/sync_docs.py --check` 与 `openspec validate --all`（52 项通过）。
- [x] 8.2 检查暂存内容，只提交本变更相关文件与配套文档。
- [x] 8.3 同步主规格并归档到 `openspec/changes/archive/`。
