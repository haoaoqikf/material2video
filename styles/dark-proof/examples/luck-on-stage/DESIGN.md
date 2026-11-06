# 运气到底是什么：41 秒示例设计

## 命题与事实边界

圆形上场标记只在尝试、记录和三柱比较中承担对象追踪；文字、概率盘与九格面积由自身变化讲解。观众最终应理解“预期成功次数 = 上场次数 × 单次成功概率”。`E(S)=Np` 是线性期望；单次概率不会因重复上场自动变大，预期值不保证实际命中。红色仅表示示意未中，金色表示示意命中、成功区域或主要结果。

## 2026-11-06 三柱同地面跳跃（当前制作）

旧候选已保存在 `outputs/baselines/0661f8bab0684874a9ac9029c83d0abd/`，SHA-256 为 `dc3a9fbd889c49df09baa71fa8e3846a36f3acb62885ef5ac602d1165533996a`；修改前材料在 `outputs/revision-sources/0661f8bab0684874a9ac9029c83d0abd/`。本轮只重做 20–27 秒三柱场，七场结构、41 秒、三组条件及数学口径保持不变。旧片审核不能证明新跳跃通过。

球底点沿同一地面 y=750 从 1 跳到 3，再从 3 跳到 9。每次先用五帧蓄力，随后用 26 帧同高抛物线完成上升与自然下落；镜头在两次起跳前停稳。球不搭乘柱顶。落地同帧触发压缩、近地闪释、接触音、目标条件与数字，随后对应柱体从共同零基准 y=650 生长；1、3、9 的稳定高度保持 1:3:9。飞行中只预告改变因素，不提前把新条件与旧结果同屏；第二次飞行保留已落定的 30 次、10% 条件直到下一次落地。球心光滴从同一轨迹的历史帧采样，老光滴才受重力下坠；地影只在支撑面上。飞行中从米白转香槟金、再转琥珀金，已发光点保留原色。

先按 22–27 秒逐帧检查球底点、两次弧线、光头中心、颜色、落点和数字读窗，再评审整段及全片。现有 Remotion 插值、spring 与 Popmotion 均已检索；纯帧解析轨迹更适合本场的接触同步与确定性，复用现有 `progress`、`smooth`、`Attempt` 和 `FlightMotes`，不增加依赖。三柱落地闪释仍弱于面积公式主爆。

首次终审指出新条件在球起跳时就出现，而旧柱仍保持约 0.9 秒，构成短时条件与结果错配。原失败观察保存在 `outputs/production/grounded-final-blind-observations.md`，该候选保存在 `outputs/baselines/e0604b19f94c4ecfb4c8b83993f3ac25/`。修订让中段条件仅在首落点出现，第二次飞行继续显示旧条件，到第三落点才切换；量测确认局部第 89/90、149/150 帧前后由旧条件与旧结果同时切为新条件与新结果。独立核心复查、新片 G5/G6 及独立终审均已完成并通过；原失败与短暂闪释歧义仍如实保留在[验证记录](VERIFICATION.md)。

## 历史：2026-11-06 球心光滴与结论去重

本轮受影响窗口为旧版 0–5 秒开场、22–29 秒柱图、12–15 秒桥段与39–45 秒结尾。旧候选 SHA-256 为 `0DBD7A63BABF6A5879C9D78A235CA648F5E6288733C90F86042AB7D1817FBB1E`，候选基线为 `outputs/baselines/42b951a5aa244cc2afe8f23f3c4ae96c/`，修改前材料在同 ID 的 `outputs/revision-sources/` 下。旧评审只说明旧片状态，不能证明本轮效果。

新版维持七场和原数学口径；桥段从 90 帧缩至 30 帧，结尾从 180 帧缩至 120 帧，全长 1230 帧。记录段结束的 30 次和末行横线在桥段延伸并卷成概率盘入口，桥段不再重复完整口号。公式 `30 × 30% = 9` 的两个因素分别触发“多上场”和“把每一次做好”，仅在结尾说一次，最后留出完整静读。

开场与柱图的球体中心就是光滴的头部坐标；离散光点记录球体过去的实际位置，越旧越下坠、变暗，去掉连续锥形尾。柱图历史位置与当前球体共用世界轨迹及当前镜头投影，1/3/9 阶段从米白、香槟金递进到琥珀金，飞行中连续过色，已发出的光滴保留原色。球在接触后仍可有短暂余光，但亮核不能从球心漂开。参考借鉴与外部依赖取舍沿用上一轮已登记研究，不引入新的 WebGL 合成。

柱图纯时间采集改为 210 帧单块、单 worker。双 worker、30 帧块的首次样片在 90 帧边界出现一侧 SVG 文字整组未显的跨进程差异（PSNR 59.31 dB），与球体位置计算无关；单块采集仍保留纯时间正反探针，完整场景重采开销增加，但避免把不完整文字帧写进复用缓存。该采集限制只作用于本示例的柱图，其他场景与风格包契约不变。

首轮独立盲审发现两个具体缺陷并已修复：隔离包误从旧检查点目录收进超出新版桥段时长的静帧，后续仅从**当前 G4 报告登记的帧**取证并限制帧号；面积段标签取整而结果使用内部小数，现以画面显示的次数和概率计算预期值，230 个可见采样帧逐项核对通过。原失败观察保留在输出记录中，新包由另一名独立代理重新盲审。

先预演开场、短接棒、柱图两次跳跃、公式到结尾及手机尺寸；然后做 G5 全片和 G6 独立终审。动态复核必须覆盖球心同步、光滴下坠、三次色阶、只出现一次的结论及至少两秒稳定留读。

## 历史：2026-11-06 形象修订

用户明确要求全片不再使用旧版尖顶角色。保持 45 秒、七场、原有文案、数学口径、红金结果语义及事件声音；形象本身是可调整的历史设计选择。旧版 0–45 秒七场均使用同一个形象，因此从制作与迭代阶段重入，统一改成实心圆形上场标记，仍沿路径进入、随结果变色并在落点短暂压扁。圆的无方向轮廓与次数、概率盘及柱形的简洁几何语言一致；不新增装饰或解释文字。

旧版视频 SHA-256 为 `1295107F9C3C084AB8A2375D1DD026B5634ADBE169041F0DDD6EF91B83EDCEFE`，准备指纹为 `4ac5803bf8474e13a0dd59d8ee4aa9fecba16acc11273ecf0defd794677cf172`。比较候选基线为 `outputs/baselines/cbbea26eec7b4144a1ada2c8a6e3481d/`；旧版角色源码副本为 `outputs/revision-sources/cbbea26eec7b4144a1ada2c8a6e3481d/attempt.tsx`。受影响的是七场的主体外观与局部接触范围，原有评审结论仅对应旧版。新候选须检查完整帧序列、手机尺寸和七场之间的形象连续性。

## 全片原则

近黑底、米白主体、金色结果、红色未中。用大字、球的尝试动作及图形自身变化保持注意力。一次只改变一个比较条件；图形和数字来自相同数据，切换后留稳定阅读。球的动作以弧线、接触、压扁和减速落定组织；无球场景用字线、盘弧和面积边缘组织。声音跟随命名事件；光效不盖过必要文字。

## 历史：2026-11-06 去球与光效重制设计

本轮保留七场、45 秒、原数学口径与主要文案。从制作与迭代阶段重入；旧版四处的球误把文字、概率盘和九格面积都变成角色表演，削弱各自的信息任务。12–15 秒桥段、15–22 秒概率盘、29–39 秒面积九格、39–45 秒收束均去掉球；0–12 秒尝试与记录、22–29 秒柱图继续用球追踪“上场”动作。旧成片保存在 `outputs/baselines/5524663f13ed490abcbed5cc20d30d9e/`，修改前材料保存在 `outputs/revision-sources/5524663f13ed490abcbed5cc20d30d9e/`；旧版审核不作本轮通过依据。

视觉令牌沿用 `#08090B` 近黑、`#F3EDDC` 米白、`#F1C64C` 成功金、`#DE3B4B` 未中红和风格包暗线。字体沿用项目中文与数字字体。文字两场以左到右的线条接棒组织“次数→质量”；圆盘用十等分高亮扇段和边界细光指示概率；面积用横向三格、纵向三格的两次增长解释乘法。检视通用模板后删除“每场右上角必须有球”的惯性：这些场景的主角分别是句子、比例边界和九格关系。

| 完整窗口 | 先看与触发 | 动效、阅读和收势 | 失败现象 |
|---|---|---|---|
| 0–5 秒开场 | 球三次尝试；飞行路径先抬后落 | 暖金细光贴着实际轨迹，尾端碎光受重力略向下垂；减速时尾迹缩回。第三次命中亮核快起、扩环和碎光下坠，结果留下 | 直线彗尾、尾迹与球脱节、爆闪盖住“命中” |
| 12–15 秒桥段 | 第一行字引出第二行字 | 第一行底线扫亮后熄到第二行；第二行金线从字下生长，线末收成细环，进入概率盘。没有球和球形光点 | 线条像无关装饰、穿环突然换中心 |
| 15–22 秒概率 | 10% 到 30% 的金区增长 | 金色前沿沿盘弧生长，边界短弧亮核与右侧百分数同步；30%锁定时用一次环形闪释，然后保留稳定读数 | 像累计命中概率、亮点看成球、闪释遮住数值 |
| 22–29 秒三柱 | 球带视线从 1 到 3 到 9 | 柱间飞行补下坠暖光轨；3、9 落定分别给中等和较强的闪释，公式主爆仍最强 | 光轨不随速度收束、三柱共同尺度被光遮没 |
| 29–39 秒面积 | 横向三格再纵向三格 | 起句“次数 × 单次成功概率”自场景起点入场，完整后保留可读窗口；增长前沿依次有薄金扫光；九格完成时矩形边缘向外短闪，公式落定触发全片最强亮核、多层扩环与余光；无球 | 九格被读成实际九次成功、球形光点混入格内、公式或起句不可读 |
| 39–45 秒结尾 | 两句文字复现 | 首句由短线定势；第二句在金线扫过后显现，末端细光停住再退，留足静读。没有球 | 结尾像第三次图表演示、线条抢字 |

强度层级由事件含义决定：失败接触仍短促且偏红；开场命中、概率 30%、三柱 3/9、九格 9 及公式 9 均有可辨的快速亮核和独立衰减的环／碎光，公式仍是唯一全幅主爆。参考视频中金光主要是局部亮核、稀疏大环与随重力下落的余光，不复制角色、数字、音轨或整屏白闪。新增爆闪必须在接触、边界锁定或结果落定后发生，亮核约数帧即退，随后给数字和文字完整阅读窗。

独立样片复核发现开场两句、三柱首句与面积起句的逐字入场占用过多阅读时间。这四句改为八帧横向揭示、六帧淡出，并延长三柱与面积起句窗口；文字内容与数学关系保持一致。其他短字幕继续沿用逐字入场。

依赖判断：已有 `sampleTrail`、`LightTrail`、`Burst`、`ScreenBurstLayer` 和固定种子粒子实现逐帧求值；既有外部后处理库只作用于 WebGL，当前 SVG 场景接入会改变合成和验证范围。因此本例复用现有路径及粒子能力，按事件重编排光层，不新增依赖或共享渲染接口。先看开场飞行／命中、桥段到概率盘、九格到公式及结尾的完整局部窗口，再生成全片候选。

## 上一轮光影编排（历史）

上一轮依据[光影与穿越方案](outputs/reference-analysis.md)制作。该轮基线为 `outputs/baselines/fe166957232b4169996a307ea62ec807/`，旧候选 SHA-256 为 `0AB2FF63A7CD731C22B07E92D810C633C65F5BF74159FA0CDDC56576AF4EBC00`；修改前的场景、分镜和设计记录在同 ID 的 `outputs/revision-sources/` 下。以下段落仅保留历史取舍，当前执行以上述去球与光效重制设计为准。

统一动作是「近身微光与离散金点 → 减速/自然下落 → 接触 → 分级释放 → 余光下坠」。开场删除白色锥形拖尾和漂浮椭圆；失败球下落变暗，红色轻反馈；第三次命中在下落末端释放局部金光。记录30落定只轻点，概率30%锁定用中弱局部环，柱图9落定用中强局部环；面积横纵扩展的接触降为轻反馈，唯一主爆移至37秒公式完整落定。结尾球加速下落、轻压缩、少量余光后安静留读。真实支撑面上才出现接触影，概率标记保持贴着边界。

14.4–15.2秒短穿环沿两幕同一个24帧时间求值：小球聚入金环、环向外扩张与径向碎光产生纵深、中心移到下一场圆盘位置、外环减速并分为十段。字幕不随镜头缩放。前后必须能认回圆环结构，跨切点不得突然换中心；若实际样片不能成立，按已确认备选缩成扩环接棒。三组比较条件及45秒总时长继续由现有分镜表达。

参考《重复》的局部结果释放与44.7–46.8秒空间穿越，证据及外观差值见 `outputs/style-reference.md`。采用亮核快起、金环外扩、碎光独立下坠、结果留读，以及前场动作生成下一场结构；不采用参考角色、岩石、具体数值或音轨。运动以克制的两端平滑移动和加速下坠为主，接触只短促压缩一次。光源固定在球体左上；飞行光点随速度收回，不用持续长尾。

外部方案已检索：现有 `@react-three/postprocessing 3.2.0`（MIT）、`postprocessing 6.39.5`（Zlib）支持Bloom，但只处理WebGL，不能直接给当前SVG图表加光。新增3D合成会扩大依赖和验证范围，本片复用成熟的 `sampleTrail`、`particleField`、`Burst`、`burstField` 与 `ScreenBurstLayer`；作品层仅编排事件、强弱及跨场连续状态，不新增共享组件或渲染契约。

## 历史：45 秒旧版逐场设计

| 时间 | 观看任务 | 画面与衔接 | 失败现象 |
|---|---|---|---|
| 0–5秒 | 失败后继续，建立期待 | 两次未中后命中，角色进入记录 | 路径与结果矛盾，字抢动作 |
| 5–12秒 | 理解每次尝试都计数 | 开场第三次命中接成记录起点，再累积至30；角色随计数起落 | 开场结果与记录脱节，或高潮后读不到30 |
| 12–22秒 | 分清次数与单次概率 | 无球的两句大字由底线转入十等分盘，盘弧从10%展示到30% | 盘区、边界与数字脱节；误写为累计概率 |
| 22–29秒 | 逐项改变条件 | 同零基准三柱先改次数，再改概率 | 同时改两条件或柱高失真 |
| 29–39秒 | 看见乘法结构 | 无球面积横向三倍、纵向三倍，再汇成30×30%=9 | 九格被误当实际九次命中 |
| 39–45秒 | 回到可采取的结论 | 无球文字与底线收束“多上场，把每一次做好” | 遮字或新增概念 |

## 当前材料与审核边界

本目录从 `videos/general/luck-on-stage` 的可编辑材料复制，保留原片的构思与数学口径。原片审核只作历史来源；本示例以自己的准备、成片与[验证记录](VERIFICATION.md)判定。原生和手机尺寸均需复核角色、图表、字幕与过渡。无需照搬复利片的雪球或连续图表形式；两片共享风格，而非分镜。
## 制作合同

```m2v-checkpoints
{
  "version": 2,
  "cycleId": "luck-example-20261106-grounded-bars",
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "reviewPlan": {
    "basis": "本轮41秒三柱重制：球在同一地面两次抛物线跳跃，接触后柱体向上生长；飞行镜头固定且球心光滴同步。开场、桥段和公式按现有结构复核；G5全片检查，G6独立终审。",
    "risks": [
      {
        "id": "light-landing",
        "kind": "core-event",
        "scope": {
          "checkpointIds": [
            "cp-redesign-hook",
            "cp-redesign-ledger",
            "cp-redesign-bars",
            "cp-redesign-area"
          ]
        },
        "reason": "开场与柱图光迹头部锁定球心，历史光滴下坠；柱图同地面跳跃、落地触发生长，颜色随1/3/9逐级变化。",
        "requiredEvidence": [
          "production/checkpoints/cp-redesign-hook/window.mp4",
          "production/checkpoints/cp-redesign-ledger/window.mp4",
          "production/checkpoints/cp-redesign-bars/window.mp4",
          "production/checkpoints/cp-redesign-area/window.mp4"
        ]
      },
      {
        "id": "ring-handoff",
        "kind": "core-event",
        "scope": {
          "checkpointIds": [
            "cp-redesign-bridge",
            "cp-redesign-probability"
          ]
        },
        "reason": "记录30次的末行短接概率盘，24帧穿环跨幕同源，不重复完整结论。",
        "requiredEvidence": [
          "production/checkpoints/cp-redesign-bridge/window.mp4",
          "production/checkpoints/cp-redesign-probability/window.mp4"
        ]
      },
      {
        "id": "light-timing",
        "kind": "structure-timing",
        "scope": {
          "checkpointIds": [
            "cp-redesign-hook",
            "cp-redesign-bridge",
            "cp-redesign-probability",
            "cp-redesign-area",
            "cp-redesign-closing"
          ]
        },
        "reason": "结尾由30与30%的公式因素引出唯一结论，停留可读；所有闪释有可见触发。",
        "requiredEvidence": [
          "g5-contact-liquid.png",
          "production/checkpoints/cp-redesign-area/window.mp4"
        ]
      }
    ]
  },
  "scenes": [
    {
      "id": "hook",
      "durationFrames": 150,
      "shots": [
        {
          "id": "hook-shot",
          "tier": "B",
          "core": true,
          "window": [
            0,
            150
          ],
          "timeStructure": {
            "establish": {
              "window": [
                0,
                12
              ],
              "audience": "片名与门框建立",
              "visible": "片名与门框建立",
              "attention": "圆形标记、落点、文字和当前光环",
              "toleranceFrames": 1,
              "failure": "球突然定住、飞行伪地影、光效无触发来源、跨场中心跳动或遮挡必要文字"
            },
            "change": {
              "window": [
                12,
                90
              ],
              "audience": "两次未中，红色反馈后球自然下落消隐",
              "visible": "两次未中，红色反馈后球自然下落消隐",
              "attention": "圆形标记、落点、文字和当前光环",
              "toleranceFrames": 1,
              "failure": "球突然定住、飞行伪地影、光效无触发来源、跨场中心跳动或遮挡必要文字"
            },
            "reveal": {
              "window": [
                90,
                126
              ],
              "audience": "第三次穿过后顺势下落到落定点",
              "visible": "第三次穿过后顺势下落到落定点",
              "attention": "圆形标记、落点、文字和当前光环",
              "toleranceFrames": 1,
              "failure": "球突然定住、飞行伪地影、光效无触发来源、跨场中心跳动或遮挡必要文字"
            },
            "result": {
              "window": [
                126,
                140
              ],
              "audience": "命中触发局部金环与碎光",
              "visible": "命中触发局部金环与碎光",
              "attention": "圆形标记、落点、文字和当前光环",
              "toleranceFrames": 1,
              "failure": "球突然定住、飞行伪地影、光效无触发来源、跨场中心跳动或遮挡必要文字"
            },
            "hold": {
              "window": [
                140,
                150
              ],
              "audience": "结果继续可读并接入第三次记录",
              "visible": "结果继续可读并接入第三次记录",
              "attention": "圆形标记、落点、文字和当前光环",
              "toleranceFrames": 1,
              "failure": "球突然定住、飞行伪地影、光效无触发来源、跨场中心跳动或遮挡必要文字"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-redesign-hook",
          "shotId": "hook-shot",
          "frame": 130,
          "window": [
            0,
            150
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "这次没中，再来一次",
              "window": [
                18,
                78
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "好运，发生在某次上场",
              "window": [
                90,
                146
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "保证成功",
            "必然成功",
            "十次必成一次"
          ],
          "sampleStep": 1,
          "minEventFrames": 1,
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "1920横屏与393宽实际观察；讲解96px起，不作为跨作品阈值"
          }
        }
      ]
    },
    {
      "id": "ledger",
      "durationFrames": 210,
      "shots": [
        {
          "id": "ledger-shot",
          "tier": "A",
          "core": true,
          "window": [
            0,
            210
          ],
          "timeStructure": {
            "establish": {
              "window": [
                0,
                28
              ],
              "audience": "表格与第3次计数建立",
              "visible": "表格与第3次计数建立",
              "attention": "当前记录、计数及其上方圆形标记",
              "toleranceFrames": 2,
              "failure": "颜色丢失、计数不同步、圆形标记抢字或高速抖动"
            },
            "change": {
              "window": [
                28,
                150
              ],
              "audience": "红金记录滚动，计数与圆形标记节拍联动",
              "visible": "红金记录滚动，计数与圆形标记节拍联动",
              "attention": "当前记录、计数及其上方圆形标记",
              "toleranceFrames": 2,
              "failure": "颜色丢失、计数不同步、圆形标记抢字或高速抖动"
            },
            "reveal": {
              "window": [
                150,
                166
              ],
              "audience": "滚动提前刹车，30落定",
              "visible": "滚动提前刹车，30落定",
              "attention": "当前记录、计数及其上方圆形标记",
              "toleranceFrames": 2,
              "failure": "颜色丢失、计数不同步、圆形标记抢字或高速抖动"
            },
            "result": {
              "window": [
                166,
                192
              ],
              "audience": "圆形标记最后落下并收势",
              "visible": "圆形标记最后落下并收势",
              "attention": "当前记录、计数及其上方圆形标记",
              "toleranceFrames": 2,
              "failure": "颜色丢失、计数不同步、圆形标记抢字或高速抖动"
            },
            "hold": {
              "window": [
                192,
                210
              ],
              "audience": "保留30与结果行供阅读",
              "visible": "保留30与结果行供阅读",
              "attention": "当前记录、计数及其上方圆形标记",
              "toleranceFrames": 2,
              "failure": "颜色丢失、计数不同步、圆形标记抢字或高速抖动"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-redesign-ledger",
          "shotId": "ledger-shot",
          "frame": 190,
          "window": [
            0,
            210
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "先增加上场次数",
              "window": [
                14,
                200
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "保证成功",
            "必然成功",
            "十次必成一次"
          ],
          "sampleStep": 3,
          "minEventFrames": 3,
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "1920横屏与393宽实际观察；讲解96px起，不作为跨作品阈值"
          }
        }
      ]
    },
    {
      "id": "bridge",
      "durationFrames": 30,
      "shots": [
        {
          "id": "bridge-shot",
          "tier": "B",
          "core": true,
          "window": [
            0,
            30
          ],
          "timeStructure": {
            "establish": {
              "window": [
                0,
                6
              ],
              "audience": "记录30次末行留在场内",
              "visible": "记录30次末行留在场内",
              "attention": "记录线、30次与概率盘圆环",
              "toleranceFrames": 1,
              "failure": "重复完整口号、出现小球、线环位置突跳或无法辨认接棒"
            },
            "change": {
              "window": [
                6,
                12
              ],
              "audience": "末行延伸并卷向概率盘入口",
              "visible": "末行延伸并卷向概率盘入口",
              "attention": "记录线、30次与概率盘圆环",
              "toleranceFrames": 1,
              "failure": "重复完整口号、出现小球、线环位置突跳或无法辨认接棒"
            },
            "reveal": {
              "window": [
                12,
                20
              ],
              "audience": "同中心短穿环启动",
              "visible": "同中心短穿环启动",
              "attention": "记录线、30次与概率盘圆环",
              "toleranceFrames": 1,
              "failure": "重复完整口号、出现小球、线环位置突跳或无法辨认接棒"
            },
            "result": {
              "window": [
                20,
                24
              ],
              "audience": "圆环扩展并迁移焦点",
              "visible": "圆环扩展并迁移焦点",
              "attention": "记录线、30次与概率盘圆环",
              "toleranceFrames": 1,
              "failure": "重复完整口号、出现小球、线环位置突跳或无法辨认接棒"
            },
            "hold": {
              "window": [
                24,
                30
              ],
              "audience": "跨切点接入十等分概率盘",
              "visible": "跨切点接入十等分概率盘",
              "attention": "记录线、30次与概率盘圆环",
              "toleranceFrames": 1,
              "failure": "重复完整口号、出现小球、线环位置突跳或无法辨认接棒"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-redesign-bridge",
          "shotId": "bridge-shot",
          "frame": 20,
          "window": [
            0,
            30
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": [
            "保证成功",
            "必然成功",
            "十次必成一次"
          ],
          "sampleStep": 1,
          "minEventFrames": 1,
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "1920横屏与393宽实际观察；讲解96px起，不作为跨作品阈值",
            "allowedOverlaps": [["bridge-record-line", "bridge-ring-seed"]]
          }
        }
      ]
    },
    {
      "id": "probability",
      "durationFrames": 210,
      "shots": [
        {
          "id": "probability-shot",
          "tier": "A",
          "core": true,
          "window": [
            0,
            210
          ],
          "timeStructure": {
            "establish": {
              "window": [
                0,
                36
              ],
              "audience": "穿环出口形成十等分盘，10%成功区与90%未中区建立",
              "visible": "穿环出口形成十等分盘，10%成功区与90%未中区建立",
              "attention": "成功边界、当前概率与起始10%标记",
              "toleranceFrames": 2,
              "failure": "出现小球、比例不符、边界光与数值脱节或单次概率被误读为累计"
            },
            "change": {
              "window": [
                36,
                112
              ],
              "audience": "成功边界扩展，细光沿弧形前沿移动，无球",
              "visible": "成功边界扩展，细光沿弧形前沿移动，无球",
              "attention": "成功边界、当前概率与起始10%标记",
              "toleranceFrames": 2,
              "failure": "出现小球、比例不符、边界光与数值脱节或单次概率被误读为累计"
            },
            "reveal": {
              "window": [
                112,
                140
              ],
              "audience": "30%锁定并显出起点差距",
              "visible": "30%锁定并显出起点差距",
              "attention": "成功边界、当前概率与起始10%标记",
              "toleranceFrames": 2,
              "failure": "出现小球、比例不符、边界光与数值脱节或单次概率被误读为累计"
            },
            "result": {
              "window": [
                140,
                192
              ],
              "audience": "成功和未中比例与数字稳定",
              "visible": "成功和未中比例与数字稳定",
              "attention": "成功边界、当前概率与起始10%标记",
              "toleranceFrames": 2,
              "failure": "出现小球、比例不符、边界光与数值脱节或单次概率被误读为累计"
            },
            "hold": {
              "window": [
                192,
                210
              ],
              "audience": "圆盘和30%稳定，接向三柱比较",
              "visible": "圆盘和30%稳定，接向三柱比较",
              "attention": "成功边界、当前概率与起始10%标记",
              "toleranceFrames": 2,
              "failure": "出现小球、比例不符、边界光与数值脱节或单次概率被误读为累计"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-redesign-probability",
          "shotId": "probability-shot",
          "frame": 190,
          "window": [
            0,
            210
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "让每一次，更有胜算",
              "window": [
                14,
                202
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "保证成功",
            "必然成功",
            "十次必成一次"
          ],
          "sampleStep": 1,
          "minEventFrames": 1,
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "1920横屏与393宽实际观察；讲解96px起，不作为跨作品阈值"
          }
        }
      ]
    },
    {
      "id": "bars",
      "durationFrames": 210,
      "shots": [
        {
          "id": "bars-shot",
          "tier": "A",
          "core": true,
          "window": [
            0,
            210
          ],
          "timeStructure": {
            "establish": {
              "window": [
                0,
                40
              ],
              "audience": "第一组从同一零基线长到1",
              "visible": "第一组从同一零基线长到1",
              "attention": "正在改变的条件及对应柱顶",
              "toleranceFrames": 2,
              "failure": "条件同时变化、稳定柱高失真或没有比较窗口"
            },
            "change": {
              "window": [
                40,
                124
              ],
              "audience": "只改次数，球从同一地面跳到第二组并触发长到3",
              "visible": "球先上升再落到第二组，接触后第二柱长到3",
              "attention": "球的完整弧线、落地反馈与第二柱",
              "toleranceFrames": 2,
              "failure": "条件同时变化、稳定柱高失真或没有比较窗口"
            },
            "reveal": {
              "window": [
                124,
                164
              ],
              "audience": "再改概率，球在同一地面跳到第三组并触发长到9",
              "visible": "球先上升再落到第三组，接触后第三柱长到9",
              "attention": "球的完整弧线、落地反馈与第三柱",
              "toleranceFrames": 2,
              "failure": "条件同时变化、稳定柱高失真或没有比较窗口"
            },
            "result": {
              "window": [
                164,
                180
              ],
              "audience": "三柱同比例定格，结果数字保留",
              "visible": "单个圆形标记停在第三组地面，三柱与结果数字保留",
              "attention": "正在改变的条件及对应柱顶",
              "toleranceFrames": 2,
              "failure": "条件同时变化、稳定柱高失真或没有比较窗口"
            },
            "hold": {
              "window": [
                180,
                210
              ],
              "audience": "同基线同比例完整比较",
              "visible": "同基线同比例完整比较",
              "attention": "正在改变的条件及对应柱顶",
              "toleranceFrames": 2,
              "failure": "条件同时变化、稳定柱高失真或没有比较窗口"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-redesign-bars",
          "shotId": "bars-shot",
          "frame": 190,
          "window": [
            0,
            210
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "先看：10次，每次10%",
              "window": [
                10,
                68
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "只增加次数",
              "window": [
                72,
                122
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "再提高单次概率",
              "window": [
                130,
                206
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "保证成功",
            "必然成功",
            "十次必成一次"
          ],
          "sampleStep": 1,
          "minEventFrames": 1,
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "1920横屏与393宽实际观察；讲解96px起，不作为跨作品阈值",
            "allowedOverlaps": [["attempt-character", "bar-result-0"], ["attempt-character", "bar-result-1"]]
          }
        }
      ]
    },
    {
      "id": "area",
      "durationFrames": 300,
      "shots": [
        {
          "id": "area-shot",
          "tier": "A",
          "core": true,
          "window": [
            0,
            300
          ],
          "timeStructure": {
            "establish": {
              "window": [
                0,
                48
              ],
              "audience": "初始1份面积与10×10%建立",
              "visible": "初始1份面积与10×10%建立",
              "attention": "改变的维度与可数面积",
              "toleranceFrames": 2,
              "failure": "出现小球、面积与数值不符、九格被误读为实际命中或公式挤压阅读"
            },
            "change": {
              "window": [
                48,
                132
              ],
              "audience": "横向变宽3倍，扫光沿矩形前沿推进，得到3份",
              "visible": "横向变宽3倍，扫光沿矩形前沿推进，得到3份",
              "attention": "改变的维度与可数面积",
              "toleranceFrames": 2,
              "failure": "出现小球、面积与数值不符、九格被误读为实际命中或公式挤压阅读"
            },
            "reveal": {
              "window": [
                132,
                194
              ],
              "audience": "纵向变高3倍，扫光沿上边缘推进，九格与9对应",
              "visible": "纵向变高3倍，扫光沿上边缘推进，九格与9对应",
              "attention": "改变的维度与可数面积",
              "toleranceFrames": 2,
              "failure": "出现小球、面积与数值不符、九格被误读为实际命中或公式挤压阅读"
            },
            "result": {
              "window": [
                194,
                240
              ],
              "audience": "九格让位，数值收拢成公式",
              "visible": "九格让位，数值收拢成公式",
              "attention": "改变的维度与可数面积",
              "toleranceFrames": 2,
              "failure": "出现小球、面积与数值不符、九格被误读为实际命中或公式挤压阅读"
            },
            "hold": {
              "window": [
                240,
                300
              ],
              "audience": "公式完整落定后释放全片主光，随后保留30×30%=9稳定阅读",
              "visible": "公式完整落定后释放全片主光，随后保留30×30%=9稳定阅读",
              "attention": "改变的维度与可数面积",
              "toleranceFrames": 2,
              "failure": "出现小球、面积与数值不符、九格被误读为实际命中或公式挤压阅读"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-redesign-area",
          "shotId": "area-shot",
          "frame": 280,
          "window": [
            0,
            300
          ],
          "expected": [],
          "textPlan": [
            {
              "role": "screen-subtitle",
              "text": "次数 × 单次成功概率",
              "window": [
                0,
                60
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "次数变3倍",
              "window": [
                60,
                124
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "概率也变3倍",
              "window": [
                136,
                213
              ]
            },
            {
              "role": "screen-subtitle",
              "text": "预期成功9次",
              "window": [
                242,
                296
              ]
            }
          ],
          "claims": [],
          "forbidden": [
            "保证成功",
            "必然成功",
            "十次必成一次"
          ],
          "sampleStep": 1,
          "minEventFrames": 1,
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "1920横屏与393宽实际观察；讲解96px起，不作为跨作品阈值",
            "allowedOverlaps": [
              [
                "area-model",
                "area-result"
              ]
            ]
          }
        }
      ]
    },
    {
      "id": "closing",
      "durationFrames": 120,
      "shots": [
        {
          "id": "closing-shot",
          "tier": "B",
          "core": false,
          "window": [
            0,
            120
          ],
          "timeStructure": {
            "establish": {
              "window": [
                0,
                12
              ],
              "audience": "接住公式30×30%=9",
              "visible": "接住公式30×30%=9",
              "attention": "公式因素与唯一结论",
              "toleranceFrames": 2,
              "failure": "文字凭空淡入、重复口号、出现小球或稳定阅读不足"
            },
            "change": {
              "window": [
                12,
                24
              ],
              "audience": "30的尝试刻痕引出多上场",
              "visible": "30的尝试刻痕引出多上场",
              "attention": "公式因素与唯一结论",
              "toleranceFrames": 2,
              "failure": "文字凭空淡入、重复口号、出现小球或稳定阅读不足"
            },
            "reveal": {
              "window": [
                24,
                44
              ],
              "audience": "30%的弧段引出把每一次做好",
              "visible": "30%的弧段引出把每一次做好",
              "attention": "公式因素与唯一结论",
              "toleranceFrames": 2,
              "failure": "文字凭空淡入、重复口号、出现小球或稳定阅读不足"
            },
            "result": {
              "window": [
                44,
                52
              ],
              "audience": "数字退去，唯一结论锁定",
              "visible": "数字退去，唯一结论锁定",
              "attention": "公式因素与唯一结论",
              "toleranceFrames": 2,
              "failure": "文字凭空淡入、重复口号、出现小球或稳定阅读不足"
            },
            "hold": {
              "window": [
                52,
                120
              ],
              "audience": "两句完整结论稳定留读",
              "visible": "两句完整结论稳定留读",
              "attention": "公式因素与唯一结论",
              "toleranceFrames": 2,
              "failure": "文字凭空淡入、重复口号、出现小球或稳定阅读不足"
            }
          }
        }
      ],
      "checkpoints": [
        {
          "id": "cp-redesign-closing",
          "shotId": "closing-shot",
          "frame": 100,
          "window": [
            0,
            120
          ],
          "expected": [],
          "textPlan": [],
          "claims": [],
          "forbidden": [
            "保证成功",
            "必然成功",
            "十次必成一次",
            "小球出现在结尾文字旁"
          ],
          "sampleStep": 3,
          "minEventFrames": 3,
          "measurement": {
            "subtitleRoles": [
              "screen-subtitle"
            ],
            "thresholdSource": "1920横屏与393宽实际观察；讲解96px起，不作为跨作品阈值"
          }
        }
      ]
    }
  ]
}
```
