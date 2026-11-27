## 背景

`catalog.json` 已集中五类身份和材料入口。当前主项目和独立运行时均拒绝旧 `project.style`。作品持有场景、字幕、依赖和准备产物。现有评审支持盲审后展示参考、显式改靶、失败闭环和当前候选摘要绑定，可用这些入口承载风格约束。现状及外部证据见 [research.md](research.md)。

## 1. 默认值和数据形状

类型目录 v4 每项新增 `defaultVisualStyle: {id, revision, spec}`。映射仅在目录源中维护，生成独立模板所用目录、类型表和说明。参数和参考的权威放在实现阶段新增的 `src/m2v/type_system/visual_styles/<id>/<revision>.json`。每个规范含 `id`、`revision`、`displayName`、`palette`、`typography`、`layout`、`graphics`、`motion`、`density`、`banned`、`benchmarks`。参考条目含 `id`、`role`、`url`、证据类型、时间范围或图片标识及预期 SHA-256。仅登记五个默认规范，发布修订不可原地改写。新增规范由后续显式项目更新采用，已初始化的工程按自己的快照运行。

`m2v init --type ... --project ...` 从目录取默认值，复制规范到作品 `design/visual-styles/`、计算原文件字节的 SHA-256，并从同一规范生成对应类型最小开场参数。静态模板占位采用 `text-motion` 的真实默认，同一初始化路径按实际类型重建清单与开场。作品带有随模板发布的默认索引（五类的 ID、修订、SHA-256），用于校验默认来源。只分发本作品实际使用的完整本地规范。下面是一个示例，哈希用占位值。

```json
{
  "schemaVersion": 4,
  "type": "data-evolution",
  "visualStyle": {
    "default": {
      "id": "apple-keynote-presentation",
      "revision": 1,
      "spec": "design/visual-styles/apple-keynote-presentation.1.json",
      "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    },
    "overrides": []
  }
}
```

作品 JSON 负责选择和绑定，机器规范负责规则，不在 Markdown 或分镜中重复可执行数值。用现有本地引用边界拒绝绝对路径、越界、符号链接逃逸和网络规范；离线核对快照与项目捆绑的索引。参考媒体用于研究及对照，遵循既有许可、摘要和封存规则，出片不读取它们。默认的参考缺证以 `insufficient` 进入验收，预演和取证仍可运行。类型、目录和场景路由继续由现有五类决定。

执行值集中于作品自有的单一参数来源。同一作品的共享 CSS 可由本地规范生成一个无条件的 `@theme static`，生成结果在校验时核对，源场景继续按现有的 `var(--m2v-*)`／`var(--fig-*)` 读取。单场覆盖由该场显式引入自己用到的本地值，全片覆盖以作品本地实现切换；各自只定义一次。React、SVG 或三维代码显式消费所需值。作用域属性一旦漏挂会导致变量静默回退，故继续拒绝 `data-m2v-preset`、`data-m2v-theme`、`data-m2v-style-pack`、`themes.json` 与相应旧运行时解析。`visualStyle` 与设计文档本身当前均不渲染，画面由本地代码消费已落地的值。

## 2. 显式覆盖和基准

原话明确指定名称、目标媒体或明确同意一个具名且说明范围的提议后，才在 `visualStyle.overrides[]` 写入一条。每条包含：

- `target` 使用同形的 `{id, revision, spec, sha256}`。具名发布规范可以复用；其他目标在作品内形成完整、可检验的本地规范。只指定配色等某维时，目标规范继承默认其余规则并明确变更维度，检查差异是否只落在授权范围。整体仍用原固定参考，除非授权明确改变。
- `scope` 为 `{"kind":"film"}` 或 `{"kind":"scenes","sceneIds":["opening"]}`，另用 `dimensions` 表示全套或具体维度。未限制的整体指令归全片。场景 ID 必须在现有分镜中，覆盖仅允许不重叠场景集合，唯一全片覆盖与场景覆盖互斥。跨场转场分别核对两端及接续。
- `authorization` 为 `{instruction, instructedAt, sourceRef}`，原话逐字，时间用带时区 ISO 8601，来源记录可复核的消息／文件位置或内部记录引用。公开示例只使用可归档文本，不写私密会话。工具核对结构、范围、引用和摘要。总代理核对确系用户所说，独立对照核对转换忠实性，文件格式不能证明发言者身份。

默认项目无风格选择参数。用户说「更高级」「多做几个」时可以比较同一风格下的构图或机制，助手不能更改家族、调低阈值或换整体标杆。规则需要放宽时明确记录用户指令并生成新目标；只在有此前已绑定失败的场合用现有 `m2v review retarget --file` 保留原失败、用户授权和新包。普通改进沿原目标复查，媒体字节相同也不得复用目标变化的通过。盲看输入继续隔离目标文件、授权和作者理由；封存后提供同轮对照的有效规范、实际参考、各帧职责和中性条件。

## 3. 机检分层与入口

| 入口／证据 | 明确校验 | 失败与证据边界 |
| --- | --- | --- |
| `m2v types`、`m2v init`、`m2v validate`、本地 `validate` 和准备入口 | 五个映射、规范结构、必填 ID、快照摘要、本地路径、覆盖互斥和 scene ID、参数白名单、缺失字体、受控源码 AST 中的禁用 CSS 选择器、调用或取值 | 同步诊断规则与位置。扫描解析本地场景和直接／递归样式依赖，排除注释、纹理、资源源码和锁文件中的字符串。动态值由浏览器或适用采样检查 |
| 本地采集及 `m2v lookdev` 证据 | 用同一工程时钟读取关键对象的实际 computed style、加载的字型、文字框、静态可测区域、事件绑定和代表状态。关键数据组件输出对象 ID、单位、值、尺度、基线和实际使用的缓动/起止帧 | 同源组件或 DOM/SVG 读取；Canvas/WebGL 由作品探针返回有界角色、几何/投影与状态，结合实际取帧交叉验证。缺必须角色、探针或样本记未验证；作者自报值不能单独充当实绘证据 |
| 本地 `qa`、`m2v qa` | 复用 `qa_inspection.sample_indices/extract_sequence` 和正式窗口取样，覆盖每场稳定态及适用进入／临界／结果，记录帧号、场景 ID、参考和规范摘要。检查文本字号/权重、网格锚点及安全区、色板和强调色计数、运动白名单、标签／基线等 | 采集原始帧在已登记的纯色 ROI 内部按 sRGB 比对，跳过抗锯齿边缘，平坦区域压缩成片比对初值为每通道 ±8，最终由本地固定测试片校准后登记。比较同输入、同帧、同尺寸和同一编码条件，外部标杆不做像素相等检查。实拍、材质、字幕和阴影按其既有职责处理 |
| 正式评审和 `m2v status` | 读取当前 QA 报告和参考绑定，核对独立盲审、同轮目标对照、适用过程和整片通过 | 合成候选允许先生成。风格 `fail` 或 `insufficient`、旧签名、参考缺失或独立评审失败均无法报告正式完成。无适用项须有可验证的规则适用依据 |

图文的阅读推进、数据是否误导、隐喻因果、三维空间连贯、纪录蒙太奇是否暗示错误事实、参考的艺术完成度与同族判断由独立评审观察。机器测量报告不得提供审美结论。原尺寸核完成度，小屏核主体和关键信息；固定整体参考负责整体效果，专项负责指定对象与证据。色板通过且画面普通仍可独立否决。具体判据改为「生效风格与世界级完成度」。数据作品以指定的 Keynote 视觉语言和正式基准评审，Apple 通用官网继续只可用作通用工艺参照，不能替其他四类定风格。

### 实施文件与命令清单

- 类型／初始化／主项目校验 6 处。修改 `src/m2v/type_system/catalog.json`、`src/m2v/type_system/catalog.py`、`src/m2v/core/project.py`、`src/m2v/standalone/scaffold.py`、`src/m2v/cli.py`，新增 `src/m2v/type_system/visual_styles/`。主项目只验证清单形状、分发完整性和委托结果。
- 独立校验与 QA 7 处。以 `templates/standalone/runtime/python/film_runtime/` 为根，修改 `catalog.py`、`core/project.py`、`cli.py`、`engine/qa.py`、`engine/qa_inspection.py`、`types/scene_film/code_scenes/capture.py`，新增 `core/visual_style.py`。同步本地 `project.json`、`DESIGN.md`、`design/`、`scenes/opening.tsx`、按需的本地样式与五例代码。复用 `core/schema.py`、`core/validate.py` 的既有校验模式，文件本身无需新规则。主项目 `engine/output_validation.py` 继续只检查成片文件完整性。
- 评审与完成 5 处。修改 `src/m2v/production/` 的 `review_tasks.py`、`reviews.py`、`film_review.py`、`ledger.py`，以及分发类型列表、校验和委托的 `src/m2v/commands.py`。核对现有完成调用方。沿用 `m2v review pack`、`review import`、`review retarget --file`、`m2v status`。`validate`、`lookdev`、`qa` 输出增加风格诊断，无需新命令。
- Skill 18 处。主 `SKILL.md` 及 `references/` 下的 `stage-research.md`、`scene-design.md`、`stage-design.md`、`design-samples.md`、`production-workflow.md`、`video-revision.md`、`reference-video-analysis.md`、`review-contract.md`、`review-protocol.md`、`subagent-review.md`、`visual-review-rubric.md` 改入口、角色和证据。`paths.md`、`prepared-and-subtitles.md`、`building-construction-video.md`、`financial-timeseries-video.md`、`vehicle-showcase-video.md` 同步版本引用。`visual-material-selection.md` 的镜头一致性补充生效风格链接。同步 `README.md`、`ARCHITECTURE.md`、`docs/reference/{README,project-model}.md`、`openspec/config.yaml`、模板 `RESEARCH.md` 和主规格 Purpose 中过时的范围表述。
- 定向测试覆盖 12 个文件。计划修改 `tests/common/{test_type_catalog,test_schema,test_qa_inspection,test_review_targets,test_media_reviews,test_film_review,test_guidance_routes}.py`、`tests/standalone/{test_scaffold,test_execution_contract}.py`、`tests/works/examples/test_examples_v9.py`，新增 `tests/common/test_visual_style.py`。用现有 `tests/common/test_frames_subtitle_style.py` 做柔光回归，如有必要同步 v4 夹具。共享模板镜像测试或夹具以项目全局搜索确认并同步。

## 4. 运行、评审与版本边界

升级 `project.json` 和类型目录 `schemaVersion` 至 4，准备记录 `contractVersion` 至 4。将规范副本和授权纳入材料输入及准备指纹，参考摘要进评审目标绑定，QA 产物继续绑定视频摘要。同步所有读写者、旧版提示、示例 manifests、结构化来源说明、脱库夹具、管理协议对交付结果的理解和 provenance 引用。检查准备消费者，包括本地 direct CLI、主项目委托、Vite/Remotion 启动、缓存、预演、样品、评审、QA 和状态。沿既有 `prepare` 生成新记录。明确拒绝旧记录作为当前输入，旧历史报告只按其原版本验证。

`storyboard.json` 保持 v9：时间轴、场景 ID、事件、转场、结构化来源以及合成字段均沿用。授权范围读取已有 scene ID，实际动作仍由已有场景源码与分镜各自负责。QA 新字段随准备输入或 QA 报告携带，不另造分镜事件协议。评审请求／包版本继续使用现有 v4，利用已绑定的参考和条件加可复核的规范身份及范围，当前完成判定拒绝漏绑；历史按现有语义只读。在试制包建立时只读取作品的有效 `visualStyle`、本地规范和试制场景标识，不新增对 DESIGN.md 或正式准备的依赖。合成成片仍走原本的唯一渲染链路。

### 否决的备选

| 备选 | 取舍 |
| --- | --- |
| 只在 Skill 或 DESIGN.md 写风格名 | 无法证明初始默认、授权与评审所用版本相同 |
| 只在类型目录按运行时实时映射 | 目录一改会改写既有工程目标，脱库也无法重现 |
| 复活旧 `project.style`、`m2v styles`、可自由选择的风格包，或用 DOM 属性切换 | 会重新提供自选入口，并复现漏挂属性的静默回退 |
| 在每个分镜或场景重复写全片默认 | 重复身份，易与主清单冲突。场景只按既有标识解析覆盖范围 |
| 像素匹配外部作品、给审美打分 | 缺少同内容输入和可比基线，易放过工艺和表达问题 |

## 5. 一次性迁移

1. 冻结确认后的规范与外部参考证据，落实五类起步、双入口、失败门禁及参考绑定。按明确内容根、现有交付和可编辑材料建立唯一清册。当前在仓库 `videos/<type>/<slug>/` 的两级目录查到 17 份 `project.json`，其中 6 份 project v3 / 分镜 v9（5 数据、1 图文），另 11 份是旧身份或旧契约。当前未发现环境变量配置的外部内容根，其他路径待明确后盘点。进一步核对可重复作品、活动会话和登记交付。
2. 五部示例逐个重编排，保住事实、场次、时间轴、必要展示和现有音轨契约。复利换为 Keynote 明度、尺度和图形构造，保留本金归塔逻辑、用户指定柱增长、原声与双语字幕。竖屏市值榜用 Keynote 深底与平面数据标记重做榜首交接，保留全部名次、平台安全区与静音。运气例把球、命中和因果改为几何矢量语法，红金语义用规范的两个强调角色校准。太阳系保留连续空间、自然材质及主要镜头任务，统一标签、比例和空间提示；纪实例保留档案、事件声音和历史事实，校准证据优先的剪切与标签，保留有叙事职责的纸带。
3. 当前六个 v3 工程纳入一次性工作清册，挨个保留题材、可编辑源与已有明确用户决定，按新契约取证。五个数据项目为 `apple-since-2007`、`china-us-market-cap-top10`、`electricity-generation-race-portrait`、`gdp-1980-present`、`gdp-world-top10-60s`，图文项目为 `material-runtime-check-20261115`。十一份旧工程是六个旧金融源、四个 `general` 和一个旧汽车例。判为现役且有源的逐部重编排到相应类型，旧金融归数据，旧汽车归三维，四个 `general` 按现存场景内容与音画职责定类。确认是退役、重复副本或仅存 MP4 的列为历史或缺源，记录理由和路径，按项目历史契约个别处理，不批量用兼容映射转换，也不宣称已验收。
4. 按项目生产锁准备验收候选。以当前独立评审、技术 QA、完整整片复核和摘要通过后替换成片，再成组清理旧基线、专属旁车、清单、记录副本和源码快照，旧视频基线保留数为 0。保留当前工程、素材、原始研究、评审原件和问题记录。原件缺失注明不可复核。失败或缺资源时保持项目未完成与原交付的实际状态，禁止新版本冒充旧片。忽略的作品与素材继续不纳入 Git。

## 6. 验证及不回归

| 改动 | 定向检查和通过证据 |
| --- | --- |
| 目录和项目 v4 | `test_type_catalog.py` 核五类唯一默认与版本拒绝；`test_scaffold.py` 核初始化一一对应及移出仓库；`test_schema.py`、`test_execution_contract.py` 核旧项目、准备版本和路径失败 |
| 覆盖与机检 | 新 `test_visual_style.py` 核缺授权、时间、重复或不存在范围、错摘要、规则白名单与禁用扫描，亦测伪造声明和实绘不符；`test_qa_inspection.py` 用选定节点核代表帧、过程抽样、稳定态阈值及失败可定位 |
| 评审和改靶 | `test_review_targets.py`、`test_media_reviews.py`、`test_film_review.py` 核已封存目标、盲包隔离、过期诊断、错范围、失败不可绕过及正式完成绑定；用被挑中的代表帧和适用过程独立观察，文件与报告有当前摘要 |
| 示例和指南 | `test_examples_v9.py` 验五例及分镜 v9，分别脱库恢复、校验、准备、短预演和完整技术导出，按既有职责复核受影响画面与过程；临时图文工程覆盖第五类初始化，固定示例清单照旧；`test_guidance_routes.py` 与文档链接和 JSON 样例一并核对 |
| 渲染与素材不回归 | 保持同输入同帧可复现、30/60 fps 原契约、帧序及并行独立、镜头长度及音轨规则、字幕逐帧实绘柔光与字号几何、素材可追溯与采用政策。定点用 `lookdev --det`、`test_frames_subtitle_style.py` 相关节点、解码帧数/顺序、字幕换句和明暗风险帧、素材摘要以及当前输出溯源核证。保持失败样本不报告完成 |

实施验证按影响范围选择。仅在对应测试文件内补必要的媒体或浏览器节点，保留执行清单、版本和前后摘要。正式对照沿现有评审风险和帧/信号证据，不为风格另设轮次。

## 7. 风险与待用户决定

- **确认四个待定默认**。推荐一次确认四个风格族和固定参考方向；Apple Keynote Presentation Style 已按用户决定写入，节奏与色板阈值是待验证的项目取值。
- **确认有历史明显不同美术的作品是否申请保留**。建议五例全部展示各自默认，现役作品按默认迁移。若确需某部存量作品沿用原风格，请明确作品及范围，以授权覆盖办理。已有可追溯并明确适用于当前范围的硬约束照常保存，历史艺术采用记录需要判断其是否由用户明确指定。
- 参考可取得性、屏幕取样假阳性和存量工时属于实施风险。冻结可恢复的官方证据并校验摘要，纯色 ROI 用已知样本校准，按项目锁逐部验收。缺证、缺资源或未分类时如实留在清册，不降低门禁。
