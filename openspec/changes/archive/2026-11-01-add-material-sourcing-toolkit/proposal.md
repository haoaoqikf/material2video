## Why

外部素材的检索、评估与整理目前只有规则文本：候选视频只能整段播放，判断“建立—动作—结果”是否完整靠反复拖进度条；素材台账靠人工比对 `media-sources.json`、`scenes/` 与 `SOURCES.md`，容易漏掉“场景用了但没登记”“登记了但许可未知”“来源表没写”的问题。规则已经存在，缺的是把规则变成可执行、可复查的动作。

## What Changes

- 新增 `m2v assets report`：只读生成素材台账，交叉核对登记记录、场景 `useMediaAsset` 引用、文件摘要/许可/来源与 `SOURCES.md`；输出 `outputs/assets-report.json`，发现错误时以非零退出码结束。它不写准备指纹、不替代 `prepare` 与 `assets audit`。
- 新增 `m2v assets contact-sheet`：对候选视频按时刻或均匀采样抽帧，或把多张候选图片拼成一张带序号的接触表，并写同名 JSON 索引（第几格对应第几秒/哪个文件）。只读输入文件，不导入、不改素材。
- 在既有 `material2video` skill 内新增 `references/material-sourcing.md`：来源层级与检索词、候选评估卡、许可与署名决策、台账修复、替换复核与停止条件；在 `SKILL.md`、`visual-material-selection.md`、`article-media-and-sound.md` 与 `guidance-routes.json` 接线。不新建 skill。
- 不新增制作阶段、审核轮次或交付门禁；既有载体选择、导入留证、prepare 指纹与渲染离线契约不变。

## Capabilities

### New Capabilities

- `material-sourcing`：外部素材的检索、候选评估、许可判断与台账整理，以及承载它的 skill 参考页和两条 `m2v assets` 命令。

### Modified Capabilities

- `article-media-assets`：资产审计入口由单一 `audit` 扩展为 `audit`、`report`、`contact-sheet` 三个职责明确的入口，并声明后两者不替代 `audit`/`prepare` 的许可与一致性阻断。

## Impact

- 代码：`src/m2v/cli.py`、`src/m2v/commands.py`，新增 `src/m2v/engine/assets_tools.py`；复用 `media_assets` 的记录读取与媒体探测。
- 测试：新增台账纯单元用例与接触表 media 用例；既有 `assets audit` 与 CLI 接线用例保持通过。
- 文档：`.agents/skills/material2video/` 的 `SKILL.md`、两份既有参考页、`guidance-routes.json` 与新增参考页；`README.md` 同步命令与导航。
- 不改变 `project.json`、`storyboard.json`、准备指纹、渲染契约与素材入库边界；`outputs/` 产物仍不入库。
