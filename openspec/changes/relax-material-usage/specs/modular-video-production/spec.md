## MODIFIED Requirements

### Requirement: 制作与质检入口（当前媒体流程）

系统 MUST 在统一入口提供制作与质检命令：`m2v lookdev --project <目录>`、`m2v qa --project <目录>`、`m2v assets audit --project <目录>`。正式导出沿用现有 `m2v render`，不新增母版命令。命令 MUST 沿用现有作品路径、内容根、退出码与产物归属规则。

- `lookdev` MUST 只渲染关键静帧与代表片段，MUST NOT 生成完整成片；输出位于作品 `outputs/lookdev/`，包含按风险选择的代表静帧（默认原生像素，可显式 2 倍）、接触表与按风险确定长度的有声样片（无声作品保持无音轨）。帧序列、量测与自动音频信号检查的结论写入作品 `outputs/visual-notes.md`，作为检查与返工依据，MUST NOT 成为导出门禁；MUST NOT 要求播放样片或连续收听声音。
- `lookdev` MUST 额外支持四种取点模式，与默认代表静帧互斥，同一调用 MUST NOT 同时声明：按指定时刻拼图、按时间区间拼图、同帧一致性自检、按幕内事件取证。指定时刻与区间 MUST 接受秒为单位的输入，并按作品实际帧率换算为帧号；拼图 MUST 在每格标注时刻与帧号，标注 MUST 只用不依赖中文字体的字符。
- 事件取证 MUST 接受可重复的 `--event sceneId:eventId`（事件 ID 全片唯一时可省略场景）、显式声明的 `--before` 与 `--after` 整数帧，以及可选 `--hold` 整数帧；MUST NOT 提供未声明的默认窗口，每次调用 MUST 由作者显式声明前后窗口。事件 MUST 从当前准备记录的 `resolvedEvents` 解析并绑定当前 `preparedFingerprint`；准备记录缺少事件表、选择器未知或在多个幕中歧义时 MUST 在启动浏览器前失败。
- 事件取证 MUST 围绕每个事件取 `before`、`at`、`after`、`hold` 四类帧；四类帧 MUST 位于事件所属幕内，越界时 MUST 明确指出事件、阶段、局部帧与合法范围并失败，MUST NOT 静默裁剪。同一帧被多个阶段命中时 MUST 只采一次并合并来源标签；相邻选中事件间隔小于 `before+after` 时 MUST 给出事件簇警告，MUST NOT 静默隐藏。
- 指定时刻与区间的帧号 MUST 在启动浏览器前完成校验：越出全片范围或不落在任何已准备场面窗口内的时刻 MUST 立即失败并指出该时刻，不先执行采集再报错。
- 同帧一致性自检 MUST 对同一批时刻执行两次独立采集，逐帧比较并报告不一致的时刻与实测值；判定阈值 MUST 沿用既有的 PSNR 60 dB，MUST NOT 引入第二套阈值。比较前 MUST 确认两次输出尺寸一致，尺寸不同 MUST 明确失败而不是给出误判结论。
- 四种新增模式的产物 MUST 落在既有 `outputs/lookdev/` 下并由 `outputs/lookdev.json` 记录路径；MUST NOT 写入 `outputs/production/` 下的评审记录目录，避免与正式制作证据混淆。产物 MUST NOT 进入准备指纹或缓存键。
- 事件取证是看图预览，MUST NOT 自动关闭或替代 局部评审 检查点、审核轮次或导出门禁；MUST NOT 把事件窗口自动绑定到旧声明式合同。新增模式 MUST NOT 改变默认代表静帧、样片长度、采集尺度与既有清单字段的语义；`--stills`、`--sample-seconds`、`--still-scale` 的现有行为 MUST 保持不变。
- `qa` MUST 输出 `outputs/qa.json` 与接触表，覆盖冻结/重复帧、banding、aliasing、字幕对比度、响度/真峰值、音轨时长差与 claims 时间窗覆盖，并提供全片采样清单、交界/异常加密帧、黑帧/突变及交付音轨削波/静音候选，并明确区分技术判定、测量提示和需查看采样图像的项目与自动信号检查的覆盖限制；MUST NOT 将技术通过表述为视觉质量通过；技术失败 MUST 以退出码 1 结束，报告 MUST 可定位到镜头/时间戳。
- `assets audit` MUST 只读素材与导入记录，输出 `outputs/asset-audit.json`；任何登记素材明确禁止当前用途、采用元数据无效、文件缺失或尺寸无效时 MUST 以退出码 1 结束；conditional 条件未满足 MUST 只作提示，不阻断。
- 正式导出 MUST 沿用 `m2v render`，交付普通 H.264 MP4；系统 MUST NOT 提供 `m2v master` 或 ProRes/DNxHR 母版入口。成片旁注文件 MUST 记录交付摘要、音频参数与 QA 指纹，MUST NOT 记录 profile。
- 所有制作阶段均取消用户确认：`m2v render` MUST NOT 因缺少帧序列/量测复核记录、确认文件或 look-dev 产物而阻断。

所有新命令 MUST 遵守离线、素材留证、准备指纹与交付权限规则；缺少准备记录、存在旧 `productionProfile` 声明或依赖缺失时 MUST 在渲染前失败，不产出部分产物。
