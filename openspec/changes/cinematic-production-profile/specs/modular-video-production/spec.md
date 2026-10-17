## ADDED Requirements

### Requirement: 电影级制作与质检入口

系统 MUST 在统一入口新增电影级制作与质检命令：`m2v lookdev --project <目录>`、`m2v qa --project <目录>`、`m2v assets audit --project <目录>`、`m2v master --project <目录>`，以及 `m2v render --profile standard|cinematic`。命令 MUST 沿用现有作品路径、内容根、退出码与产物归属规则；standard 的现有命令与行为 MUST NOT 改变。

- `lookdev` MUST 只渲染关键静帧与代表片段，MUST NOT 生成完整成片；输出位于作品 `outputs/lookdev/`，包含 3–5 张从当前源码原生采集的 4K 静帧、接触表与 20–30 秒有声样片。
- `qa` MUST 输出 `outputs/qa.json` 与接触表，覆盖冻结/重复帧、banding、aliasing、字幕对比度、响度/真峰值、音画同步与 claims 可见性；技术失败 MUST 以退出码 1 结束，报告 MUST 可定位到镜头/时间戳。
- `assets audit` MUST 只读素材与导入记录，输出 `outputs/asset-audit.json`；hero 资产不合格时 MUST 以退出码 1 结束。
- `master` MUST 产出母版与兼容交付，并在成片旁车记录 profile、母版/交付摘要、音频母版参数与 QA 指纹。
- cinematic 的 look-dev 用户确认 MUST NOT 被 CLI 自动跳过；未确认时 `render --profile cinematic` MUST 阻断。standard MUST 保持无需人工确认。

所有新命令 MUST 遵守离线、素材留证、准备指纹与交付权限规则；缺少准备记录、profile 非法或依赖缺失时 MUST 在渲染前失败，不产出部分产物。

#### Scenario: look-dev 只出样片
- **WHEN** 对 cinematic 作品运行 `m2v lookdev`
- **THEN** 只生成关键静帧、接触表与 20–30 秒有声样片，不生成全片，不覆盖正式成片

#### Scenario: QA 失败定位
- **WHEN** 某镜头出现冻结帧、banding 或响度超限
- **THEN** `m2v qa` 以退出码 1 结束，报告指出镜头/时间戳与实测值

#### Scenario: 未经确认的电影级导出
- **WHEN** cinematic 作品缺少 look-dev 用户确认记录
- **THEN** `render --profile cinematic` 阻断并说明需要先完成 look-dev

#### Scenario: 标准命令不变
- **WHEN** 使用现有 validate/prepare/preview/render 处理 standard 作品
- **THEN** 参数、默认输出、退出码与成片行为保持不变

#### Scenario: 原生 4K 关键帧
- **WHEN** 运行 lookdev 生成静帧，作品包含显式低 DPR 的 WebGL 画布或多个代码幕
- **THEN** 从当前源码连续推进至各幕选定帧，以 2 倍像素绘制画布，PNG 合成原有字幕与转场；不放大 1080p 缓存视频冒充原生细节，像素不足时明确失败；有声样片流程不变
