# 验证记录

制作与复核：2026-10-19 至 2026-10-20。当前结论绑定准备指纹 `56a2465beed096a4aec60676b4309cb072f79a4a9fd0f11661c4cec370637dba`；旧准备指纹、被替换的缓冲示例与旧粗预演不构成本版证据。

## 事实、素材与许可

- 十项史实的核验页、年代、贡献边界见 [SOURCES.md](SOURCES.md)。文字明确计算机、互联网与人工智能是长期国际合作与累积成果，不将整体归为一国独创。
- 9 件二维档案与实物素材经统一 `assets import` 内容寻址导入，逐件登记来源页、作者、许可、实测尺寸与 SHA-256；[assets/recipe.json](assets/recipe.json) 与 [assets/fetch.py](assets/fetch.py) 可在缺失时重新获取，摘要变化即拒绝替换，不静默换源。
- 国会图书馆 API 部分 403、Commons 原尺寸部分 429 的失败与替代路径已记录：官方事实页与公共领域原片交叉核验，晶体管使用许可明确的 1280 像素版本，NASA 片段截取原片 84.25–91.75 秒、去声并以 0.75 倍慢放至 10.0 秒。
- `m2v assets audit` 为 `status=pass`、0 个阻断项、8 条预期警告：6 件低于 2K 的二维档案按原生尺寸使用，不冒充 4K；结尾与大模型示意 2 个程序化目标没有三维颜色贴图，不适用贴图清单。开场复用 flight 档案，已关联到该镜头目标。

## 设计与代表画面

- [DESIGN.md](DESIGN.md) 记录画幅、两个美术方向、参考板、配色与构图、无声声音意图；采用档案纪录片方向，照片保留原生光比，代码图形用暖白与冷青。
- 三张代表画面均为 hero 镜头 75% 处的原生 3840×2160 静帧，未放大 1080p 画面：
  - `outputs/lookdev/still-002010.png`，第 2010 帧 / 33.5 秒，莱特兄弟首飞；SHA-256 `195bd639ef745f3bbd4c7bb255ab319c4e5609f10546398d95e41b2279016823`。
  - `outputs/lookdev/still-004410.png`，第 4410 帧 / 73.5 秒，阿波罗 11 号月面档案；SHA-256 `70a26f806b75a08cae2c9aac30e1ff8a871066f8e63c853d5e90f1b27a1df177`。
  - `outputs/lookdev/still-006210.png`，第 6210 帧 / 103.5 秒，大模型节点网络原理示意；SHA-256 `ee654c05ac4f1dd3e14f8d92dc3a2882c2693e57ef0095dbad041fe410b01006`。
- 联系表 `outputs/lookdev/contact-sheet.png`，SHA-256 `a9a39c61581adad6b7a5e0e57572bbef926fa4af7e52b099c9be02454382c726`。
- 复核结论：三张静帧中年份、标题、说明与署名均清晰；全幅与留边构图的文字都未越界；登月、电话、ARPANET 等低清档案保留原生画框与质感，不宣称为 4K；大模型画面明确标注「原理示意 · 非模型真实内部结构或运行记录」。
- 复核修正：首轮粗预演发现电话章节的 ECharts 波形上缘与说明文字重叠，已将图表顶部由 680 像素下移到 700 像素并压缩为 90 像素高；最终粗预演与正式成片均使用修正后版本。

## 粗预演与风险样片

- 全片动态粗预演 `outputs/rough/rough.mp4`：120.0 秒、960×540、60 fps；按当前场景源码以 6 fps 采样后补帧，SHA-256 `f8d6382e817472454e3da5ef730ad4c55e58c02586b6f8002a3ba2a24f6c91f3`。记录见 `outputs/rough/receipt.json`，绑定同一准备指纹与分镜摘要。
- 风险样片 `outputs/lookdev/sample.mp4`：第 1560–2999 帧（26.0–50.0 秒），覆盖飞行、三位一体与 ENIAC 区间，24.0 秒；SHA-256 `5b59d4052f40de5036974947a5d7a555243017719e05b886cf3eeaaa7589e4e5`。
- 粗预演复核：逐幕顺序、硬切年代、三个 hero 各 10 秒的连续停留、结尾十项回顾与署名切换均可见；电话波形不再压住说明文字。未发现必须返工的构图、可读性或节奏问题；样片与粗预演都不要求播放或连续收听。

## 回归与流程

- 完整 Python 回归 634 项通过、4 项跳过、0 失败；`pnpm -C web test` 58 项通过；`pnpm -C web build` 与 `tsc --noEmit` 通过（仅保留既有 chunk 体积提示）。
- 2D 档案审计、静音 QA 与多幕 look-dev 静帧合成的回归用例通过；后者修复了未采样幕以空 `mediaPath` 进入合成层的缺陷。
- `m2v validate` 通过；`openspec validate replace-buffer-with-american-science --strict` 通过；`sync_docs.py --check` 无漂移。
- 替换缓冲示例后音效测试改用独立合成夹具，不再依赖任何固定作品素材。
- 代码审查修正：NASA 月面片段此前导出仅 7.5 秒，10 秒镜头末段会停在片尾；现按 84.25–91.75 秒源段以 0.75 倍慢放为完整 10.0 秒。另修正多幕 cinematic 溯源只记录第一幕、素材记录读取时未校验 `role`/`target`、显式空 `soundtrack` 被误判为有声，以及二维素材与颜色贴图并存时审计遗漏。

## 正式成片与自动检查

- 正式成片 `videos/examples/american-science-milestones/outputs/video.mp4`：7200 帧 / 120.0 秒 / 1920×1080 / 60 fps，H.264 High、yuv420p(tv, bt709)，AAC-LC 44.1 kHz 双声道；46,357,120 字节，SHA-256 `ae4a15b337c744444629b76facc1eabb52149a008baff096a12973d729b1661c`。
- 旁车 `video.provenance.json` 绑定准备指纹 `56a2465b…`，逐幕记录 12 条镜头（含 sceneId 与全片帧号）和 `幕ID → look`；`delivery.json` 的交付键为 `cc6fc1fc…`，与视频和溯源一致。
- `m2v qa --profile cinematic` 为 `status=pass`：基线抽样步长 30 帧（0.5 秒），在镜头交界处加密，覆盖帧 0–7199，共 1339 个样本、84 页接触表。
- 冻结帧通过：最低相邻帧差 0.00063，重复帧与近乎静止比例均为 0，最长静止 0.0 秒；7 处 frame-change 候选位于章节硬切处，属设计预期。
- 静音检查通过：`peakAbsolute=0.0`，音频 120.00073 秒、与画面差 0.00073 秒；自动音频候选为整段静音，符合无声设计。字幕对比度、claims 与音画同步检查均通过。
- 全片帧序列位于 `examples/american-science-milestones/outputs/qa/sequence-r1c8ddox/`；六维复核记录见 `videos/examples/american-science-milestones/outputs/visual-notes.md`。
- 最终回归：完整 Python 测试 634 项通过、4 项跳过、0 失败；`pnpm -C web test` 58 项通过；`tsc --noEmit` 与 `pnpm -C web build` 通过。

## 限制

- 历史档案原生清晰度有限；成片不声称素材原生 4K，也不把代码原理图表述为实拍或精确历算。
- 自动 QA 是抽样与技术信号结论，不等同于逐帧观看；采样之间的瞬时运动缺陷可能遗漏。
