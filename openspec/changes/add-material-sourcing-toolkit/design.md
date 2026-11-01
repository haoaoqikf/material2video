## Context

素材规则已集中在 `visual-material-selection.md` 与 `article-media-and-sound.md`，但执行层只有 `assets audit`（需先 prepare）与 `general assets search/import`。制作时仍要手工拖进度条看候选片段、手工比对三份记录。本变更只补两条制作期只读命令与一页操作手册，不改变准备、渲染或审核契约。

## Decisions

### 命令面

`m2v assets` 由单一 `audit` 扩展为三个 workflow，共用 `--project`：

| 命令 | 是否要求 general | 作用 | 输出 |
|---|---|---|---|
| `audit` | 是 | 既有许可/尺寸审计，绑定准备指纹 | `outputs/asset-audit.json` |
| `report` | 是 | 台账交叉核对，不依赖 prepare | `outputs/assets-report.json` |
| `contact-sheet` | 否 | 候选抽帧/拼图，只读输入 | PNG + 同名 JSON |

`--project` 在解析层改为可选、由各 workflow 自行校验，保证 `contact-sheet` 可以脱离作品目录检查候选文件，同时 `audit`/`report` 仍给出明确缺失提示。`audit` 的参数与行为保持原样。

### 台账报告

- 单一数据源：`assets/media-sources.json`；不重新探测媒体（保持纯单元层可测、无 ffmpeg 依赖），只核对记录里的宽高是否有效。
- 引用识别：扫描 `scenes/**/*.tsx` 中 `useMediaAsset("id")`/`useMediaAsset('id')` 字面量；包装组件常写 `<Media id="x" />`，因此登记 ID 只要以引号字面量出现在场景源码里也算被引用。「未登记引用」只认显式 `useMediaAsset("x")`，避免把普通字符串误判成素材；出现非字面量调用且仍有未引用素材时给 `dynamic-usage` 警告。
- 错误：引用未登记、文件缺失、摘要不符、许可未知、路径越界；警告：登记未引用、作者/来源未知、重复文件、`SOURCES.md` 未出现该 ID。
- 退出码：有错误为 1，仅警告为 0；报告正文显式写“不替代 prepare 与 assets audit”。
- 不写准备指纹，不读 `prepared.json`，因此可在 prepare 前运行。

### 接触表

- 输入 1～24 个本地文件；视频最多一个，其余必须为图片。
- 视频取帧：显式 `--times`（逗号分隔秒）优先；否则按 `--samples`（默认 6）在全片均匀取点，避开末帧。
- 视频用 ffmpeg 在入点前 seek 抽单帧到临时目录；图片直接读取。两者统一用 Pillow 拼格，避免依赖系统字体。
- 格宽 `--tile-width`（默认 480），格高按所有输入的最大宽高比推算，纵向视频得到更高的格子，不裁切主体。
- 每格左上角画序号；同名 JSON 记录 `{index, input, timeSeconds, sourceWidth, sourceHeight}`，供回到原片定位。
- 默认输出：给了 `--project` 写 `outputs/qa/contact-sheet.png`（与既有检查图同目录，成功交付后可清理），否则写在第一个输入同目录；`--out` 覆盖。重复运行覆盖同名产物，不留半成品（先写临时文件再原子替换）。

### 文档位置

不新建 skill：新增 `references/material-sourcing.md`，定位为操作手册，权威仍归两份既有参考页。`SKILL.md` 只加一行条件参考，`guidance-routes.json` 增加 `sourcing` 条件路由，`visual-material-selection.md` 与 `article-media-and-sound.md` 在检索/导入段各加一次指向。入口预算 1570/2000，新增行后仍在预算内。

## Risks

- **台账误报**：`useMediaAsset` 若有拼接或变量调用，报告只能标记动态引用，不能断言未使用。以警告呈现，不阻断。
- **视频抽帧耗时**：长视频逐点 seek 仍可能慢；默认采样数小、显式时刻由助手按需给，避免全片扫描。
- **与 audit 职责重叠**：report 也检查许可，但只作为制作期提示；audit 与 prepare 仍是唯一阻断点，文档与规格都写明。
- **产物入库**：接触表与报告都写 `outputs/`，沿用既有忽略规则，不新增入库路径。

## Alternatives

- 把 report 合进 audit：audit 需要 prepared 指纹，prepare 前无法用；且会把“制作期台账”和“交付审计”混成一个门禁。
- 用 ffmpeg `tile` 直接拼图：`drawtext` 依赖系统字体，序号在无字体环境会整条失败；Pillow 已在依赖里，拼格与标号更可控。
- 新建独立 skill：用户明确要求留在既有 skill 内；操作手册与既有权威同目录也更不易漂移。
