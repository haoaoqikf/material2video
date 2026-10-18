## MODIFIED Requirements

### Requirement: 电影级制作与质检入口

系统 MUST 在统一入口新增电影级制作与质检命令：`m2v lookdev --project <目录>`、`m2v qa --project <目录>`、`m2v assets audit --project <目录>`。cinematic 的正式导出沿用现有 `m2v render`，不新增母版命令。命令 MUST 沿用现有作品路径、内容根、退出码与产物归属规则；standard 的现有命令与行为 MUST NOT 改变。

- `lookdev` MUST 只渲染关键静帧与代表片段，MUST NOT 生成完整成片；输出位于作品 `outputs/lookdev/`，包含 3–5 张从当前源码原生采集的 4K 静帧、接触表与 20–30 秒有声样片。观看结论写入作品 `outputs/visual-notes.md`，作为检查与返工依据，MUST NOT 成为导出门禁。
- `qa` MUST 输出 `outputs/qa.json` 与接触表，覆盖冻结/重复帧、banding、aliasing、字幕对比度、响度/真峰值、音轨时长差与 claims 时间窗覆盖，并明确区分技术判定、测量提示和需要实际观看的项目；MUST NOT 将技术通过表述为视觉质量通过；技术失败 MUST 以退出码 1 结束，报告 MUST 可定位到镜头/时间戳。
- `assets audit` MUST 只读素材与导入记录，输出 `outputs/asset-audit.json`；hero 资产不合格时 MUST 以退出码 1 结束。
- 正式导出 MUST 沿用 `m2v render`，交付普通 H.264 MP4；系统 MUST NOT 提供 `m2v master` 或 ProRes/DNxHR 母版入口。成片旁车 MUST 记录 profile、交付摘要、音频参数与 QA 指纹。
- standard 与 cinematic 的所有制作阶段均取消用户确认：`m2v render` MUST NOT 因缺少观看记录、确认文件或 look-dev 产物而阻断。standard MUST 同样无需人工确认。

所有新命令 MUST 遵守离线、素材留证、准备指纹与交付权限规则；缺少准备记录、profile 非法或依赖缺失时 MUST 在渲染前失败，不产出部分产物。

#### Scenario: look-dev 只出样片
- **WHEN** 对 cinematic 作品运行 `m2v lookdev`
- **THEN** 只生成关键静帧、接触表与 20–30 秒有声样片，不生成全片，不覆盖正式成片

#### Scenario: QA 失败定位
- **WHEN** 某镜头出现冻结帧或响度超限
- **THEN** `m2v qa` 以退出码 1 结束，报告指出镜头/时间戳与实测值

#### Scenario: look-dev 之后直接导出
- **WHEN** 跑完 `m2v lookdev` 且作品未记录任何确认或观看结论
- **THEN** `m2v render` 正常交付，不因缺少确认而阻断；`lookdev` 产物仍可供观看与返工定位

#### Scenario: 标准命令不变
- **WHEN** 使用现有 validate/prepare/preview/render 处理 standard 作品
- **THEN** 参数、默认输出、退出码与成片行为保持不变

#### Scenario: 原生 4K 关键帧
- **WHEN** 运行 lookdev 生成静帧，作品包含显式低 DPR 的 WebGL 画布或多个代码幕
- **THEN** 从当前源码连续推进至各幕选定帧，以 2 倍像素绘制画布，PNG 合成原有字幕与转场；不放大 1080p 缓存视频冒充原生细节，像素不足时明确失败；有声样片流程不变

#### Scenario: 测量项不能冒充通过
- **WHEN** QA 只计算了 banding 或 aliasing 相关数值
- **THEN** 报告标识为测量提示，不据此自动宣称画面无缺陷，也不将测量项当作技术失败

#### Scenario: 导出与完成分离
- **WHEN** render 成功但缺少当前有效的最终观看记录
- **THEN** CLI 仍可输出视频，助手报告尚未完成视觉复核，不要求用户确认，不宣称制作完成

### Requirement: 共用渲染及可靠输出
系统 MUST 使用完整缓存键且命中不跳门禁，元数据核验与渲染使用同一浏览器会话；临时成片通过帧数、尺寸、帧率、音轨验收及输入复核后才替换目标。所有类型 MUST 输出溯源与性能记录。正式成片成功替换并生成旁车后，统一入口 MUST 清理当前作品 `outputs/` 中旧成片及其旁车、预演与已知检查和调试产物；MUST 保留本次成片、其字幕/溯源/性能旁车、准备和评审 JSON、可供重渲使用的准备媒体。清理不得越出当前作品 `outputs/`，不得清理共享构建缓存。general 当前 visual-notes、其引用的当前检查证据及返工前后对照 MUST 保留在作品忽略的输出目录中，作为已知检查产物清理的例外；历史无引用大体积检查产物仍按原规则清理。渲染或验收失败 MUST NOT 触发清理；清理遇到文件错误时 MUST 保留有效新成片、报告失败和遗留路径，且不得声称全部清理完成。

#### Scenario: 元数据不符或输出失败
- **WHEN** composition 元数据不符或渲染期间材料变化
- **THEN** 阻断或丢弃临时产物，不覆盖原有效成片

#### Scenario: 正式渲染成功后清理旧产物
- **WHEN** 任一视频类型的正式渲染通过验收并写好成片旁车
- **THEN** 只保留本次成片和必要旁车、准备及评审记录、准备媒体；清理当前作品输出目录内旧视频、预演与已知检查/调试产物

#### Scenario: 渲染失败不清理
- **WHEN** 正式渲染或成片验收失败
- **THEN** 不执行旧产物清理，已有有效成片及其他产物保持不变

#### Scenario: 清理遇到文件错误
- **WHEN** 新成片已验收，但一个或多个旧产物无法删除
- **THEN** 保留新成片并报告清理失败及未删除路径，不影响新成片交付状态

#### Scenario: 保留当前视觉复核证据
- **WHEN** general 渲染成功后清理旧产物
- **THEN** 当前观看记录及其引用的检查依据和前后对照仍可访问，内容与媒体不加入 Git
