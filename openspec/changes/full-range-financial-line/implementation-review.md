# 实施审查与验收记录

本文件记录 `full-range-financial-line` 完成后补齐的类型检查、测试、完整静音预演、可读性评审、性能量测与代码审查结果（对应任务 2.2）。
数据来自本机单次顺序执行，命令与产物均可在作品目录 `videos/full-range-qa-20261009/`（已忽略）复核。

## 验收结论

| 项目 | 命令 | 结果 |
| --- | --- | --- |
| 前端类型检查 | `pnpm -C web typecheck` | 通过，无输出（`tsc --noEmit`） |
| 前端测试 | `pnpm -C web test` | 23 个文件、160 个测试全部通过 |
| Python 测试 | `uv run pytest -q` | 58 个文件、811 项全部通过，0 失败（详见下节） |
| 材料校验 | `financial_video.py validate` | 通过，5479 个交易日、60 秒 |
| 完整静音预演 | `financial_video.py preview --project-dir videos/full-range-qa-20261009` | 1800 帧、1920×1080、30 fps、无音轨、退出码 0 |
| 正式导出 | `financial_video.py render --out outputs/financial-line.mp4` | 1800 帧、60.00 秒、1920×1080、30 fps、无音轨、退出码 0 |
| 评审门禁 | `financial.validate_legibility_review` | 通过（摘要与预演逐字节绑定） |
| 门禁反向验证 | 移走 `legibility-review.json` 后运行 `render` | 退出码 2 并提示需要完整视频评审；未生成成片 |

正式导出成片属性：`h264 (High)`、`1920x1080`、`30 fps`、时长 `00:01:00.00`、321 kb/s、2 437 463 字节；`-map 0:a` 报 `matches no streams`，确认无音轨。终帧为 201.13 USD / 最近有效收盘 2020-12-31。

## 测试与中途发现的缺陷

任务开始时构建树自身的完整 pytest 有 7 项失败，已在干净 HEAD 的临时 worktree 中复现同样的 7 项，确认全部是**本次变更之前就存在的漂移**，不是金融改动引入：

- `tests/test_doc_examples.py` 2 项：`article-to-storyboard.md` 在早先改版中把「输入审查 → 核心观点与隐喻设计 → …」整句加了粗体标记、并删掉了断言要求的「同一个视觉世界」「阶段代表推理进展」措辞。
- `tests/test_paths.py` 3 项、`tests/test_content_root_e2e.py` 2 项：正式渲染门禁后来新增了「全片节奏至少 4/5」的硬门槛（[rhythm_review.py](../../../.agents/skills/article2video/scripts/a2v/rhythm_review.py) 解析 `review.md` 的「节奏」行），但这两处夹具只写了「是否值得发布：通过」，因而被判为「缺少全片节奏单项评分」。

已在本次任务内一并修正（恢复文档措辞、给夹具补上带时间码证据的节奏评分行），修正后 `uv run pytest -q` 全部通过。

代码审查另发现并修复两处**真实缺陷**，两处都补了回归测试：

1. **旁路预演会顶掉已登记的完整预演**（`a2v/financial_render.py`）。`preview --out <其它文件>` 原先无条件改写 `outputs/previews/preview-record.json`，把它指向旁路文件；已填写的 `legibility-review.json` 里的 `previewSha256` 随即失效，而用户看到的却是「预演记录已更新」。本次即由该缺陷触发：一次 `--out` 复核渲染改写了记录，随之评审被判过期。现在只有作品默认路径的完整预演才登记记录，`--out` 是纯旁路输出。回归测试：`test_preview_with_explicit_out_does_not_replace_the_recorded_preview`。
2. **金融评审摘要会吸收文章级代码场景**（`a2v/financial.py`、`a2v/remotion.py`）。`legibility_review_digest` 调 `remotion.build_inputs()` 时不传分镜，于是退回读取共享的 `web/.gen/scene-manifest.json`；该清单是「最后写入者获胜」的全局派生文件，残留上一篇文章（含仓库外内容根）的代码场景模块，导致 (a) 摘要随无关文章变化而失效，(b) 模块位于 `web/` 之外时直接抛 `ValueError: … is not in the subpath of …`。金融画面是共享受信代码、从不加载作品模块，因此给 `build_inputs` 增加显式 `scene_modules` 参数并由金融侧传空集。回归测试：既有 `test_short_or_asset_stale_preview_cannot_supply_review`（其桩函数同步更新）。

该修复改变了摘要的构成，因此本次重新生成了完整预演与可读性评审；`materialsAndAssetsSha256` 现为 `291f7c6d…`，`previewSha256` 为 `9b21ea83…`。

## 性能与资源

- 完整静音预演：1800 帧 1920×1080，画面产出约 231 秒（约 7.8 帧/秒，含打包与同步字体）。
- 正式导出：同帧数约 175 秒（约 10.3 帧/秒）。两次为不同执行、共享缓存状态不同，不构成严格对比。
- 视图计算：`financial time-series composition > handles thirty years of daily data within the view-computation budget` 实测 11000 点 / 1800 帧 = 114.5 ms，预算 3000 ms，余量约 26 倍；该用例把每帧 `financialView` 的开销作为合成瓶颈的代理指标。
- 终幕稳定性：终幕 120 帧相对首个终幕帧的画面 PSNR 最低 58.089545 dB、平均 62.685011 dB（判据 50 dB）。
- 未测：ffmpeg 子进程峰值内存与 Remotion 打包阶段的峰值内存本次均未量测，不宣称全链路峰值。

## 代码审查：已确认无问题的部分

- 因果性：`financialView` 只读取 `currentDate` 之前的点，6 帧加权范围也只取已到达前缀；用例对每帧把未来点改成 999999 后结果逐字段相同。
- 寻帧一致：终幕冻结在 `endingStart - 1`，`ending` 段与末推进帧坐标一致；用例覆盖 1800 帧正序与倒序。
- 极值与留白：前缀极值数组一次构建、`WeakMap` 缓存，单点/恒定价格走绝对 1%（至少 0.01）半跨度，值刻度小数位随步长自适应。
- 材料与迁移：v3 价格 + v5 计划的组合校验、旧计划拒绝、迁移前全量备份与写入失败回滚均有既有用例覆盖。
- 画面契约：`svg` 上的 `data-a2v-*` 探针与 `data-a2v-visible-price-points` 由用例断言，固定年份刻度、首点 x 坐标在首末帧一致。

## 剩余风险与已知局限

- `financialView` 返回的 `windowPosition`、`windowEndPosition`、`windowStart`、`windowEnd` 与 DOM 上的 `data-a2v-window-start/end` 仍是滚动窗口时代的命名，现在语义是「固定全日期范围」。本次不改名以免扰动已归档的探针契约，属可读性债而非行为缺陷。
- 每帧 `points.slice(0, end)` 产生一次数组分配；实测余量充足，未做优化。
- 终幕坐标冻结依赖「ending 段存在」这一不变量，`financialView` 用 `!` 断言；计划校验器已保证三段结构，但直接以非法计划调用组件会抛错而非降级。
- 多年跨度下早期曲线横向宽度小，年份刻度有意稀疏（`span > 730` 时按约 7 个刻度取整年步长）；本次 20 年样例可读，跨度更大的标的仍需人工过一遍完整预演。
- 仓库 `examples/` 仍固定三例，本次未新增、删除或替换。
