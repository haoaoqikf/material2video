## 1. 命令实现

- [x] 1.1 `src/m2v/engine/assets_tools.py`：`build_report` 交叉核对登记、场景引用、摘要/许可/来源与 `SOURCES.md`。
- [x] 1.2 `src/m2v/engine/assets_tools.py`：`contact_sheet` 支持图片拼格与视频抽帧，输出 PNG 与同名 JSON 索引。
- [x] 1.3 `src/m2v/cli.py` 与 `src/m2v/commands.py` 接线 `assets report`、`assets contact-sheet`，`audit` 行为不变。

## 2. 文档

- [x] 2.1 新增 `.agents/skills/material2video/references/material-sourcing.md`：来源层级、候选评估卡、许可决策、台账修复、替换复核、停止条件。
- [x] 2.2 `SKILL.md`、`guidance-routes.json`、`visual-material-selection.md`、`article-media-and-sound.md` 接线新参考页。
- [x] 2.3 `README.md` 同步命令与导航；不把规划写成已实现。

## 3. 测试与验证

- [x] 3.1 纯单元层：台账错误/警告、动态引用、`SOURCES.md` 覆盖、CLI 参数与类型守卫。
- [x] 3.2 media 层：接触表图片与视频生成、索引对应、非法输入失败。
- [x] 3.3 验证记录：新增台账与 CLI 用例 20 项、接触表 media 用例 7 项通过，`sync_docs.py --check` 与 `openspec validate --strict` 通过；全量 `pytest` 套件按用户指示停止，未跑完。

## 4. 提交与归档

- [x] 4.1 检查暂存内容，提交实现与文档，不夹带生成媒体。
- [x] 4.2 同步主规格并归档变更。
