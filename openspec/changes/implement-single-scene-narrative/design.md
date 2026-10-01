## Context

动机见 [proposal.md](proposal.md)。现有 composition 按 scenes[] 选择活跃幕，分别计算局部帧、beat、镜头与相邻转场；代码模块也接收幕级上下文。媒体 version 3 保存逐幕实际时长和 resolvedBeats，制作门禁尚无独立持续世界结论。

用户已确认：全面替换旧制作方式、建设全片持续场景运行时、保留全片 tree/code 双轨、逐一改编全部八个现有示例。当前代码尚未实现本设计。

## Goals / Non-Goals

**Goals:** 全片只有一个画面根和对象身份域；时间轴可随机访问；有声与无声使用相同求值路径；阶段边界不重置对象或镜头；所有例子有新输入的真实评审证据。

**Non-Goals:** 不实现旧分镜兼容或自动迁移，不改写仓库外作品，不新建模型服务、自动选曲、平台发布或另一个网页入口。保留现有基础安全、视觉令牌、输出路径、码流与权限验收。

## Decisions

### 1. 明确区分世界和阶段

采用 version: 4、schemaVersion: 4、directingVersion: 2。保留根级 fps、尺寸、标题、visual、directingBrief、visualDirection 和声音设置；新增根级 world 与 stages，移除 scenes。未知字段按现有严格 schema 拒绝。

- world：id、claim、metaphor、objects、renderer、data、stateTracks、motions、camera；tree 另需 sceneTree，code 另需 renderer.module，不允许同时声明两种画面。
- objects：每项 id、role、description；角色固定为 primary、supporting、annotation。tree 对象必须映射存在的全局树节点，code 对象必须有规定探针。至少一个 primary，临时出现的对象也预先声明稳定身份。
- stages：id、durationInFrames、data、visualIntent、可选 narrationSegments 与 beats；保留有效的展示文案与强调标记。stage 不包含 renderer、sceneTree、camera 或 transition。
- stage、beat、口播段和全局节点分别具有全片唯一 id，不能通过局部同名制造绑定歧义。对象和对应节点共享同一个身份值，不再使用跨幕映射。

原来 scenes[] 同时承载画面和时间，继续复用该名字会诱导旧制作方式；选择 stages[] 明示仅为叙事时间分段。规格目录 storyboard-v3-contract 保留路径以便增量归档，实施时更新 Purpose 为当前 v4，不重命名历史归档。

### 2. 全局状态使用受控轨道

stateTracks 每项为 id、target、property、binding、to、interpolation。binding 判别联合为 {beatId} 或 {stageId, phase}；phase 使用 establish/change/result/settle。没有 from 字段，起点从对象基础值或此前轨道终态派生，避免两份状态真源。

允许 property 为 visible、state、value、contentRef、sourceRef；其取值类型与目标原语及内容引用仍由注册表校验。visible 为布尔，state 保留 rest/focus/muted/done，value 只用于已有数值和图表受控数据结构，contentRef/sourceRef 为有效内容引用。代码对象采用同样受控可观察状态，复杂几何可由共享全局 beat 纯函数计算。

离散属性只允许 step-end，在绑定区间末提交；数值及同形数据允许 linear 或既有 ease 曲线，数组长度与数据结构变化只允许 step-end。节点创建/删除由 visible 控制，不更换树形或节点类型；复杂对象变形走全片 code。基础值缺失、属性不支持、同对象同属性轨道重叠、绑定无效或结果类型不符都提前失败。

轨道先解析成全局半开区间，按开始帧稳定排序；每帧从基础状态及所有已完成轨道求终态，再计算当前轨道。区间空隙保留终态；无口播静音阶段的 phase 由声明时长及既有阶段算法解析。所有阶段保留至少 12 帧收束，动效不得侵入稳定窗。

与“通过 React state 顺序累加”相比，这个方案能直接寻帧，并且媒体重新定时只需重新解析绑定。不开放任意属性、CSS、表达式或绝对起始帧作为逃生口。

### 3. 全片双轨共享唯一时间上下文

composition 全片挂载一个世界根。tree 先求对象状态，再传给同一递归解释器；code 全片挂载同一作品模块。阶段数据可切换展示标签，但禁止把不同完整页面包装为条件分支冒充持续世界，这一点由动态评审判断。

全片代码 props 固定为 world（内容与对象声明）、frame、progress、fps、canvas、theme、stage（id、index、localFrame、progress、data）、beats（全局 plan、current、progress、completed、estimated）、objects（只读求值状态）、camera（当前全片镜头状态）。不提供旧 scene、continuity 或幕级渲染器；阶段时长及 beat 区间可作为共享层生成的只读计划，不允许模块自己推导第二套总时间轴。

模块仍放在作品 scenes/ 下，沿用稳定路径校验、当前作品静态模块清单、固定白名单、稳定种子、离线网络隔离和源码指纹。避免无关目录迁移。复杂运动使用全局 beat 区间及对象身份生成确定性几何，探针同时暴露 worldId、stageId、objectId、角色、容器与几何。

### 4. 镜头和音频从派生时间轴解析

world.camera 保留现有受控镜头段词汇，将所有绑定提升至全局 beat 或阶段 phase。每段以上一段终态为起点，空隙 hold；有重叠绑定或不可见焦点时失败。移除独立幕 section、进场转场和共享元素映射路径，世界身份连续由同一对象直接表达。

媒体 version 4 保存同序 stages（id、durationInFrames、audio）和根级 resolvedBeats，后者包括 stageId、beatId、全局 startFrame/endFrame、action、targets。先解析全部阶段实际时长，再累加全局边界；统一供字幕、状态、动作、镜头、节拍音效与混音使用。effects 的 sceneId 改为 stageId，禁止两种标识混用。缓存键包含契约版本、段文本和声音参数；不重用旧清单或旧边界。有声入口检测清单版本、源指纹、次序与区间，出错提示重新 prepare。

window.__A2V__ 的契约版本升级为 4，提供全局帧、当前阶段、对象状态与几何、镜头与 beats。预览、量测、局部渲染和正式导出均从 composition 共用这一模型。provenance 自身版本 4 保留，因为本轮不改变其外层结构；输入摘要纳入新的分镜、轨道及可达模块即可。

### 5. 检查有效推进，而非强迫换画面

视觉模式受控枚举与图形证据检查继续使用；取消短片至少两种、长片至少三种非文字模式预算，保留 ceil(stages × 30%) 文字幕上限和相邻文字幕禁令。

复用指纹改为世界结构、对象角色、目标属性、受控动作及变化类型，不读取正文。相邻同构阶段如果存在非中性 beat 且轨道产生非文字状态差异，就允许复用；只有 contentRef 的文字替换不计论证推进。受控数值/图表变化、visible 的解释型显隐及语义 state 变化都必须由有效 beat 支撑；单纯 reveal/highlight 不充当推进证据。

代码路径无法仅靠 JSON 证明运动时，结构报告明确 pending，动态探针核对对象的可观察变化，AI 实际播放判断论证质量。严格 schema 校验可以成功，但 pending 的动态证据不得满足正式输出门禁。提升视觉预算及复用 RULE_VERSION，测试固定新口径。

### 6. 独立连续性记录与材料

production 记录 version 4 增加 continuity 五项：worldConsistency、identity、stateCarry、cameraContinuity、resultReadability。每项包含 pass/fail/pending、stageId 与帧/时间依据、assessment 来源与材料 SHA-256。关键阶段与全片静态/有声评审继续保留；定制五项评分中的转场连贯性改为阶段衔接连贯性，4/5 门槛不变。

关键阶段片段以全局帧裁切，前后各最多 12 帧上下文，夹到全片范围；边界材料额外采集开始前一帧、起始帧、结束前一帧与下一帧（存在时）。不以像素完全相同要求抹平合理动作，而以状态轨道、镜头终态与播放证据判断连续。媒体变化使动态与连续性过期；资产变化使相关静态和动态过期。缺材料不能填写通过。

### 7. 示例和主规格同步

新增 darts-trial-and-error 标杆，默认全片 code，人物、飞镖与靶用全局稳定对象并以 SVG/受控运动呈现，数量均标示意。八个旧示例保留目录与主题：buffer-smoothing 的缓冲系统、cause-chain 的因果网络、code-scenes 的同一技术系统面板、declarative-number 的计数对象、keynote-baseline 的统一概念模型、milestone-climb 的攀登结构、narration-beats 的持续流程模型、why-effort-fails 的投入产出系统。

每个示例只选一个 renderer。cause-chain、declarative-number、narration-beats 优先 tree；其余优先 code，持续场景内保留原有技术覆盖，不能为了覆盖不同库切换无关页面。全部重新准备媒体、生成评审材料、实际评审并渲染验收；生成 MP4 留在忽略的 outputs，源码、分镜、抽象动作说明与验收摘要纳入 Git。

## Risks / Trade-offs

- [旧作品不能执行] → 所有入口明确诊断，仓库外内容不自动修改；重新编排使用 Skill，重新生成媒体和评审。
- [声明连续但实际切页] → 全片唯一结构约束加实际动态连续性评审，禁止仅凭 JSON 填通过。
- [全片树更大] → 保留受控节点与子容量上限，超出当前 48 节点能力时选择全片 code，不擅自放宽限制；状态计划预编译，避免每帧重新解析媒体或布局。
- [有声时间改动导致状态错位] → 无绝对帧绑定，先解析实际阶段再推导全局轨道；双端固定测试向量。
- [八个示例改编耗时] → 按示例逐个记录检查和真实评审，不提前勾选，缺媒体或评审条件明确报告未完成。
- [隐藏的旧规格矛盾] → 实施阶段审查活跃主规格、参考文档和命令示例中 scenes/sceneId/逐幕/v3 的行为语义，补齐相应增量；不修改历史档案，也不把所有“场景”字样机械替换。

## Migration Plan

先实现双端 v4 契约和测试向量，再切换共享运行时、prepare 与命令、制作门禁，随后飞镖及八个示例。实施期间不宣称新能力已经落地，README 当前状态在验收通过后更新。

完整验证后提交仅包含本次源码、示例和文档；再同步增量与主规格（包括保留路径下的 v4 Purpose）、归档并提交。发布以一次完整可验证的版本切换为单位，不保留旧格式运行时。若必须回滚则回退整组实施与归档提交，不做 v3/v4 混用；不删除或覆盖用户内容与旧成片。
