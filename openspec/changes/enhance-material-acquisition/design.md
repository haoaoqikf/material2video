## Context

动机及能力清单见 [proposal.md](proposal.md)。当前 `author assets search` 要求查询数量与场景数一致，默认只有 Pixabay；`import` 只接直链或本地文件，正式单文件上限 256 MiB。主项目已有 yt-dlp、抖音参考提取、FFmpeg 接触表和切镜测量，但尚无统一素材工作层。

独立作品的本地导入比主项目更严格：文件必须在作品根内；项目只允许 storyboard 材料，运行时不读取主仓库。新增能力必须位于制作期工作层，不能通过共享库路径例外或新增 runtime 协议破坏作品独立性。

第一部分指南已在 `2eb76e67` 独立提交。本设计只覆盖第二部分。此变更尚未实现，不能将下列目标写为现有能力。

用户 2026-11-15 明确要求后续不再使用子 agent：停止已有并行子任务，由主代理亲自接手实施、测试和完整代码自审。此前已经取得的独立审查结论保留其当时范围；后续自审不独立，必须显著披露，不能据此声称独立评审通过。此执行方式更新不缩减功能、真实测试或安全契约。

## Goals / Non-Goals

**Goals:** 覆盖需求到正式本地素材的完整流程，包括真实转录、OCR、中文文本和视觉检索；接口可组合、可离线测试，来源、媒体字节、时间映射和实际观察分别追溯。

**Non-Goals:** 不新增类型、分镜/项目/正式媒体登记版本、成片审核职责、素材配额或许可审批；不建立云服务、账号运营、自动发布、大型向量平台或全网镜像；不绕过验证码、DRM、付费权限或去水印；不将图像相似分数解释成事实或动作完整性。

## Decisions

### 1. 制作工作层与命令边界

新增 `src/m2v/materials/`，以契约、存储、来源、网络获取、模型、索引、检索、预览、选择、库和 CLI 按职责分模块。CLI 只解析、调度和映射错误，不建立万能管理器。复用现有严格 Pydantic 基础、媒体采用政策、图库、受控文件交付、作品写锁和 FFmpeg；确有共享价值才提取公共工具，不复制整个旧模块。

选择 `m2v author assets` 而非新增顶层命令，保持用户素材操作的单一入口：

| 工作流 | 输入 | 输出/副作用 |
|---|---|---|
| discover | `--request` 需求文档或重复 `--query`，显式来源、分页/数量 | 来源候选及各源失败，不下载视频 |
| fetch | URL、来源 ID、显式本地文件，格式/区间/预算 | 源媒体、字幕/章节、来源与实测记录 |
| index | 媒体 ID，字幕/ASR/OCR/镜头/文本/视觉选项 | 本地索引与缓存，不隐式联网 |
| find | 查询/需求、查询通道、索引/库范围、Top-K、条件 | 候选区间、各通道召回依据；不自动获取或索引 |
| preview | 候选 ID/文档、上下文与显示偏好 | 接触表、短预览、静态 HTML 和索引 |
| select | 选择清单，输出/项目/asset ID，显式替换策略 | 精裁、manifest、receipt；`--import` 才修改作品登记 |
| library | 显式目录登记、核验、统计及清理操作 | 本地索引范围、复用、清理清单 |
| models | list/prepare/verify，显式模型名与设备 | 可恢复本地模型登记；prepare 才联网下载 |
| doctor | 工具/运行库/模型/来源能力诊断 | 结构化可用性，不自动安装或暴露凭据 |

公共操作接受 `--project` 或 `--workspace`，默认工作目录为 `<project>/outputs/materials/`；无作品时显式 workspace。`--library` 仅引用明确指定的共享库，不扫描个人目录。models 使用显式模型目录或工作库 `models/`，不依赖隐蔽全局缓存。

原 `search` 与 `import` 保持现有调用方式；新 discover 与 search 共用 Pixabay 适配器。抖音 `ref` 的研究目录不直接供正式渲染，新获取仅复用提取机制，必须走同样的选材、复制、导入。

### 2. 工作材料与数据库权威

新工作文档使用 `{schemaVersion: 1, kind, id, createdAt, data}` 封套，`kind` 为 `material.requirement|source|media|index|candidate|selection|receipt`。集合输入使用同样版本和明确复数 kind。严格拒绝未知版本、未知字段、bool 冒充数值、非有限数、非法路径和区间。

SQLite 是运行元数据与关系的唯一权威；JSON 是事务后导出的不可变快照，不允许任意双向修改。导入外部需求/选择须经严格校验，数据库使用外键、唯一缓存身份、busy timeout、短事务。网络、解码和推理不持有数据库写事务。媒体/向量先暂存、校验、内容寻址发布，再提交引用；崩溃遗留孤立对象可清理，不引用半文件。

核心记录如下：

| 记录 | 最少信息 |
|---|---|
| requirement | 文本、职责 evidence/identity/process/explanation/mood、对象/动作、身份/事件/地点/日期限定、多语言查询、最短过程窗口、比例偏好、允许示意、可选 sceneId |
| source | provider、平台稳定 ID、公开来源页、作者/发布主体、标题/描述、发布日期及精度、原始许可与现有 usage、元数据快照摘要 |
| media | sourceId、实际文件相对路径/摘要/字节/格式、variant、full/section/unknown 覆盖、请求与实测区间、probe、timeline、获取身份、工具链 |
| index | 媒体摘要、索引类型/状态、参数和工具摘要、输入字幕/模型身份、输出文件摘要/记录数、向量空间和时间映射身份 |
| candidate | 需求/索引/媒体摘要、局部与源窗口、召回原因、原文摘录/关键帧、各通道分数、预览、实际观察与未验证项 |
| selection | 候选/媒体摘要、局部窗口、源窗口、chosen/rejected、理由、观察依据、转码策略、输出摘要和工具链 |
| receipt | 操作/选择/媒体身份、源与局部窗口及映射、manifest 摘要、目标 asset ID/路径/摘要、登记项摘要、pending/committed/failed |

所有库内路径为相对根的 POSIX 路径，所有程序执行路径由验证后的记录解析，不能从 JSON 接收任意命令或宿主绝对路径。宿主的显式本地输入可为绝对路径，但进入记录只保留实际文件身份和允许公开的来源，不将私人宿主路径写进可发布 receipt。

时间统一整数微秒、半开区间 `[startUs,endUs)`；原始 PTS 和有理数 time base 独立保留。图片区间为 null，不能假装有动作窗口。

### 3. 来源覆盖、发现与状态

实现 Commons、Archive、NASA 原生公开接口，复用 Pixabay；B站/YouTube 使用 yt-dlp 的站点搜索，数量与分页有界；抖音复用已有提取，小红书、微博、西瓜及其他站点用已知分享链接尽力提取；上述站点均纳入逐站真实有限尝试与能力矩阵，不要求受限平台必须下载成功。网页提供公开 video/source/img、媒体链接和结构化元数据发现，不执行任意脚本或自研全网搜索。

Pexels API 仍停用，支持来源页登记和公开文件获取。快手/视频号等未验证接口提供搜索入口、诊断和本地文件替代，不宣称稳定自动获取。通用网页发现可由助手现有工具产生 URL，CLI 不绑定 DSH 或任何付费搜索服务。旧 `ref` 的显式浏览器路径保持原语义；新 fetch 不直接调用不受网络策略约束的浏览器，只有完成同等出站限制后才能接入自动回退，否则报告可通过原参考操作或已有本地文件继续，不能声称浏览器路径已经受 SSRF 防护。

每个来源返回 results/failures/partial，成功零结果不等于网络失败。JSON 结果保留各源覆盖；CLI 退出码：0 为全部请求成功（允许零命中），1 为有部分成功但存在失败，2 为参数/契约错误或全部失败，130 为取消；与旧 search/import 的退出行为隔离，不暗改旧入口。

方向只作排序偏好。证据型身份限定只有来源证据或实际核对能满足；视觉相似不能自动通过。

### 4. 受控网络、平台子进程与资源

新 HTTP 传输必须检查 URL scheme/userinfo/端口/控制字符，解析 IPv4/IPv6 并拒绝私网、回环、链路本地、组播、元数据和映射私网地址；连接绑定已经校验的解析结果。每次重定向、页面媒体/字幕/缩略图及 HLS/DASH 子资源都走相同策略；跨源不转发凭据。默认不用环境代理，私网假服务仅由测试显式注入 transport。

yt-dlp 运行于受控子进程，只接受白名单结构化参数，禁用户配置、任意插件、shell/external downloader 和任意 FFmpeg 参数。网络下载仅允许可强制检查的 handler/native 路线；后续连接同样验证，单独的初始 URL 校验不算完成 SSRF 防护。

已核验 yt-dlp 的区间/live/HLS 回退可能调用联网 FFmpeg，因此不以 `hls_prefer_native` 声称绝对隔离。优先使用可执行的受控 handler/连接策略，并对 FFmpeg 网络下载 fail-closed；普通文件的 HTTP 区间恢复与原生片段在同样策略下运行。无法保证安全的上游区间下载回退为预算内完整获取后本地精裁，或明确报告需要本地文件，不能静默放开网络协议。live 与 DRM 不纳入自动获取。

实现固定到经审查的 yt-dlp 版本，worker 的 RequestDirector 只注册自定义 PublicOnlyUrllibRH，不以优先级替代强制约束，不允许 requests/curl_cffi 自动回退。urllib 内部 redirect_request 逐跳校验；受控连接创建器返回同一批已检查数值 sockaddr，并在 socket connect/connect_ex 处检查实际数值目的地址，作为纵深防护。要求 is_global 并显式排除组播、保留地址、CGNAT、映射 IPv6 私网和未处理的 IPv6 过渡机制；端口默认仅 80/443。跨 origin 清敏感头，拒绝保留敏感 POST 的跨源 307/308。

worker 禁环境代理、netrc、cookiesfrombrowser、任意插件、远端组件、外部 JS、impersonation 和非白名单后处理；这会使部分 YouTube 格式或验证路径不可用，必须明确报告，不静默开放。此策略是固定版本及审核 extractor 的应用级防护，不宣称 OS 级网络沙箱。外部 JS/浏览器如未来接入，须先有独立出站隔离验证。

本地 FFmpeg 索引/预览/精裁限制到受控本地媒体与必要本地协议；默认拒绝伪装媒体的网络播放列表。子进程有时限、取消和进程树回收，日志只显示脱敏来源。

获取实行可配置单件/总字节、时长、磁盘余量、重试及并发预算；默认下载并发 2、推理并发 1。退避遵循 Retry-After 并有上界，续传必须核对 ETag/Last-Modified/长度等身份，不将未知远端版本接到旧文件。临时媒体 URL 重新解析，不当作永久来源 ID。

Key 只读环境变量；cookie 仅显式文件/专用 profile；普通数据库、快照、异常、HTML 和 receipt 不持久化完整 cookie、Authorization、带会话 token 的分享链接或签名 CDN 参数。技术可得性与素材采用状态分开，现有从宽政策不变。

### 5. 媒体身份与可信时间映射

分开存储页面条目身份、本次实际文件 SHA256 和完整上游 SHA256。只有确实取得完整上游字节才填后者，不能把片段摘要冒充整片摘要。

`timeline` 保存首有效展示 PTS、time base、局部归零方式，以及 sourceMapping 的 verified/estimated/unknown、方法、源原点、速率和误差。区间请求起点只是意图，不是实测源原点；下载器归零后无法证明源原点时保持 unknown。

未知源映射可以按本地已哈希媒体执行精裁，但候选/receipt 的 sourceRange 为 null，并明确局限；需要精确源引用的任务应先取得可靠映射或整片，不能编造。VFR 依 PTS 而非 nominal fps 换算；非线性/多段映射若未支持必须拒绝自动换算。预览转码另存映射，不从文件名推偏移。

### 6. 索引、模型与外部方案选择

已有 FFmpeg 接触表/黑场/切镜作为基础，复杂切镜引入 PySceneDetect adaptive 可选后端，避免自己重复发明成熟算法。平台人工字幕优先，自动字幕及外部 SRT/VTT/ASS 分别标记来源和对齐状态。无字幕时 faster-whisper；画面烧录字用 RapidOCR，不把 OCR 当成可下载字幕轨。

| 能力 | 采用方案 | 理由与替代 |
|---|---|---|
| ASR | faster-whisper + Systran/faster-whisper-small，CPU int8 默认 | 支持中文、词时间码及 VAD；比完整 GUI 工作站轻，GPU 可选 |
| OCR | RapidOCR + ONNX Runtime | 中英与 Windows 支持；代码、转换及上游权重分别登记 |
| 文本语义 | intfloat/multilingual-e5-small + Transformers | 中文多语言检索，保留 query/passage 前缀；不先引入云 embedding |
| 视觉 | google/siglip2-base-patch16-224 + Transformers | 明确多语言、Apache-2.0 模型卡；不再同时引入等价 OpenCLIP |
| 镜头 | FFmpeg 基础 + PySceneDetect adaptive | 复用现有，复杂情况有成熟可选算法 |

研究来源包括 [yt-dlp](https://github.com/yt-dlp/yt-dlp)、[faster-whisper](https://github.com/SYSTRAN/faster-whisper)、[RapidOCR](https://github.com/RapidAI/RapidOCR)、[E5 模型卡](https://huggingface.co/intfloat/multilingual-e5-small)、[SigLIP 2 模型卡](https://huggingface.co/google/siglip2-base-patch16-224)、[PySceneDetect](https://www.scenedetect.com/docs/latest/)。StoryToolkitAI 过重且 GPL 集成成本高、clip-retrieval 偏大规模图片服务、BBDown 原仓库归档，均不作为本系统主干；Chinese-CLIP 本次未核清完整许可，不引入。

新增模型登记单一权威，固定仓库 revision、文件列表/摘要、许可证、包版本、预处理和恢复路径；软件与模型许可分开，yt-dlp/FFmpeg 打包构建不得一概按源码许可描述。可选 extras 对应 asr/ocr/semantic/vision/scenes，并提供组合安装方式，不把所有模型塞进每个作品。

prepare 模型是显式联网动作，verify/index/find 离线，只用本地固定输入且 `trust_remote_code=False`。CPU 批量、GPU 可选；模型摘要/推理参数/设备精度进入缓存，缺项明确缺依赖，不静默换模型。

索引绑定媒体、字幕/模型、参数、版本与时间映射摘要。关键帧在镜头首/中/末采样，长镜头补间隔帧；OCR 按需区域化；转录分段缓存。中文词面用规范化字符 n-gram，避免英语分词漏召回。文本/视觉各通道独立检索，使用 RRF 融合，不将不同量纲原始分数相加。

向量采用不可变安全 `.npy` float32 分片（禁止 pickle），SQLite 保存索引行、维数、空间摘要和分片身份；查询分块点积，不一次载入全库。不同模型 revision/预处理/维数不得混查。更换模型只重建受影响索引。

### 7. 候选观察、预览与选择

候选带原文摘录、关键帧、各通道命中原因和实际观察，subjectMatch/actionVisible/actionComplete/cropUsable/factualIdentityMatch 使用 observed/not-observed/unknown 三态，并保留观察窗口及依据。默认 unknown，模型得分不能填 observed。

接触表复用原模块；批量候选由新层逐件调度，不改旧 contact-sheet 最多一个视频的合同。短预览带源/局部时间映射；静态 HTML 使用转义文本、受控相对路径和本地媒体，支持候选比较及导出选择 JSON，不启动服务器，不把外部脚本或敏感 URL 注入页面。

助手或操作者查看后生成选择，不默认要求用户逐条批准。精裁以解码后 trim/setpts、音轨对应裁切重编码实现，显式 fps/像素格式；按真实 PTS 校验起止，保留或丢弃原声是选择属性。`-c copy` 只可用于明确快速预览/封装，不宣称帧精确。

### 8. 跨作品导入、恢复与清理

选中片段先核对摘要并复制到目标作品内私有暂存，不用符号链接/junction/hardlink；持有与现有作品写操作同域的锁，生成原有 schema manifest，调用现有 import。正式文件仍在 `assets/media/`，最大 256 MiB；超限应调整片段/编码或失败，不自动升级契约。

receipt 放在作品 `assets/materials/receipts/` 并由来源说明引用，包含操作、选择、源身份、时间映射、manifest 和目标登记身份，不进入正式媒体 schema，也不成为渲染依赖。`usableSegment` 保持候选检查意义，不填原片几百秒冒充片段本地坐标。

asset ID 已有不同字节时默认冲突，显式 replace 才替换。先记 pending 操作，导入成功后核对登记再 committed；若导入成功而 receipt 发布失败，恢复时依据操作和正式摘要补凭据，不误称导入未发生、不重复覆盖。失败只清本操作暂存，保护旧有效记录。作品移走或库删除后仍能离线工作。

库扫描仅显式目录，默认不跟随 reparse point； SHA256 去重实际字节，感知摘要只提示相似不混同来源。清理先输出计划，显式执行前重新核验引用；保护选中对象、有效候选/索引、receipt、原始研究和唯一源证据，不清理作品正式媒体。现有两次历史备份上限不被新库机制改写。

### 9. 错误、性能与验证口径

统一 MaterialError（M2VError 子类）带 code/stage/retryable/sourceId/safeMessage；至少区分 invalid-request、unsupported-source、dependency/model-missing、auth/session/challenge-required、rate-limited、network-timeout/unavailable、not-found、expired-locator、media-invalid/decode-failed、hash-mismatch、timeline-unverified、resource-limit、security-blocked、conflict/store-busy、cancelled。

单元测试使用注入 HTTP/模型/探测适配器；真实媒体仅相关节点，CPU 模型实测独立记录；不默认全仓回归。固定生活/动作、公司/产品、人物/事件、历史/科学四类至少 24 查询，事前逐条记录必要对象、动作、身份、连续窗口、可接受样本及负例，不适用条件标 N/A。分母固定为事前判定可满足的查询，不可满足项和负例另行报告，不得事后调整分母。Top-5 中至少一段经过实际查看且满足该查询全部必要条件才算可用命中；未知观察不能计为符合。分别报告各通道和融合结果，融合 Top-5 可用率目标至少 75%；身份/动作子指标另外报告但不豁免必要条件。查找操作中位耗时较相同素材手工流程目标降低 30%，记录真实样本及计时局限。所有选中片段来源/区间追溯完整率 100%；实际起点、终点相对请求本地窗口的误差分别不超过目标输出一帧，输出时长误差不超过目标输出一帧，VFR 按真实展示 PTS 和声明输出帧率判定；上游映射未知只验收本地已哈希媒体位置。有音轨样本偏移不超过 50ms。

一万条索引热词面查询本机目标 2 秒，记录硬件、冷启动、峰值内存；相同输入重复索引无下载/推理。四个模型能力均需真实运行，mock 不能关闭验收。来源逐站记录 succeeded/limited/failed/not-tested，网络和登录限制不包装成通过。

## Risks / Trade-offs

- [平台接口变化和登录限制] → 版本固定、部分成功报告、明确能力矩阵与本地替代，不承诺全平台稳定。
- [yt-dlp/FFmpeg 跨进程出站绕过初始校验] → 请求及连接守卫、native 白名单、联网 FFmpeg 拒绝与本地精裁回退；专项安全测试先于宣布通用获取安全。
- [源时间误标、VFR、归零封装] → 保留微秒/PTS/时间基与映射置信度，未知不填源区间，受控样本逐帧验证。
- [模型启动、权重和 Windows 依赖成本] → extras、显式准备、CPU 默认、分批推理、权重/许可登记和缓存；磁盘现有充足不代表可无限使用。
- [误召回和身份错认] → 原始召回依据、unknown 观察、实际预览和既有终审；不把分数当概率或事实。
- [数据库与文件发布不一致] → 不可变对象、短事务、pending 操作及幂等恢复；清理重新检查引用。
- [工作层侵入独立工程] → 只输出项目内文件和现有 manifest，模板/正式 schema 不加共享库依赖。

## Migration Plan

这是加法能力，不升级 project/storyboard/正式媒体格式，也不迁移旧参考通过状态。新工作 schema 未知版本直接拒绝，不建立旧版兼容分支。现有 search/import/ref 回归保护。先契约及获取，再索引检索、预览选择和复用；本轮所有模块完成后才整体声明实现。

回滚仅移除新增入口和工作层，不删除用户作品或素材库；已通过现有 import 进入作品的字节仍按原正式契约独立可用。提交前完成代码复核、相关测试和真实验证；后续代码复核按上述用户更新改为主代理自审并显著披露不独立，不能继承此前局部独立结论。全部实施任务与提交通过且适用归档条件满足后按项目约定归档。验证记录如实区分通过、受限及未验证，不以工具返回成功代替质量。
