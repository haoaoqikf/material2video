# 验证记录

制作与复核：2026-10-21。本文记录逐场设计与独立验收、百万播放潜力报告和拥堵波重制后的
最终交付版本。机制依据、作者与使用边界见 [SOURCES.md](SOURCES.md)；完整设计、候选与回退
记录见 [DESIGN.md](DESIGN.md)；逐场观察与问题闭环见交付目录 `videos/examples/traffic-jam-wave/outputs/visual-notes.md`，传播预估见 `videos/examples/traffic-jam-wave/outputs/reach-potential-report.md`。

## 本轮变更范围

- 共享流程：新增技能参考中的逐场设计与独立验收、全片导演审查与剪辑重组、百万播放潜力模板；
  本片按新契约重制。
- 作品：主问题改为「堵了半天，前面为什么什么都没有？」；结构改为
  `empty` → `rewind` → `brake` → `relay` → `density` → `return`；取消固定 75 秒或
  60～90 秒预算，时长由实测旁白与观察时间决定。
- 美术：比较纸面交通笔记与夜景俯视道路两个方向，采用后者；方向 A 保留对照证据但不进成片。
- 仓库仍只有 `american-science-milestones`、`traffic-jam-wave`、`solar-system-journey`
  三个示例；另外两片的画幅、时长与声音契约未修改，严格示例校验通过。

## 旧版对照

- 旧版成片 SHA-256 `ab41d2e338b27a5635cf39c6a489fda65fd3b8d2d9f981603f08cf237f5c2ea8`，
  1080×1920、60 fps、3653 帧、60.883 秒；准备指纹
  `f83ef54c307923caba0b6423a70c97f692ce3d3f99516c51b53c968af8b7c789`。
- 旧版成片、13 张代表帧、旧设计/复核文本与摘要保存在交付目录
  `videos/examples/traffic-jam-wave/outputs/visual-review/before/`，已由 `videos/examples/traffic-jam-wave/outputs/visual-notes.md` 直接引用，成功交付清理后
  仍可访问；旧媒体不纳入 Git。
- 新旧对照按叙事角色对应：`empty` 对应旧版 `opposite` 的方向反常，`rewind` 对应旧版
  `origin` 的倒回，`brake`/`relay` 对应旧版 `relay` 的机制，`density` 对应旧版
  `density`，`return` 对应旧版 `return`。不强求相同时间码对应同一事件。

## 素材与配音

- 材料校验通过；`prepare` 按 14 段中文旁白合成配音并生成 40 条烧录字幕。
- 音色 `zh-CN-YunxiNeural`：服务返回 Novel 类别、Lively/Sunshine 个性，适合先提问再解释的
  中文科普叙述；依据完整旁白与服务元数据选择，未试听。
- 阅读速度报告 `pass`：最快 7.29 字/秒、平均 5.27 字/秒，上限 9 字/秒。
- 声音契约：无配乐；仅保留两次低增益内置提示音（回放、首次刹车），中文旁白与烧录字幕；
  不依赖外部音乐或音效素材。

## 场景时间预算（实测配音）

| 场景 | 起止 | 时长 | 旁白段 |
|---|---:|---:|---|
| `empty` | 0.00–10.65 秒 | 10.65 秒 | `e1`–`e2` |
| `rewind` | 10.65–22.73 秒 | 12.08 秒 | `w1`–`w2` |
| `brake` | 22.73–34.77 秒 | 12.03 秒 | `b1`–`b2` |
| `relay` | 34.77–52.25 秒 | 17.48 秒 | `l1`–`l3` |
| `density` | 52.25–64.75 秒 | 12.50 秒 | `d1`–`d2` |
| `return` | 64.75–84.90 秒 | 20.15 秒 | `f1`–`f3` |

- 准备指纹：`9276bb67ec33430b2dccda40387d4f0d6f867670102623f2a1bb6fee27310586`；
  成片 5094 帧、84.9 秒、1080×1920、60 fps。
- 时长由 14 段实测旁白、24～36 帧阅读停留与片尾 90 帧留白共同决定，没有固定秒数或加速画面。

## 方向比较与核心试制

- 同一核心内容实际制作两个方向：A 纸面交通观察笔记，B 夜景俯视道路。两者使用同一轨迹、
  同一组正式文案与实际字幕，并在 393×852 手机尺寸比较。
- 采用 B：道路铺满画面，蓝框车、红色慢区与后视镜同框，手机尺寸下方向冲突更清楚；A 的
  车辆在手机尺寸偏小，阅读方式更像查表，淘汰理由与证据见 `DESIGN.md` 和
  `videos/examples/traffic-jam-wave/outputs/visual-review/directions/`。
- 核心事件试制发现并修复：红区在开场第 8 秒移出画面；标题与后视镜重叠；环路标签随车旋转；
  密度标题换行与坐标重叠；结尾后视镜失去红区。关闭记录见 `videos/examples/traffic-jam-wave/outputs/visual-notes.md`。

## 整片动态复核

- 正式候选前使用 `m2v lookdev` 采集跨六幕的 12 张静帧与 8 秒有声样片，检查开场、回放、
  刹车、环路、密度与结尾的构图和信息推进。
- 正式候选后使用 `m2v qa` 生成 746 个全片序列样本与 47 页接触表，并查看第 1、4、8、12、
  16、20、24、28、32、40、47 页，覆盖六幕与主要交界；未单独生成低清粗预演，整片动态检查
  由 lookdev 样片与最终全片序列共同承担，结构和表现必改项在正式候选前关闭。

## 全片导演审查与剪辑

- 第一次导演审查在 lookdev 跨幕静帧与 8 秒样片上执行，角色分离自审，不是外部导演或真实
  观众试映；记录在最终候选形成后整理，观察依据为精制前实际保存的静帧与样片；结论为
  「进入下一阶段」，无结构必改项，登记密度位置、抽象红区、结尾长度与手机尺寸下环路
  可读性四项局部/可选问题。
- 剪辑决策比较了保留、后移密度、删除密度与进一步压缩四种方案：保留当前结构，理由是密度
  明确标为补充解释、提供条件边界与视觉降温；后移会削弱结尾回扣，删除会丢失必要对照，
  进一步压缩会让手机尺寸读不清。未采用修改，因此无需回写材料或重新 prepare。
- 第二次导演审查绑定最终成片 SHA-256 与准备指纹，结论为「交付」；结构、主次、高潮、
  统一性与衔接成立，V01–V05 已关闭。完整记录见交付目录
  `videos/examples/traffic-jam-wave/outputs/visual-notes.md` 的「全片导演审查」与
  「剪辑重组」章节。
- 导演与剪辑判断演练（局部全通过但全片失败、因已投入拒绝删场、重剪未回写、最终结构回退、
  自审冒充试映）均记录为演练，未伪造真实失败。

## 轨迹与运动量测

| 指标 | 高密度组 | 低密度组 |
|---|---|---|
| 车辆数 / 初始间距 | 16 辆 / 174.22 px | 8 辆 / 348.44 px |
| 最小中心距 | 104.65 px | 285.90 px |
| 低速区域出现区间 | 7.6–21.8 秒 | 7.6–11.8 秒 |
| 最低速车辆编号变化 | 1 → 16 | 1 → 5 |
| 后退速度（示意） | 184.03 px/秒 | 331.84 px/秒 |
| 第 6 辆车最低相对速度 | 16.31% | 77.56% |

- 环路累计弧长表单调且闭合，周长 2787.495 px；全部关键帧速度非负，最小中心距大于车身
  长度并保留安全余量，没有穿车。
- 制动灯条件固定为相对巡航速度低于 94%，场景代码从同一速度采样派生；编号在整段传播中
  不变；图表直接采样同一份数据，没有手工灯态或第二条曲线。
- `tests/test_traffic_example.py` 重新生成轨迹并逐值比对仓库数据，同时检查车距、时间戳、
  低速区域方向、灯态与图表派生。

## 成片与技术验收

- 成片位于 `videos/examples/traffic-jam-wave/outputs/video.mp4`。
- 交付键：`95cbceaed7fd76f583a5f4b3961c73b86bb1d848eef0d6c482a67623968f4b26`；
  成片 SHA-256：`67b0aa91c3a74a2d899d9c6f1bd9ba08c3b63cc235970e4a05bef5cb456cba79`。
- `m2v render` 通过；`m2v qa` 状态 `pass`：169 对抽样帧、重复帧 2 对、最长静止 1.0 秒
  （片尾阅读留白）、字幕对比度 19.43:1、音画时长差 0.01537 秒、响度 −14.2 LUFS、
  真峰值 −3.8 dBFS；全片 746 个序列样本、47 页接触表，未发现黑场或突变候选。
- 全片时间标注帧序列、接触表与逐镜头加密采样位于交付目录或 QA 报告引用位置；代表静帧、
  393×852 手机尺寸抽帧与新旧同尺寸对照位于 `videos/examples/traffic-jam-wave/outputs/visual-review/final/`。
- 手机尺寸复核：标题、结论、车辆编号与后视镜内容在 393×852 下可辨；字幕位于共享安全区，
  作品正文止于其上方。

## 逐场与全片复核

- 六场均完成设计、试制、精制与验收，七类结论、传播贡献、流失风险与问题闭环见
  `videos/examples/traffic-jam-wave/outputs/visual-notes.md`；场景清单与实际分镜完全对应。
- 全片检查问题闭合、主次、节奏、高潮、统一性与衔接：开场生活困惑 → 方向反常 → 一次刹车 →
  环路换车 → 密度补充 → 回到空路；没有重复静态信息卡或逐页文字板。
- 必改项 V01–V05 已在有效版本复查关闭；覆盖限制与未验证范围随交付披露。

## 百万播放潜力

- 报告位于 `videos/examples/traffic-jam-wave/outputs/reach-potential-report.md`，绑定最终成片 SHA-256、准备指纹与证据链接。
- 结论、支持/反面依据、逐场贡献、平台/账号未知项与发布后验证方法见报告；不保证播放量、
  不虚构概率或平台指标。

## 验证命令与结果

| 命令 | 结果 |
|---|---|
| `uv run m2v validate --project examples/traffic-jam-wave` | 材料校验通过 |
| `uv run m2v prepare --project examples/traffic-jam-wave` | 准备完成；5094 帧、84.9 秒、40 条字幕 |
| `uv run m2v lookdev --project examples/traffic-jam-wave --stills 12 --sample-seconds 8` | 12 张静帧、接触表与 8 秒有声样片 |
| `uv run m2v render --project examples/traffic-jam-wave` | 一次全片生成并交付；候选 `95cbce…`、SHA-256 `67b0aa…` |
| `uv run m2v qa --project examples/traffic-jam-wave` | `pass`；技术范围见上节 |
| `uv run python examples/traffic-jam-wave/scripts/verify-trajectory.py` | 轨迹量测报告写入 `examples/traffic-jam-wave/outputs/verification/` |
| `uv run pytest` | 退出码 0；100% 进度、4 个跳过，无失败 |
| `pnpm -C web typecheck` | 通过 |
| `pnpm -C web build` | 通过（101 modules，8.23 秒） |
| `pnpm -C web test` | 4 个测试文件、58 个用例通过 |
| `openspec validate scene-level-creative-review-and-traffic-remake --strict --type change` | valid |
| `openspec validate --specs --strict` | 18 项通过 |
| `uv run python .agents/skills/material2video/scripts/sync_docs.py --check` | 类型清单与目录一致 |

实现提交：`101d2ca`（逐场验收、导演审查与拥堵波重制）；归档提交随本次 `openspec archive` 生成，交付时报告。

## 覆盖限制

- 未播放视频、未连续收听；复核基于全片时间标注帧序列、代表静帧、轨迹量测与自动音频信号。
  采样之间的瞬时运动与主观听感不在覆盖范围内。
- 轨迹是预设示意，不复制论文数值，也不证明密度是任何条件下拥堵的唯一原因。
- 手机尺寸复核只验证画面可读性，未验证真实设备、播放器 UI 或平台安全区。
