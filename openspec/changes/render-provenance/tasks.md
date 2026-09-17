# 任务：成片溯源与陈旧判定

## 1. 溯源伴随文件

- [x] 1.1 渲染成功后落一份伴随文件（与成片同目录、同主名，`voiced.mp4` → `voiced.provenance.json`），字段：页面、分镜、资产指纹表、帧数、分辨率、帧率、采集格式、渲染时刻。实测一次 12 帧渲染：伴随文件 1.8KB，逐个列出被引用资产（含 `vendor/spring.js`）与总 digest。
- [x] 1.2 指纹口径与 `media.json` 的 `sourceFingerprint` 一致（哈希算法与字段命名不另造）：`media.asset_fingerprint` 复用同一个 `media.fingerprint`，并有测试钉住「同一份 files 必须得到同一个 digest」。
- [x] 1.3 只指纹**网页真正引用的本地资源**（样式表与脚本，含 skill 共享资产），不把整个 `assets/` 目录算进去——否则改一个用不到的图形也会报落后。两侧都有测试：被引用资产改一个字节指纹必须变，未被引用文件改了指纹必须不变。
- [x] 1.4 有声导出把媒体清单的指纹一并记进溯源（同一个成片要能回答「素材是哪一版」）：实测带 `--media` 的 12 帧渲染，溯源里记下 `media.sourceFingerprint`（`bd19b676…`）。
- [x] 1.5 分镜路径要由渲染入口传给溯源：`render()` 新增 `storyboard_origin`，`cli.main_render` 传入 `args.storyboard`；分镜文件同时进指纹表。实测同一支渲染的溯源里 `storyboard` 记为 `examples/why-effort-fails/storyboard.json`。

## 2. 陈旧判定

- [x] 2.1 验收命令能回答「这个成片是不是旧资产渲的」；不一致时报出**是哪几个文件**变了。已接进体检流程：`report.json` 多出 `provenance` 键，终端摘要多出「成片溯源（只提示、不拦人）」一段。实测三条结论都在真实作品上报出来过——旧成片 `? 无法判断`、改过 `vendor/spring.js` 后 `! 落后……改了：…vendor/spring.js`、重渲后 `✓ 对得上`。
- [x] 2.2 溯源缺失时如实报「无法判断」，SHALL NOT 默认放行，也 SHALL NOT 当成失败：三种结论 `current`/`stale`/`unknown` 互斥且有测试；读不出来、网页已不在同样归 unknown。
- [x] 2.3 判定不改变画面类检查的错误数与退出码（它是提示，不是废片判定）：实测判为「落后」时体检仍是 0 错误 0 提醒、退出码 0。

## 3. 测试

- [x] 3.1 指纹口径的单元测试：同一组文件稳定、文件内容变一位就不同、路径顺序不影响结果（`tests/test_asset_fingerprint.py`，11 项）。
- [x] 3.2 反例：改掉一个被引用的资产之后，已有成片必须被判为落后，并指出是哪个文件：`tests/test_render_provenance.py::test_referenced_asset_change_is_reported_with_the_file`。另加了「新增引用」「被引用文件不见了」两侧。
- [x] 3.3 未引用资产的变化**不得**触发落后（否则闸门会变成噪音，人会开始忽略它）——指纹侧已钉住，判定侧待接。
- [x] 3.4 缺失溯源时的行为有测试（报「无法判断」而不是通过或失败）：`TestUnknownIsNotAPass` 四项。

## 4. 文档与验收

- [ ] 4.1 `references/render-contract.md` 补上溯源伴随文件的位置与字段。
- [ ] 4.2 `SKILL.md` 的渲染验收把「靠人比对时间戳」改成查溯源。
- [ ] 4.3 `docs/PROJECT_PLAN.md` 把这条从缺口移入已实现。
- [ ] 4.4 全量 `uv run pytest` 通过；重渲一次基准示例确认成片字节不变、只多出伴随文件。
