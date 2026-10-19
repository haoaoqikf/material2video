# 验证记录

制作与复核：2026-10-20。当前结论绑定准备指纹 `4501df3a3777f77463a5905fd69acb003f10a07f51ddad437bcb8d03ad6bbf97`；旧 120 秒版本、旧准备指纹与旧粗预演不构成本版证据。

## 事实、素材与许可

- 十项史实的核验页、年代、贡献边界见 [SOURCES.md](SOURCES.md)。文字明确计算机、互联网与人工智能是长期国际合作与累积成果，不将整体归为一国独创。
- 9 件二维档案与实物素材经统一 `assets import` 内容寻址导入，逐件登记来源页、作者、许可、实测尺寸与 SHA-256；[assets/recipe.json](assets/recipe.json) 与 [assets/fetch.py](assets/fetch.py) 可在缺失时重新获取，摘要变化即拒绝替换，不静默换源。
- 国会图书馆 API 部分 403、Commons 原尺寸部分 429 的失败与替代路径已记录：官方事实页与公共领域原片交叉核验，晶体管使用许可明确的 1280 像素版本，NASA 片段截取原片 84.25–91.75 秒、去声并以 0.75 倍慢放至 10.0 秒，成片使用前 8 秒。
- `m2v assets audit` 为 `status=pass`、0 个阻断项、8 条预期警告：6 件低于 2K 的二维档案按原生尺寸使用，closing 与大模型示意 2 个程序化目标没有三维颜色贴图，不适用贴图清单。
- 片中只在片尾出现一份署名与版权说明，逐幕不重复素材署名；完整来源、作者、许可、SHA-256 与改编记录保存在作品材料中，片尾不引用文件名或路径。

## 设计与代表画面

- [DESIGN.md](DESIGN.md) 记录画幅、手机观看检查尺寸、两个美术方向、参考板、配色与构图、无声声音意图；采用档案纪录片方向，照片保留原生光比，代码图形用暖白与冷青。
- 成片逐幕代表帧见 `outputs/qa/review/contact-sheet.png`（SHA-256 `bfe60d417c159fb9d9cef19b0d84c8a50f87c4155c5fc021237029b0cc989ebf`），覆盖 12 幕；手机尺寸复核见 `outputs/qa/review/phone-contact-sheet.png`（SHA-256 `9755a57eb459b28bf8d80e85e1471c22bd5778e2f04df68ab785537e23a16f87`）。
- 复核结论：主说明 32–38px 在 699×393 手机画面上约合 11.6–13.8px；次级说明约 9.5–11.3px；示意标注 24px 约合 8.7px；片尾署名 32px 约合 11.6px。标题、主说明、贡献边界和片尾署名可辨；低清档案保留原生画框与质感，不宣称为 4K；大模型、双螺旋、四节点与晶体管截面均明确标注示意。

## 反幻灯片与观众可见文案

- 十项按素材特征分别采用竖幅实物、压暗背景加波形、全幅横移、竖幅推进、全幅反向横移、实物加截面、NASA 连续影像、档案地图加独立四节点示意、全幅加双螺旋、抽象网络等不同处理；没有连续多段只替换年份/标题/说明而沿用同构静态卡片。
- 观众可见文案覆盖片头、逐幕固定文字、动态示意标注与片尾；静态源码扫描与全片 47 页时间标注序列一致，未出现 `.md` 文件名、仓库路径、`SOURCES`、`examples/`、`outputs/`、制作文档名或“详见内部资料”一类指引。
- 作者、素材署名与许可只在片尾出现一次：`影像：John T. Daniels · Jack W. Aeby · 美国陆军 · NASA · NHGRI · 佚名`、`晶体管照片：Unitronic，CC BY-SA 3.0（裁切与调色）`、`ARPANET 地图：UCLA 与 BBN，CC BY-SA 4.0（调色）`、`其余档案为公有领域。本片改编部分按 CC BY-SA 4.0 提供。`
- 未取得适用平台的官方界面遮挡尺寸，只验证画面可读性，不宣称通过平台安全区实测；横屏画幅未裁成竖屏。

## 粗预演与正式候选

- 全片动态粗预演 `outputs/rough/rough.mp4`：60.0 秒、960×540、6 fps 采样后补帧到 60 fps；SHA-256 `47c4bb90b3f0eae8637540dc540b3cd6f80b65c13a85a8b57c1762aa71f9c6ce`。回执 `outputs/rough/receipt.json` 绑定准备指纹 `4501df3a…`、分镜 SHA-256 `c8d80f20143ca1275a1a29c00c3634b59a155035f44c42e1e175cd35bb1bab01`、采样 6 fps 与 60.0 秒总长。
- 粗预演逐幕检查了顺序、硬切年代、三个 8 秒 hero、结尾主旨与署名；发现并关闭的问题：LLM 无素材分支曾被 `!asset` 提前返回，导致场景不就绪；已改为先分派 llm 再检查素材。示意标注在手机尺寸下偏小，已统一放大；月面幕的 `NASA ARCHIVE` 情境标注与片尾署名重复，已改为 `LUNAR SURFACE`；ARPANET 示意从档案图上移出，改为独立四节点面板，避免与图内旧标签混淆。
- 正式候选由 `m2v render` 生成一次并直接交付同一文件；渲染记录 `video.performance.json`：3600 帧、render 758.188 秒、总耗时 1578.719 秒、concurrency 1。

## 正式成片与自动检查

- 正式成片 `videos/examples/american-science-milestones/outputs/video.mp4`：3600 帧 / 60.0 秒 / 1920×1080 / 60 fps，H.264 High、yuv420p(tv, bt709)，AAC-LC 44.1 kHz 双声道；19,518,470 字节，SHA-256 `118b8091f6e944e7a9229c16a42ca00beaadc60b0b5dfe2605ed033f6713c9fe`。
- 旁车 `video.provenance.json` 绑定准备指纹 `4501df3a…`，逐幕记录 12 条镜头（含 sceneId 与全片帧号）和 `幕ID → look`；`delivery.json` 的交付键为 `2ab42624369f46f84dc434f01e249018cd1d22840d3700b03de773e13262f0ba`，与视频和溯源一致。
- `m2v qa --profile cinematic` 为 `status=pass`：基线抽样步长 30 帧（0.5 秒），覆盖帧 0–3599，共 739 个样本、47 页接触表。
- 冻结帧通过：sampledPairs 119，最低相邻帧差 0.0001526，重复帧与近乎静止比例均为 0，最长静止 0.0 秒；10 处 frame-change 候选位于 2.9、6.9、10.9、18.9、22.9、26.9、30.9、38.9、42.9、46.9 秒，对应章节硬切，属设计预期。
- 静音检查通过：`peakAbsolute=0.0`，音频 60.00036 秒、与画面差 0.00036 秒；自动音频候选为整段静音，符合无声设计。字幕对比度、claims 与音画同步检查均通过。
- 全片帧序列位于 `examples/american-science-milestones/outputs/qa/sequence-2ag_55tv/`；六维复核记录见 `videos/examples/american-science-milestones/outputs/visual-notes.md`。

## 回归与流程

- 完整 Python 回归 634 项通过、4 项跳过、0 失败（pytest 退出码 0；末尾 Windows 临时目录清理权限提示不影响测试结果）。
- `pnpm -C web test` 58 项通过；`pnpm -C web build` 通过（含 `tsc --noEmit`，仅保留既有 chunk 体积提示）。
- `m2v validate`、`m2v prepare`、`m2v assets audit` 与 `m2v qa --profile cinematic` 通过；`openspec validate forbid-internal-references-in-video-copy --strict` 通过；`sync_docs.py --check` 无漂移。
- 示例严格测试同步为 60 秒、12 幕、三个 8 秒 hero；README、DESIGN、SOURCES 与创作参考中的时长和署名规则同步更新。

## 限制

- 历史档案原生清晰度有限；成片不声称素材原生 4K，也不把代码原理图表述为实拍或精确历算。
- 自动 QA 是抽样与技术信号结论，不等同于逐帧观看；采样之间的瞬时运动缺陷可能遗漏。
- 未取得平台官方界面遮挡数据；手机尺寸检查为按 852×393 屏幕、699×393 画面等比缩放后的可读性验证。
