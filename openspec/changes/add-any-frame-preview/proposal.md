## Why

通用作品的画面问题几乎都是看着图改出来的，但现有预览工具只提供两类取点：代表静帧按 hero 镜头后段自动选点，检查点采集只认设计合同里声明过的时刻。改一版画面后想知道"第 8 秒到第 12 秒这个转场到底说清楚没有"，或者"这三个时刻并排看一下"，没有对应手段，只能等到一次完整生成或一轮独立评审。

另有一项一直缺命令行入口的能力：同一帧重复渲染是否一致。判据（PSNR ≥ 60 dB）已写进规格与测试，但没有面向作者的检查入口，记为技术问题时要靠临时脚本。

## What Changes

- `m2v lookdev` 增 `--sheet`：指定若干时刻（秒）拼一张接触表；给单个整数时按全片均匀取那么多帧。每格标注时刻与帧号。
- `m2v lookdev` 增 `--motion`：给起止时刻与可选帧数，区间内均匀取帧拼一张，用于看转场与动作连续性。
- `m2v lookdev` 增 `--det`：对同一批时刻做两次独立采集，逐帧比较 PSNR，输出不一致帧与时刻；阈值沿用既有的 60 dB。
- 三条新参数与既有 `--stills` 互斥；指定的时刻在启动浏览器前完成越界与归属校验。
- `--det` 与 `--sheet`/`--motion` 的产物落在既有 `outputs/lookdev/` 下，清单仍写 `outputs/lookdev.json`。
- 不新增顶层命令；不改变 `--stills`、`--sample-seconds`、`--still-scale` 的现有行为；不新增导出门禁或准备指纹输入。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `modular-video-production`: 「制作与质检入口」的 `lookdev` 条款扩展为支持任意时刻拼图、区间转场拼图与同帧一致性自检；原有静帧、样片与"不生成全片、不成为导出门禁"的约束不变。

## Impact

影响 `src/m2v/engine/lookdev.py`（新增三种取点模式与时间标注）、`src/m2v/cli.py` 与 `src/m2v/commands.py`（参数与分发）、`tests/test_cinematic_commands.py` 与 `tests/test_cinematic_lookdev.py`（接线与纯函数）、`README.md` 与制作参考文档（`cinematic-video.md`、`code-scene-runtime.md`、`production-workflow.md` 的指定时刻说明）。

采集复用既有 `native_stills()` 与 `contact_sheet()`，仍受"只从第 0 帧连续推进"的运行时约束：某一时刻的采集代价与它所在幕内的时间位置成正比，不承诺秒级返回。产物在成功交付后按既有清理规则处理，要作为证据保存的图须登记进 `outputs/visual-notes.md`。

不修改分镜 schema、准备指纹、成片编码、审核轮次或任何门禁。金融与住宅类型不适用本命令，行为不变。
