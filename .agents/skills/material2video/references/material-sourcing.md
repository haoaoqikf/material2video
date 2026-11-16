# 素材检索、评估与台账

设计样品及正式交付遵守[网页原生样品的 AI 边界](design-samples.md#ai-图片的边界)：生图仅作内部构思/参考，不能直接交付，也不能贴入网页加镜头运动代替核心实现。本页生成记录和素材导入说明不构成样品通过；真实照片、档案及外部模型等仍按各自用途与许可核验。

本页是外部素材的操作手册，回答「今天怎么找、怎么验、怎么记、换素材后查什么」。选什么载体、为什么选，权威在[视觉素材选择与使用](visual-material-selection.md)；导入字段、来源记录与声音契约在[媒体与音效](article-media-and-sound.md)。本页只补操作步骤，不新增阶段、审核轮次、分镜字段或 CLI 门禁。

## 1. 开工前先有三样东西

| 输入 | 从哪来 | 用途 |
|---|---|---|
| 每场一句话任务 | 对应场景文档 | 决定要找“证据、识别、过程、机制还是情绪” |
| 每幕 `keywords` | `storyboard.json` | `assets search` 的检索词；也是候选是否对题的检查线 |
| 载体来源政策 | `DESIGN.md`「表达载体」 | 哪些必须真实、哪些只能代码解释、图库能不能用 |

三样缺一时先补设计，不要用检索结果反过来决定片子在讲什么。

## 2. 按用途与对象选择来源

先按[来源优先级](visual-material-selection.md#按用途排序素材来源)确定真实原件、代码、生图或混合路线。内部研究需要定制概念参考且当前代理支持生图时可进入下方生成步骤，不先穷尽外部图库；证据型任务仍按原始来源检索。

讲到具体公司、产品或生产过程时，先检查相关官方来源，再按实际缺口扩展；找到合格素材即可停止，不要求搜遍所有栏目或达到固定次数。

| 对象 | 优先检查 | 扩展来源 | 要核什么 |
|---|---|---|---|
| 公司、品牌 | 官网新闻中心、媒体中心、品牌素材库、投资者关系、官方视频账号 | 行业协会、采访、新闻机构 | 主体、发布时间、原始发布与转载关系 |
| 产品、技术 | 产品页、发布会、演示、说明书、技术文档、官方案例 | 供应商、研究机构、专业评测 | 型号、版本、演示是否对应具体主张 |
| 工厂、生产过程 | 企业工厂视频、参观资料、官方账号 | 行业协会、设备供应商案例 | 真实企业与工序，动作窗口是否完整 |
| 人物、事件 | 当事人及所属机构、活动主办方、原始采访 | 新闻机构、法院/议会、历史档案 | 人物、地点、年代、事件身份 |
| 科学、历史、自然 | 大学、研究机构、博物馆、图书馆、档案馆 | 专业组织、Wikimedia Commons 等开放库 | 馆藏编号、原始出处、文件级使用限制 |
| 背景、情绪、示意 | 开放媒体库、Pexels 等图库、其他公开发布素材 | 按缺口补充公开来源 | 是否仅作示意、构图与使用限制 |

能拿到原件就不拿转载。官方账号是正式来源，社交平台只是载体；须确认账号身份和原始发布。公司宣传片能提供对象画面，不能自动证明所有宣传结论。参考作品用于分析，其中独立素材应追溯原始发布者后再评估；不得默认把整条参考作品当可复用素材。

先明确对象、动作、年代、地点、所需过程窗口与可接受示意，再围绕缺口检索。例如「公司名 + factory / manufacturing / product demo / press kit」，补查站内新闻、媒体资源或官方账号；缺少装配动作就针对装配检索，不用泛产业空镜冒充。官网公开直链、用户提供的本地文件或已取得的截图均走统一导入；平台条款、登录墙与付费墙不算采用禁止，工具不实现绕过凭据的自动抓取。

口播通用画面先按[口播选材规则](visual-material-selection.md#观点旁白与意境素材)整理每段对象和动作，再优先查 Pexels 和 Pixabay。以实际动作、构图及使用窗口筛候选，缺少合适素材时扩展到其他公开来源。

### AI 图片生成与记录

1. 检查当前代理是否有实际可用的生图工具，按该工具及适用生图 skill 操作；无需凭据的内置工具可用时优先使用。工具不可用或调用失败如实记录，回到其他合格来源。
2. 在对应[场景文档](scene-design.md)说明图片的叙事任务、主体、构图、准确文字、画幅和真实／示意边界。参考图先核查来源与可用范围；历史照片、真实人物或产品内部结构不能通过生成补成事实证据。
3. 在作品内容目录保存实际完整提示词、工具名称、生成日期、参考输入及其来源、原始输出、采用输出与摘要；采用后把文件复制到作品目录，不只依赖聊天展示或工具默认保存位置。记录属于作品材料，不另建公共字段或绕过忽略规则入库。
4. 实际查看原生图与目标手机尺寸，检查对象错误、文字、细节、构图及与相邻镜头的衔接；生成成功不等于可入片。生成图片保留为内部参考，正式主体与过程由网页实际实现；不得用整张生成图冒充原生主体。
5. 若内部探索需用素材台账保存，使用现有 `localPath` 导入（不代表准许正式入片）：`sourceType: "other"`，`publisher` 写实际生成工具／本作品，`description` 明确 AI 生成及用途，`author`、`license` 如实记录；不编造外部作者、来源 URL 或许可。工具使用条件、参考图权利与第三方内容分别核查，`usage` 沿用既有状态，不把生成成功自动等同授权。
6. 采用后把实际生成记录及素材 ID 纳入 `SOURCES.md`。可能被当作实拍、历史记录或真实操作的画面按既有规则保留必要小字示意边界；抽象插画不逐镜叠加无用途说明。AI 生成图片不是独立目标图的自动凭据，目标图仍按[独立目标关键帧](review-contract.md)判断。

## 3. 检索词怎么写

- **对象 + 动作 + 限定**：`纺织厂 童工 1833`、`ILO 1919 delegation`、`factory floor assembly line`。
- **换语言**：中文找不到就换英文、原文语言或机构惯用名（`International Labour Conference 1919`）。
- **换范围**：年代（`1930s`）、地点（`Chicago`）、介质（`photograph`、`newsreel`、`archive footage`）。
- **从窄到宽**：先精确事件；无结果再退到同类过程，但退到“同类”时必须记录它只是示意。
- 检索词与来源页写进工作记录或 `SOURCES.md`，方便复核“当时到底搜了什么”。

用 Pixabay API 按关键词检索候选：

```powershell
uv run m2v author assets search --project videos/<类型>/<slug> --kind both
```

不传 `--query` 时按幕读 `keywords`；只出候选、不下载。也可在 [Pexels 官网](https://www.pexels.com/) 搜索照片或视频，选定后按 [Pexels 公开媒体直链](#pexels-公开媒体直链) 导入。

## 4. 候选评估卡

对每个候选逐项打勾，任何一项“否”都先别导入：

| 项 | 判据 | 不合格时 |
|---|---|---|
| 叙事支持 | 画面能完成本场任务：证据支持结论，意境素材承接情绪与上下段；不能仅凭题材相近采用 | 换候选或改载体 |
| 动作完整 | 建立、动作、结果都在可用窗口内 | 换片段；不要靠剪辑补因果 |
| 动作与运镜 | 所需动作在使用窗口内清晰可辨。叙事需要相机运动时，另外核对视差与空间揭示 | 调整入出点、换镜头或改载体 |
| 内部连续 | 没有突然切镜、遮挡、黑帧、无关字幕 | 缩窗口或换片段 |
| 原生尺寸 | 够实际显示；放大后不糊 | 换高清件或降为局部/示意 |
| 水印与烧录 | 台标、烧录字幕、素材自带文字不干扰构图 | 换件；不移除来源标记 |
| 裁切后构图 | 主体、动作路径、必要文字、字幕空间都还在 | 调整布局或换件 |
| 原声 | 环境声/对白是否有用、是否有权使用 | 默认不用原声，单独判断 |
| 使用限制 | 只有权利人明确禁止当前用途才换件；平台服务条款、登录墙与付费墙不算禁止，只记风险 | 权利人明确禁止就换件；其余情况直接采用 |

### 用接触表看“完整过程”

```powershell
# 视频：给建立、动作、结果附近的时刻
uv run m2v assets contact-sheet --input assets/downloads/clip.mp4 --times 0,2.5,6,9 --columns 4

# 图片候选：按传入顺序拼一张表
uv run m2v assets contact-sheet --input a.jpg --input b.jpg --input c.jpg --columns 3
```

输出一张带序号的 PNG 和同名 JSON 索引（第几格对应第几秒/哪个文件）。先看整张表判断动作是否完整，再按有序帧与帧差/场景切分核对可疑格。**静帧不能证明动作连续**；接触表只用来快速筛候选，采用前须核对覆盖实际窗口的有序帧与切分。

## 4.1 人物不设默认限制

可辨认人物、肖像、正脸或人物主导构图都可以直接作为主体，不再默认回避，也不需要记录人物例外。是否使用人物按表达需要决定；用户另有要求时从其要求。

## 5. 采用政策与署名

素材与使用相关的一切从宽。只有**权利人明确禁止当前用途**时才不用；平台服务条款、登录墙、付费墙与反爬限制都不算禁止，只作为风险记录。社交媒体截图、引用其他图文或音视频都可以直接使用，引用不设时长或比例上限；无需逐件征求确认，也无需以取得明确授权为前提。原始许可和采用依据分开保存，不能把「未发现禁止」写成「已获授权」。

| 检查结果 | `usage.status` | 制作处理 | 程序处理 |
|---|---|---|---|
| 明确允许当前用途 | `explicit-allowed` | 保存依据并采用 | 通过 |
| 未发现明确禁止（默认） | `no-explicit-restriction` | 直接采用 | 提示，不阻断 |
| 使用条件未满足 | `conditional` | 条件本身构成明确禁止时按 `prohibited` 处理，其余记风险后继续采用 | 提示，不阻断 |
| 权利人明确禁止当前用途 | `prohibited` | 更换素材 | 阻断 |
| 尚未检查 | `not-checked` | 按从宽政策直接采用 | 提示，不阻断 |

`usage` 缺省即为 `no-explicit-restriction`，不再要求 `evidenceUrl`、`checkedAt` 或 `note`。许可未知只提示；非空许可文字也不自动代表可用，明确禁止应登记到 `usage`。程序不自动解释自然语言条款。

CC BY 的署名、CC BY-SA 的同许可条件及仅编辑、非商业、禁止改编等限制都不再默认阻断：构成「明确禁止当前用途」的按 `prohibited` 处理，其余记风险后照用。音乐音效、字体、地图和软件依赖仍执行各自专用契约。

- 普通人物照片和视频直接出画，采访近景、人物群像和活动配图默认无角标、来源条和人物下标。若图片或视频的拍摄时间、地点、事件或与当前现场的关系需要解释才容易看懂，加小字「资料画面」，并补写必要的实际年份或场合。逐镜出处、拍摄年份和拍摄场合保存在作品台账。叙事日期和原帖时间按内容需要呈现。
- 照片、实拍、采访、新闻画面、产品录屏等普通配图默认省略画面署名，发布说明也默认省略逐项罗列。完整作者、链接、日期与许可保存在素材台账和 `SOURCES.md`。
- 法院文书、政府文件、官方统计等原件作为关键证据时，在对应窗口用可读小字标发布机构或文件名，必要时加日期或编号。原件自带清晰标识即可。转引关键证据时保留原始机构，已知转引路径记在台账。直接采用当事人发言或陈述时说明发言者，例如「马斯克的指控」「据 OpenAI 披露」。
- 成片默认以正文收束。许可条件或用户明确要求署名时，按实际要求保留必要文字，选用符合条件的画面位置或发布说明。
- 裁切、去色、暗化都算改动；条件要求注明改动时尽量保留，未保留就记风险。
- 图库素材用于公司、产品或产业段落时，仅在画面可能被误认为真实事件、公司自有产线或具体型号时，用最小必要的小字标「示意」；其余情况不默认添加。
- 来源页和适用条款的检查结论留在材料中；不伪造作者、许可或检查记录。

### 5.1 社媒截图与引用媒体

引用当事人的社媒发言时，优先采用 X／Twitter 等平台的原帖截图。原页无法直接截图时，可使用平台官方嵌入渲染的同一帖文。截图保留发帖账号、相关原文、发帖时间和理解回复所需的上下文；裁切与高亮保留原意，必要时留一张完整截图供复核。原件不可取得时，使用可追溯的转引；关键证据与当事人观点按上节标明原始机构或发言者。

社媒截图登记 `sourceType: "social-screenshot"`，可填 `platform`、`postUrl`、`postedAt`、`capturedAt`、`risk` 与 `riskNotes`；引用其他作品登记 `sourceType: "quoted-media"`，可填 `quotedWork`（标题、作者、平台、链接、时长）。两类都按从宽政策直接采用，平台条款只记风险；可选字段用于追溯，不填也不阻断。

公开署名按上节处理。完整来源进作品台账和 `SOURCES.md`。

## 6. 导入与台账

导入清单和字段要求见[媒体进入作品的唯一路径](article-media-and-sound.md#媒体进入作品的唯一路径)。最小清单：

```json
{
  "schemaVersion": 1,
  "assets": [
    {"id": "haymarket-1886", "kind": "image",
     "localPath": "assets/downloads/haymarket-1886.jpg",
     "sourceUrl": "https://commons.wikimedia.org/wiki/File:HaymarketRiot-Harpers.jpg",
     "author": "Thure de Thulstrup", "license": "Public domain",
     "sourceType": "open-library", "publisher": "Wikimedia Commons",
     "description": "历史事件图像原件"}
  ]
}
```

```json
{
  "schemaVersion": 1,
  "assets": [
    {"id": "x-post-2026-03", "kind": "image",
     "localPath": "assets/downloads/x-post.png",
     "sourceUrl": "https://x.com/example/status/1",
     "sourceType": "social-screenshot", "publisher": "X", "author": "@example",
     "license": "未知", "platform": "X", "postUrl": "https://x.com/example/status/1",
     "postedAt": "2026-03-01", "capturedAt": "2026-11-14",
     "risk": "medium", "riskNotes": "平台条款只记风险，不阻断采用"}
  ]
}
```

```powershell
uv run m2v author assets import --project videos/<类型>/<slug> --manifest videos/<类型>/<slug>/assets/import-manifest.json
uv run m2v assets report --project videos/<类型>/<slug>
```

`--manifest` 路径相对当前 shell 工作目录；清单内 `localPath` 默认相对作品目录，显式 `--base` 时相对该基准。上例在仓库根执行，避免把清单路径误当成作品内相对路径。

`report` 交叉核对三处：`assets/media-sources.json`、`scenes/` 里的 `useMediaAsset` 引用、`SOURCES.md` 的素材表。读法：

| 输出 | 含义 | 怎么修 |
|---|---|---|
| `used-not-registered`（错误） | 场景用了未登记 ID | 补 manifest 后重新 import |
| `missing-file` / `sha-mismatch`（错误） | 文件缺失或被改 | 重新 import，不要手改摘要 |
| `license-unknown` / `usage-not-checked`（警告） | 原始许可未知 / 显式标为未核实 | 如实保留未知，按从宽政策继续制作 |
| `usage-no-explicit-restriction`（提示） | 按默认从宽政策采用 | 无需补充依据，继续制作 |
| `usage-conditions-unmet`（警告） | 适用条件未满足 | 记入风险后继续采用；构成明确禁止时改用 `prohibited` |
| `usage-prohibited`（错误） | 权利人明确禁止当前用途 | 换件 |
| `invalid-usage`（错误） | 状态、依据、日期或片段窗口无效 | 修正清单并重导 |
| `unused`（警告） | 登记了但没引用 | 预留可忽略；否则删记录或补用 |
| `sources-missing`（警告） | `SOURCES.md` 素材表没写 | 补表 |
| `dynamic-usage`（警告） | 存在变量调用 `useMediaAsset(id)` | 人工确认未引用清单 |

`report` 是制作期台账，**不替代** `prepare` 和 `assets audit`：三者共用采用政策；prepare 仍阻断技术不一致与明确禁止，`assets audit` 仍绑定准备指纹。

原生采集的来源扫描区分`useMediaAsset`函数声明与实际调用：声明本身不触发动态资源的保守绑定，变量参数的真实调用仍保守绑定。JPEG／PNG／WEBP贴图使用Pillow验证结构并完整解码，损坏或不支持的格式明确失败；视频仍走视频探测与解码路径，不以图片尺寸读取代替完整有效性校验。

### Pexels 公开媒体直链

从 Pexels 素材页选定图片或视频，分别把文件下载地址填入 `mediaUrl`，把素材详情页地址填入 `sourceUrl`。在详情页核对作者和许可，按本次用途检查 [Pexels 许可](https://www.pexels.com/license/) 和[服务条款](https://www.pexels.com/terms-of-service/)。清单中 `sourceType` 填 `stock`，`publisher` 填 `Pexels`。下面是图片导入示例，实际使用时按详情页填写作者及许可核查结果。

```json
{
  "schemaVersion": 1,
  "assets": [
    {
      "id": "pexels-landscape",
      "kind": "image",
      "mediaUrl": "https://images.pexels.com/photos/417074/pexels-photo-417074.jpeg?w=640",
      "sourceUrl": "https://www.pexels.com/photo/417074/",
      "sourceType": "stock",
      "publisher": "Pexels",
      "author": "未知",
      "license": "Pexels License (https://www.pexels.com/license/)",
      "usage": {"status": "not-checked"}
    }
  ]
}
```

保存为导入清单后执行上面的 `m2v author assets import`，命令会直接下载文件，无需 API Key。视频使用 `kind: "video"` 和对应的公开 MP4 直链。若直链失效，可在官网重新取得公开下载地址，或下载文件后通过 `localPath` 导入。逐项选材并保留来源记录，遵守 Pexels 对批量或系统性复制的限制。

### 完整工作层：发现、获取、索引、检索、预览、选择

`import` 仍是进入作品的唯一正式路径；下面九个工作流用于在导入前把来源、媒体字节、时间窗口和观察依据分开追溯。工作根默认 `<project>/outputs/materials/`，无作品时显式 `--workspace`；命令统一挂在 `m2v author assets` 下并支持 `--json`。

| 工作流 | 最小用法 | 作用与边界 |
|---|---|---|
| `discover` | `--request 需求.json` 或重复 `--query`，`--provider commons/nasa/archive/pixabay/youtube/bilibili` | 只取来源候选；零命中不等于网络失败，失败逐源报告；不下载视频 |
| `fetch` | `--source ID`、`--url`、`--local FILE`，可选 `--range 0-8` | 受控下载、实测解码并发布；区间请求先完整取得再本地精裁，不伪造源原点 |
| `index` | `--media ID --channel captions/asr/ocr/shots/frames/text/visual` | 只读本地媒体与本地模型；缺字幕/章节可 `--tolerate-missing` 记为 skipped |
| `find` | `--query "中文对象动作"` 或 `--requirement`，`--channel lexical/text/visual/metadata` | 只查询现有有效索引，自动获取或建索引一律不做；分数只用于排序 |
| `preview` | `--candidates find.json --out NAME` | 逐候选接触表、短预览与静态 HTML；HTML 不执行脚本、只引用本地相对文件 |
| `select` | `--candidates find.json --index 1 --rationale/--purpose/--operator` | 解码精裁，显式 fps/音频/CRF；显式 `--import 作品 --asset-id` 才改作品 |
| `library` | `scan --dir`、`verify`、`stats`、`cleanup-plan`、`cleanup-apply --digest` | 只处理显式目录；同字节共享内容对象但来源独立；清理先计划后执行 |
| `models` | `list`、`prepare --name whisper-small`、`verify` | prepare 才联网；固定 revision/摘要/许可，缺模型明确失败 |
| `doctor` | `--models DIR` | 只读报告工具、设备、运行库、模型与凭据存在性，不安装、不下载、不泄露 Key |

模型能力按需安装，不进入作品运行时：

```powershell
uv sync --extra index        # 或分别 --extra asr / ocr / semantic / vision / scenes
uv run m2v author assets models prepare --models outputs/materials/models
uv run m2v author assets models verify --models outputs/materials/models
```

模型文件存在不等于可读取或可推理；先用 `doctor` 检查依赖，再用 `models verify` 校验内容，最后实际执行索引。本机恢复与短样本实测见[推理环境验证记录](../../../../docs/material-runtime-readiness.md)；恢复依赖使用 `uv sync --locked --extra index`。

操作要点：

- 先 `discover`/`fetch` 建立来源与媒体，再 `index`；`find` 不会补建索引。语义通道需要显式 `--models`，缺失时报告 `model-missing` 并给出 prepare 入口。
- 中文词面用字符 n-gram；文本语义用 E5 的 `query:`/`passage:` 前缀；视觉用 SigLIP 2 固定长度 padding。语义命中低于校准阈值不参与融合；RRF 融合只改变排序，不把分数解释为概率、身份或动作已完成。
- 一次 `find` 对同一通道的查询与背景描述只编码一批，不按媒体重复；完整模型空间或向量行不匹配的索引先排除。同图无时间多通道证据合为一项，视频无定位元数据不被混入有定位时间窗口。冷热耗时与逐站状态见[改进实测](../../../../docs/material-library-improvements.md)，单次冷启动仍包含模型加载与摘要核验。
- 文本索引默认也纳入来源标题与描述，保留原文并标为 metadata，无字幕图片同样可建；该依据没有逐帧位置，不把它当成字幕或可直接精裁的时间窗口。语义检索同时比较通用描述/测试画面背景，按版本化校准策略排除弱证据；结果可以为空，不能为凑 Top-K 降低门槛。
- 字幕、转录、OCR 分别标记 `manual/automatic/local/asr` 与对齐状态；黑场/纯色低对比度采样帧不进入视觉证据；切镜是候选边界，不是动作起止。
- 帧预算按完整时间轴分布分配，OCR/视觉采用更小预算时也分布选择；索引参数及警告记录策略和实际范围。覆盖前中后段不代表所有短动作都被采到；单帧只选中部代表点。
- 选择输出与导入凭据：作品内 `assets/materials/receipts/`、正式登记仍在 `assets/media-sources.json`。作品移走后 `verify_project_media` 只依赖作品内文件，不读取共享库。
- 精裁起点按真实源 PTS 测量并换算为媒体本地时间；长关键帧间隔不能只探测固定包数，非零视频原点也必须计入。测量失败仍明确拒绝，不手改候选窗口或放宽误差绕过。
- 曲库/素材库清理只删除未被工作文档绑定的对象与暂存残留；不删除作品正式文件、选择输出、索引帧、凭据或唯一源证据。
- `library scan --dir DIR --recursive --max-files 500` 逐项遍历并保存增量状态；复用项不占新的获取预算，`hasMore` 为真时重复同一命令继续。源字节变化或对象失效会重采，坏件独立报告；内容未变化的失败记录默认跳过实际重试，需重试时显式 `--retry-failed`。返回码 1 为部分成功、2 为全部失败。诊断明细最多保留 1000 项，总数另列；扫描仍需读取源摘要，不承诺零 I/O。
- `library annotate --media ID --tag 厨房 --collection 口播实拍 --favorite yes` 持久化组织信息；`--remove-tag`、`--remove-collection`、`--favorite no` 可移除。组织信息不修改媒体、来源或许可；`library list --tag 厨房 --favorites --limit 100 --offset 0` 可筛选和翻页，使用相同 `--workspace`。
- `library similar --similarity 0.96 --max-items 1000` 只比较已有有效视觉向量，按完整模型空间隔离；每个成员直接满足与代表的相似度，不依靠传递关系合并。结果保留媒体/窗口/关键帧，只是建议，缺索引与预算截断如实披露。
- `library browse --workspace WORK --library OTHER_WORK --out outputs/material-library-view` 为显式多库生成本地 `index.html` 与缩略图，可搜索标题/标签/备注、按标签/集合/收藏筛选。每库默认最多 200 件，可用 `--limit`（最多 2000）和命令筛选调整；来源库只读，无自动下载或建索引。页面筛选覆盖本轮显示内容，`find` 的语义查询仍限定所选工作库；旧 `preview` 页面仍不执行脚本。
- 平台能力按实测披露：B站/YouTube 搜索依赖固定版本 yt-dlp，会话/风控可能失败；抖音/小红书/微博/西瓜只接受已知链接；失败时改用网页候选、公开直链或本地文件，不自动启用个人浏览器。

## 7. `SOURCES.md` 素材表模板

```markdown
## 画面素材

以下图片均通过 `m2v author assets import` 登记，原始来源、作者与许可保存在
`assets/media-sources.json`。

| 用途 | 素材 ID | 发布主体与文件页 | 作者 | 原始许可 | 采用依据与检查日期 | 画面处理 |
|---|---|---|---|---|---|---|
| 开场 | `tape-measure` | Wikimedia Commons，https://… | Kulmalukko | CC BY-SA 3.0 | 未核实，待检查当前用途与条件 | 暗化、去色作纹理 |
```

素材来源按[采用政策与署名](#5-采用政策与署名)留在本表。普通素材默认省略公开署名，片尾以正文收束。

## 8. 替换素材后的复核

同一成片里，一段原始视频默认只采用一次。排镜与全片复核时按原片来源核对，裁切、调色、镜像和另存文件都沿用原片身份。需要为明确的叙事回扣、动作对照或前后呼应再次使用时，在 `DESIGN.md` 记录原片、成片时间窗及复用理由，并核对重复出现确实承担相应作用。

模型包中的贴图不能默认按经纬图直接替换：先核对原模型的UV、形体和图集布局。采用专属UV时成对保留几何与原图，登记原包摘要、提取对象及坐标/UV变换；不匹配的微表面贴图应移除或实际解决接缝与切线，不能仅声明“已接入”。

1. 保留旧版材料，再改 manifest 并重新 `import`；
2. 重新 `prepare`，让准备指纹与候选失效；
3. 查裁切与摆位、入出点与时长、动作是否仍完整、字幕与画面文字是否被挡；
4. 查相邻衔接：前后镜头主体、空间关系、色调是否跳；
5. 查声音：原声、音效起点、音床是否仍对；
6. 重跑 `assets report`，确认三处记录同步；
7. 只重做实际过期的证据，不因换一个文件宣称其他证据全部有效。

## 9. 停止条件与常见错误

满足任一条件就停：

- 找到满足评估卡的候选；
- 换过检索方向仍没有合格候选 → 按载体规则改用代码或图片，并记录回退原因；
- 证据型内容拿不到对应原件 → 改表达或缩短，不用图库/代码伪造证据；
- 已发现权利人明确禁止当前用途 → 换件；其余情况一律从宽采用。

| 常见错误 | 替代做法 |
|---|---|
| 按旁白名词贴无关空镜 | 回到本场任务，选择辅助内容或承接情绪的片段；意境选材见[观点旁白与意境素材](visual-material-selection.md#观点旁白与意境素材) |
| 只看缩略图就导入 | 打开来源页与实际媒体，用接触表看完整窗口 |
| 用静帧推拉伪装动作 | 用真实视频或代码动画 |
| 把图库产线当某公司实录 | 标「示意」，或换真实材料 |
| 把明确禁止写成可用 | 发现权利人明确禁止时改用 `prohibited` 并换件 |
| 只改 `media-sources.json` 不重导 | 重新 import，让摘要与文件一致 |
| 换素材不重跑 prepare | 重新 prepare 并重做受影响证据 |
