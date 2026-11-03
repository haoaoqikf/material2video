# 建筑建造视频专题

本文定义 `building-construction` 类型的材料与画面契约；行为以 [OpenSpec 规格](../../../../openspec/specs/building-construction-video/spec.md) 为准。

## 材料 v2

- `building.json`：固定 1920×1080 画布与两层框架住宅参数。除开间、层高、墙厚、基础与场地留白外，必须声明：
  - `roof`：`type`（`gable` 坡屋顶或 `flat` 平屋顶）、`height`（脊高或女儿墙高）、`overhang`（檐口外伸）；
  - `stairs`：`side`、`offset`、`width`，决定楼梯与梯井的位置；
  - `openings[]`：每扇门窗的 `floor`、`side`、`offset`、`width`、`height` 与 `sill`（窗台高度）。洞口必须落在所属墙面内，`sill + height` 不得超过层高。
- `construction.json`：60 秒级、30 fps、连续阶段、`shots` 多镜头轨道、`initial` 初始构件与 `steps` 构件级步骤。
  - `stages` 从 0 开始、首尾相接并覆盖全片；
  - `shots` 同样首尾相接、不重叠，每个镜头有 `camera.position`、`target`、`fov`，可选 `to` 做单向缓动，`hide` 只影响取景；
  - `steps` 用 `select` 选择构件，声明 `action`、`stage`、`startSeconds`、`endSeconds` 与 `after`；`after` 只约束开始时间不早于依赖结束；
  - `label` 是画面小字标注用的构件名，可省略。
- `manifest.json`（v2）：外部资产清单；纯程序材质时为空数组。登记资产时必须保存来源、许可、路径与 SHA-256。
- v1 材料明确失败并提示按 v2 重写；不提供迁移工具或兼容分支。

## 构件与选择器

- 稳定 ID：`site`、`excavation`、`foundation-slab`、`foundation-ring-*`、`column-{floor}-{bay}-{front|back}`、`beam-{floor}-{front|back}-{bay}`、`slab-{floor}`、`stair-{floor}-{step}`、`stairwell-{floor}`、`wall-{floor}-{side}-0`、`roof-*`、`opening-{id}`、`finish-{id}`、`yard-*`。
- `select` 只支持末尾 `*` 的简单 glob。每个非初始构件必须恰好被一个步骤建成一次；未匹配、重复、选择器重叠、引用初始构件或依赖环都会失败，并报告步骤与构件 ID。
- Python 校验器（`components.py`）与前端构件图（`model.ts`）维护同一套 ID；prepare 后运行时还会核对身份清单，漂移会直接报错。

## 动作与镜头

- 动作：`excavate` 向下开挖；`pour` 从底部浇筑；`grow` 柱向上生长；`slide` 梁沿轴向滑入；`lift` 墙板/屋面板落下；`rotate` 屋面板转到位；`insert` 门窗框与玻璃吸附；`spread` 庭院路径展开。
- 每个动作只读当前帧、步骤窗口与材料参数，不读上一帧；任意帧正序、倒序或重复求值得到同一变换。
- 镜头边界硬切，不做溶解；近景用较低机位与 35–45° 透视，让柱梁板交接占据画面。`hide` 用于近景剖切，隐藏不改建成状态，最终镜头必须恢复全部构件。

## 可读性层

- 常驻底部阶段轨，当前阶段高亮；
- 当前步骤的构件名用 20 px 小字与引线指向构件，最多两条，避让画面边缘；
- 完工体量的幽灵轮廓在主体完成前可见，完工镜头淡出；
- 左下 3 m 比例尺，右下“建造过程示意”小字；
- 小字不得遮挡构件、连接点或关键动作。

## 视觉与边界

- 16:9 横屏、30 fps、无音轨；程序化住宅使用真实墙洞、坡屋顶、楼梯与庭院，不使用贴片冒充门窗。
- 混凝土、木材、玻璃、屋面与地面有可区分的材质与明度；固定平行主光与半球补光，接触阴影方向一致。
- 不得把组装动画宣称为完整施工工序、结构计算或工程适用性结论；首例为表达示意。
- 作品、媒体与生成候选留在忽略的内容目录，不入库。

## 制作命令

```powershell
uv run m2v init --type building-construction --project <slug>
uv run m2v validate --project videos/building-construction/<slug>
uv run m2v prepare --project videos/building-construction/<slug>
uv run m2v lookdev --project videos/building-construction/<slug> --sheet 2 8 12 18 24 30 36 42 48 54 59
uv run m2v preview --project videos/building-construction/<slug> --start-seconds 10 --end-seconds 16
uv run m2v render --project videos/building-construction/<slug>
uv run m2v qa --project videos/building-construction/<slug>
```

`lookdev --sheet` 按秒数渲染原生静帧并拼接触表；`lookdev --det` 正序/倒序两遍采集，逐帧 PSNR 须不低于 60 dB。`qa` 检查帧数、尺寸、帧率、时长、无音轨与冻结帧；技术通过不等于理解通过。

## 视觉与运动

- 构图、层级、色彩与字阶判断按 [Frontend Design](../../frontend-design/SKILL.md) 与[视频适配](../../frontend-design/ADAPTATION.md)：主体占比、阶段标签的小字层级、示意边界标注的次要位置都在其观察方法内判断。
- 阶段推进、构件生长、镜头切换的时长、缓动与编排按[运动设计](../../motion-design/SKILL.md) 与[视频适配](../../motion-design/ADAPTATION.md)：构件出现用减速落定，镜头切换用两端平滑，匀速升降只在表达需要时显式声明。
- 本页只保留建造特有的材料、动作与确定性要求，不复述通用视觉或运动理论。
