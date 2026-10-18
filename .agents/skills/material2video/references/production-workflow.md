# 通用作品制作流程

通用作品使用 project.json 和 v8 storyboard.json。顺序是：确定发布语境、画幅与视觉设计（默认抖音横屏；作品 `DESIGN.md`）
→ 写 `scenes/` 下的本地 React 场景 → 保存源文并完成[输入审查](input-review.md)（`input.kind` 为
`topic` 时跳过）→ 编排旁白 → 按需导入素材 → 由制作助手按[自动选音流程](../SKILL.md)选择并保存
音色 → 准备与录制 → 查看风险片段帧序列与自动音频候选 → 完整预演 → 正式导出 → 全片帧序列与自动音频复核 → 自主交付。用户明确指定音色时沿用其选择。

```powershell
uv run m2v general assets search --project videos/general/<slug> --kind both
uv run m2v general assets import --project videos/general/<slug> --manifest <清单.json>
uv run m2v validate --project videos/general/<slug>
uv run m2v prepare --project videos/general/<slug>
uv run m2v preview --project videos/general/<slug>
uv run m2v render --project videos/general/<slug>
uv run m2v status --project videos/general/<slug>
```

prepare 复核 `assets/media-sources.json` 里**全部**登记素材（摘要、真实类型、实测尺寸与视频时长），
把「素材 ID → 本地地址与实测信息」注入作品代码，按实际 TTS 分段编译时间轴并缓存音频，在无头
浏览器里把每一幕按画幅逐帧录成无声片段并按摘要缓存，最后按 `soundtrack` 合成一条母版轨并裁到
全片时长。无旁白镜头按声明帧数或目标剩余时长分配。

preview 只做**字幕量测**（安全区矩形、换行范围与可见性）并生成有声完整视频；限帧预览不能用于
正式导出。`m2v general keyframes --storyboard <路径>` 输出各幕结果帧用于静态检查。

作品正文在栅格片段里，自动检查**不**声称能识别其中的全部正文或主体遮挡。因此做完之后要真的看：
关键帧 + 代表片段的加密帧序列与自动音频报告，把时间位置、修改与复查写进作品
`outputs/visual-notes.md`。无法观看时如实说明，不能虚构通过。这些记录不是导出门禁。

可选的 review.json 绑定当前准备指纹和完整预演摘要，主动评审时填写五项通过依据：信息清晰、
视觉设计、图文关系、旁白同步、阅读节奏。源文、素材、导入记录、分镜、场景源码与资源、画幅、
字幕几何、输入审查、音轨、渲染代码或字体变化，均要求重新准备与完整预演；人工画面评审不阻断导出。

正式渲染先生成临时文件、核验画布尺寸、帧数与声音，再替换 outputs/video.mp4 并保存溯源。
失败不覆盖旧成片。旧准备与旧评审不兼容；v7 及更早分镜须重新编排。

CLI 自动门禁仍为材料审查 → 选音 → 准备 → 完整预演 → 导出；可选评审记录不阻断导出。助手制作另外遵循[自主视觉复核](visual-review-rubric.md)：自主搜集参考、验证风险样片、必改项关闭后铺全片、最终文件全片帧序列与自动音频复核。导出成功不能代替制作完成。

## cinematic 分支

作品在 `project.json` 声明 `productionProfile: "cinematic"`（或 `prepare --profile cinematic`）后，
流程改为五个阶段，所有阶段均无需用户确认；产出静帧与样片、实际复核并关闭必改项后继续：

```powershell
uv run m2v validate --project videos/general/<slug>
uv run m2v prepare --project videos/general/<slug>
uv run m2v lookdev --project videos/general/<slug>   # 3–5 张 4K 静帧 + 接触表 + 20–30 秒有声样片
# 实际观看静帧与样片，记录版本、时间码、问题与复查；关闭必改项后铺全片，不新增 CLI 导出门禁
uv run m2v preview --project videos/general/<slug>
uv run m2v qa --project videos/general/<slug>        # 技术 QA，输出 outputs/qa.json
uv run m2v assets audit --project videos/general/<slug>
uv run m2v render --project videos/general/<slug>     # 普通 H.264 MP4 交付
```

- 阶段为 **Brief → Look-dev → Hero → Full film → QA/自主复核**；look-dev 只产出检查产物，
  不设人工门禁，`m2v render` 不因缺少观看或确认记录而阻断。
- shot list、look、`claims`、`leadInFrames` / `tailFrames` / `readingHoldFrames` 都是分镜的可选
  字段，进入准备指纹与代码片段缓存键；只改 look 或镜头也必须重新 prepare。
- 不执行数字评分卡。技术 QA 与 hero 实看后全片帧序列与自动音频复核最终文件，关闭必改项再自主交付；模板与版本失效规则见[自主视觉复核](visual-review-rubric.md)。
- 有声样片缺音轨时修复；使用全片帧序列与自动音频检测，明确覆盖限制，不要求连续播放或实际试听。

太阳系示例保留历史制作说明，历史确认不授权新版本完成；当前复核状态见示例 VERIFICATION.md。
