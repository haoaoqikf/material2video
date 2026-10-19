# 验证与审查记录

本文件记录 `replace-buffer-with-american-science` 的实施与验证结果。任务全部完成、验证与提交通过后，按项目约定同步主规格并归档。

## 材料与设计（1.1–1.2）

- 十项史实、贡献边界与逐件许可见示例 [SOURCES.md](../../../examples/american-science-milestones/SOURCES.md)；9 件素材经统一导入为内容寻址输入，`recipe.json` + `fetch.py` 可重新获取，摘要不符即拒绝。
- 官方档案优先；国会图书馆 API 403、Commons 原尺寸 429 等失败及替代路径已记录。大模型未能取得可真实呈现内部运算且许可明确的历史动态素材，因此使用代码动画并标注「原理示意」。
- 设计稿、两个美术方向与参考板见 [DESIGN.md](../../../examples/american-science-milestones/DESIGN.md)；三张 4K 代表静帧、24 秒风险样片与全片 6 fps 粗预演已完成，证据与复核结论见示例 [VERIFICATION.md](../../../examples/american-science-milestones/VERIFICATION.md)。
- 设计复核发现电话章节波形与说明文字重叠并已修正；修正后重新生成粗预演和全部证据。

## 实现与回归（2.1–2.3）

- 120 秒 / 7200 帧、1920×1080、60 fps 的 v8 分镜共 12 幕，空旁白、无 soundtrack、三个 10 秒 hero（flight、moon、llm）；`m2v validate` 与 `m2v prepare` 通过，准备指纹 `56a2465b…`。
- `examples/buffer-smoothing` 已删除，固定示例改为 american-science-milestones、darts-trial-and-error、solar-system-journey；音效测试迁移到独立合成夹具，示例名单、文档、字体与示例测试同步。
- 二维档案以 `role: other` 登记：审计不再要求虚构 normal/roughness/emissive，仍要求 hero 许可已知，低于 2K 时提示按原生尺寸复核、不冒充 4K；三维颜色贴图规则不变。
- 无声 QA 在「空旁白 + 无 soundtrack」时要求最终 PCM 峰值为 0，替代响度目标；有声作品仍走原响度与真峰值检查。
- look-dev 多幕静帧合成缺陷已修复：只保留当前帧所在幕，避免未采样幕的空 `mediaPath` 进入合成层；补充回归用例。
- 代码审查修正：NASA 月面片段改为完整 10.0 秒（此前输出仅 7.5 秒导致镜头末段停在片尾）；多幕 cinematic 溯源逐幕汇总并换算全片帧号；素材记录读取时校验 `role`/`target`；显式空 `soundtrack` 仍按无声处理；二维素材与颜色贴图并存时仍单独审计许可与尺寸。
- 回归：完整 Python 测试 634 通过、4 跳过、0 失败；`pnpm -C web test` 58 通过；`tsc --noEmit`、`pnpm -C web build`、OpenSpec 严格校验与文档同步检查通过。

## 交付（3.1–3.2）

- 正式成片 `videos/examples/american-science-milestones/outputs/video.mp4`：7200 帧 / 120.0 秒 / 1920×1080 / 60 fps，H.264 High + AAC-LC 44.1 kHz 双声道；SHA-256 `ae4a15b337c744444629b76facc1eabb52149a008baff096a12973d729b1661c`。
- 溯源与交付记录绑定准备指纹 `56a2465b…`；多幕 cinematic 溯源包含 12 条镜头（sceneId + 全片帧号）与逐幕 look，交付键 `cc6fc1fc…`。
- `m2v qa --profile cinematic` 为 `status=pass`：0.5 秒基线并加密交界，1339 个样本、84 页接触表；冻结帧 0，静音 `peakAbsolute=0.0`，音画差 0.00073 秒；7 处 frame-change 为章节硬切，音频整段静音为设计预期。
- 全片帧序列与 QA 报告位于 `examples/american-science-milestones/outputs/qa/`；六维复核见 `videos/examples/american-science-milestones/outputs/visual-notes.md` 与示例 [VERIFICATION.md](../../../examples/american-science-milestones/VERIFICATION.md)。
- 审查与回归：代码审查 10 项发现全部处理；最终完整 Python 回归 634 项通过、4 项跳过、0 失败，前端测试与构建、OpenSpec 严格校验和文档同步检查均通过。
