## Why

现有制作复核能检查渲染、文字可读性与镜头节奏，却没有明确检查观众可见文案是否暴露仓库内部资料，也没有把反复套用静态信息卡片的幻灯片式观感定义为必改问题。`american-science-milestones` 的 120 秒横屏示例因此重复展示年份、标题、说明和素材署名，并在片尾指向 `SOURCES.md`。本变更同时修订通用流程并重制示例，建立可复用的检查标准。

## What Changes

- 明确作品默认面向手机观看；按作品声明的横竖画幅复核手机显示时的正文、主体和界面遮挡，不把手机观看等同于强制竖屏。
- 增加反幻灯片式视觉复核：检查画面结构、信息推进、运动和版式重复；重复静态卡片或机械逐页切换主导全片时属于必改项。
- 交付复核逐项盘点所有观众可见文字，禁止内部文件名、仓库路径、制作文档及查阅指引出现在成片中。
- 每部作品只保留一份片尾极简署名与版权说明；完整事实、来源、作者和许可证据留在作品材料中，并确保所用许可义务得到满足。
- 重制 `american-science-milestones`：1920×1080 横屏、约 60 秒、无旁白，保留十项里程碑和贡献边界，以更丰富的档案影像、细节、动作与镜头承接替代重复信息卡片。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `video-production-workflow`：增加手机观看默认目标、观众可见文案审查、片中内部引用禁令、单份极简署名及反幻灯片式视觉质量门槛。

## Impact

- 更新 `openspec/specs/video-production-workflow/spec.md` 对应流程契约及 `.agents/skills/material2video/references/` 中的创作与视觉复核指南。
- 同步 `openspec/specs/article-explainer/spec.md` 中固定示例的时长契约与 `tests/test_examples_strict.py`：无声美国科学里程碑从120秒改为60秒。
- 更新固定示例 `examples/american-science-milestones/` 的分镜、场景源码、设计、README 与验证记录；重新生成忽略的 `videos/examples/american-science-milestones/outputs/` 成片和检查证据。
- 不新增分镜字段、CLI 命令、依赖或渲染器 API；使用现有代码场景、准备、渲染、QA 和帧序列复核能力。
