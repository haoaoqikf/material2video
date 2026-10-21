# 验证记录

制作与复核：2026-10-21。本文记录本轮「体验问题闭环与拥堵波重制」的实现、重制与验收。
机制依据、作者与使用边界见 [SOURCES.md](SOURCES.md)；完整设计、候选与回退记录见
[DESIGN.md](DESIGN.md)；逐场观察、问题闭环与导演审查见交付目录
`videos/examples/traffic-jam-wave/outputs/visual-notes.md`，传播预估见同目录
`reach-potential-report.md`。

## 本轮变更范围

- 共享流程：问题状态扩展为未解决、待复查、已关闭、接受保留；关闭必须回应原验收条件；
  接受保留不计入解决。制作前声明手机尺寸及主体辨认、动作理解、关系理解三类目标；
  第一次导演审查在精制前保存，第二次在最终候选后保存；最终候选逐页实际查看全片时间标注
  序列并记录页码与时间范围。
- 共享实现：新增 `src/m2v/engine/rhythm_measure.py`，在 `m2v qa` 的
  `inspection.rhythm` 输出全片/逐场字数、旁白窗口、平均字速、静音并集/交集、声明留白与
  未知归因；复用已完成的音轨检测与 prepared 时间轴，不再次解码音轨，不参与技术或审美判定。
  字数口径下沉到 `src/m2v/core/text.py`，与字幕阅读报告共用。
- 作品：按 A/B/C 配音对照与微调方案 E 重制；放大道路、车辆、后视镜与环路；密度场改为
  ① 车流 → ② 曲线；删除 `f3` 来源口播与重复静态文案，`return` 缩至 12.4 秒。
- 仓库仍只有 `american-science-milestones`、`traffic-jam-wave`、`solar-system-journey`
  三个示例；另外两片的画幅、时长与声音契约未修改。

## 旧版对照

- 本轮重制前的有效交付 SHA-256
  `67b0aa91c3a74a2d899d9c6f1bd9ba08c3b63cc235970e4a05bef5cb456cba79`，5094 帧、
  84.90 秒；准备指纹 `9276bb67ec33430b2dccda40387d4f0d6f867670102623f2a1bb6fee27310586`。
- 旧版成片、摘要与 14 张手机尺寸代表帧保存在交付目录
  `videos/examples/traffic-jam-wave/outputs/visual-review/before-r3/`，由 `visual-notes.md`
  直接引用；媒体不入库。
- 新旧对照按叙事角色对应：`empty`、`rewind`、`brake`、`relay`、`density`、`return`；
  不强求相同时间码对应同一事件。

## 素材与配音

- 材料校验通过；`prepare` 按 13 段中文旁白合成配音并生成 34 条烧录字幕。
- 音色 `zh-CN-YunxiNeural`：服务返回 Novel 类别、Lively/Sunshine 个性；依据完整旁白与
  服务元数据选择，未试听。
- 同一旁白的四种节奏方案（`visual-review/voice/comparison.json`）：

| 方案 | 语速 | 停顿 | 总时长 | 窗口字速 | 字幕峰值 | 超限 |
|---|---|---:|---:|---:|---:|---:|
| A 当前参数 | +0% | 默认 | 75.83 秒 | 3.85 字/秒 | 7.29 字/秒 | 0 |
| B 仅调停顿 | +0% | 0.15 / 0.45 / 0.50 / 0.08 | 69.02 秒 | 4.29 字/秒 | 12.00 字/秒 | 2 |
| C 停顿 + 加速 | +15% | 同 B | 61.53 秒 | 4.89 字/秒 | 10.91 字/秒 | 2 |
| E 微调后采用 | +0% | 0.22 / 0.65 / 0.80 / 0.12 | 70.98 秒 | 4.15 字/秒 | 8.28 字/秒 | 0 |

- 选择 E：B、C 把两条短字幕推到 9 字/秒以上；E 无超限，比 A 短 4.85 秒，观察预算仍为
  8.1 秒（总时长减旁白窗口并集）。不按最短自动获胜，未播放、未试听。
- 声音契约：无配乐；仅保留两次低增益内置提示音（回放、首次刹车），中文旁白与烧录字幕。

## 场景时间预算（实测配音）

| 场景 | 起止 | 时长 | 旁白段 |
|---|---:|---:|---|
| `empty` | 0.00–9.75 秒 | 9.75 秒 | `e1`–`e2` |
| `rewind` | 9.75–21.07 秒 | 11.32 秒 | `w1`–`w2` |
| `brake` | 21.07–31.83 秒 | 10.77 秒 | `b1`–`b2` |
| `relay` | 31.83–48.18 秒 | 16.35 秒 | `l1`–`l3` |
| `density` | 48.18–58.58 秒 | 10.40 秒 | `d1`–`d2` |
| `return` | 58.58–70.98 秒 | 12.40 秒 | `f1`–`f2` |

- 准备指纹：`20721dc7ccf422f447df7681c28d5d781820ad9aefbffbb7e458e4080869f90f`；
  4259 帧、70.98 秒、1080×1920、60 fps。

## 设计、试制与重制

- 手机关键事件目标、逐场设计与美术参数见 [DESIGN.md](DESIGN.md)；三类目标分开记录：
  主体辨认、动作理解、关系理解，不以标签清楚替代动作或关系。
- 尺度：道路车辆 2.4 倍（车长约 125 px，393 宽下约 45 px）、编号基字号 13 px；后视镜
  470×330；环路车辆 2.6 倍、缩放 1.02→1.18。旧版车体约 29 px、后视镜 120×87 px。
- 密度：① 先出现高密度道路，随后低密度道路；约 2.6 秒后 ② 曲线淡入；坐标字号 24–26 px。
- 结尾：删除 `f3` 来源口播与重复静态句，`readingHoldFrames` 30、`tailFrames` 60；
  `return` 20.15 → 12.40 秒，全片 84.90 → 70.98 秒。
- 试制中修复：标题压「后视镜」、1 号车被切出画面、环路浮动标签压车号、图表取景看不到
  红区、图表字号偏小、结尾后视镜放大越界；修复与复查证据见 `visual-notes.md`。
- 实现审查修复：`explainer_prepare` 在拼接音轨时误用了最后一幕的段间留白列表；改为逐幕
  使用本幕 `holdFrames`，并补回归测试。场景边界与构图不变，幕内窗口移动不超过 0.4 秒；
  修复后重新 prepare（指纹 `20721dc7…`）并重制最终候选。
- 两个美术方向仍沿用上一轮的夜景俯视道路；本轮不重新做方向选案，只修正尺度与信息顺序。

## 整片动态复核

- 正式候选前生成完整粗预演 `visual-review/r3-rough/preview.mp4`（70.97 秒，
  SHA-256 `f160bbc1b8fc46175c154c1e1af59c88012a82db92a272542c6b433af3a04360`），
  逐秒 71 帧分 5 页查看，覆盖 0–70 秒；另看 12 张跨幕静帧与手机尺寸接触表。
- 第一次导演审查在粗预演后、最终候选前保存：主问题、观看动机、核心事件、答案与结尾回报
  均成立，无结构必改项；记录见 `visual-notes.md` 的「第一次导演审查」。
- 剪辑决策比较了保留旧结尾与删除 `f3`/重复句、保留旧密度顺序与分步呈现；采用后者，
  理由与前后证据见 `visual-notes.md` 的「剪辑重组」。

## 全片导演审查与剪辑

- 第二次导演审查绑定最终成片 SHA-256
  `b2cb909210ab674b68efd8f2f1b0a339eff3808dbdbc04e0d9cf60a0e1afabef`、准备指纹
  `20721dc7ccf422f447df7681c28d5d781820ad9aefbffbb7e458e4080869f90f` 与 41 页全片
  逐页检查记录；结论为交付，无结构必改项。
- 第一次审查的 D01–D03 与 R01–R08 已关闭；保留意见仅为 `brake` 首枚圆点与 `density`
  图表信息量，均非必改。
- 最终审查保留退回剪辑的权力；本轮未使用，因为结构、主次、高潮、统一性与衔接成立。

## 轨迹与运动量测

| 指标 | 高密度组 | 低密度组 |
|---|---:|---:|
| 车辆数 / 初始间距 | 16 辆 / 174.22 px | 8 辆 / 348.44 px |
| 最小中心距 | 104.65 px | 285.90 px |
| 低速区域出现区间 | 7.6–21.8 秒 | 7.6–11.8 秒 |
| 最低速车辆编号变化 | 1 → 16 | 1 → 5 |
| 后退速度（示意） | 184.03 px/秒 | 331.84 px/秒 |
| 第 6 辆车最低相对速度 | 16.31% | 77.56% |

- 本轮未修改 `assets/traffic/traffic.json` 或生成脚本；轨迹、车距、灯态与图表仍同源。
- `tests/test_traffic_example.py` 继续重新生成轨迹并逐值比对仓库数据。

## 成片与技术验收

- 成片位于 `videos/examples/traffic-jam-wave/outputs/video.mp4`；交付键
  `a2c7f001b2fab6a6e6301aae6c8440d59c3c19e0968346092cdcaceb14a947a7`，
  SHA-256 `b2cb909210ab674b68efd8f2f1b0a339eff3808dbdbc04e0d9cf60a0e1afabef`。
- `m2v render` 通过；`m2v qa` 状态 `pass`：645 个全片序列样本、41 页接触表，逐页查看；
  重复帧 1 对、最长静止 0.5 秒；字幕对比度 19.43:1；响度 −14.3 LUFS、真峰值 −3.9 dBFS；
  音画时长差 0.0034 秒；claims 覆盖通过。
- 唯一视频候选为 48.183–48.517 秒的 `black-frame`，位于 `density` 硬切入场；标题与字幕
  可见、道路随后淡入，按设计暗场记录，不改技术判定。
- `inspection.rhythm`：261 字、旁白窗口并集 62.88 秒、平均字速 4.15 字/秒；静音候选 16、
  合并 16、并集 22.04 秒（31.04%）；旁白窗口内 13.94 秒、声明留白内 8.10 秒、
  未知归因 0.00 秒（四舍五入前 0.00007 秒）。逐场字速 `empty` 4.38、`rewind` 4.03、`brake` 4.18、`relay` 4.43、
  `density` 4.02、`return` 3.77；字幕峰值 8.28 字/秒，超限 0。

## 节奏测量实现检查

- 区间聚合为排序合并，复杂度 O(n log n)；逐场与旁白窗口求交为 O(n·m)，本片 m 为
  6 场、13 段旁白、16 个静音区间，无性能风险。
- `rhythm_measure.build` 是纯函数；`qa_inspection.inspect` 只调用一次 `audio_signals`，
  再把结果交给节奏测量。`tests/test_rhythm_measure.py` 用 monkeypatch 拒绝
  `subprocess.run/Popen`，验证不会再次解码音轨。
- 字数与 `reading_pace` 共用 `count_characters`（排除 Unicode 标点与空白）；窗口平均字速
  可以高于 9 字/秒而不产生失败状态，字幕阅读上限仍独立报告。
- 测试覆盖：重叠/首尾相接区间、跨场与片尾静音、无旁白、零时长、未知归因、检测失败、
  缺时间轴、逐场交集不重复计时、纯函数不再解码。
- 声明留白与时间轴实际落地留白分开报告（`storyboardHoldSeconds` / `declaredHoldSeconds`）；
  淡化重叠的边界静音归后一幕，逐场合计等于全片并集。音轨短于旁白窗口时 `truncated` 为真、
  字速为 `null`，不强行计算。另补 `test_segment_holds_are_read_from_each_scene`，防止
  准备阶段误用其他幕的 `holdFrames`。

## 代码审查修复

- 准备阶段：`explainer_prepare` 的第二个拼接循环误用了最后一幕的 `holds` 列表，导致所有
  幕的段间留白沿用最后一幕；已改为逐幕 `hold_lists`，并补
  `test_segment_holds_are_read_from_each_scene`。修复后 `relay` l1→l2 与 l2→l3 分别按
  18/20 帧落地。
- 节奏测量：补 `READING_TAIL_SECONDS` 共享默认值，避免漏报未声明阅读停留；淡化重叠时
  边界静音只归后一幕；音轨短于旁白窗口时 `truncated` 为真、字速为 `null`；声明留白与
  实际落地留白分开报告；旁白窗口提取与音频候选共用一份口径。
- 画面：`return` 后视镜放大后的右边缘不再超出 1080 画布。
- 文档：修正 `DESIGN.md` 中 `return` 仍写 `f1`–`f3` 的残留。
- 新增代码与测试已纳入 Git 管理；回归测试见上表。

## 逐场与全片复核

- 六场均完成观察复述、七类结论、证据与问题闭环，见 `visual-notes.md`；场景清单与实际
  分镜完全对应。
- 全片检查问题闭合、主次、节奏、高潮、统一性与衔接：生活困惑 → 方向反常 → 一次刹车 →
  环路换车 → 密度补充 → 回到空路；没有重复静态信息卡或逐页文字板。
- 最终候选 41 页逐页检查全部完成，页码与时间范围见 `visual-notes.md`；未查看页为无。
- 第二次导演审查结论为交付；`brake` 首枚圆点与 `density` 图表信息量作为非必改保留。

## 百万播放潜力

- 报告位于 `videos/examples/traffic-jam-wave/outputs/reach-potential-report.md`，绑定最终
  成片 SHA-256、准备指纹与逐页证据；结论、支持/反面依据、平台未知项与发布后验证方法见报告。

## 验证命令与结果

| 命令 | 结果 |
|---|---|
| `uv run m2v validate --project examples/traffic-jam-wave` | 材料校验通过 |
| `uv run m2v prepare --project examples/traffic-jam-wave` | 准备完成；4259 帧、70.98 秒、34 条字幕 |
| `uv run m2v lookdev --project examples/traffic-jam-wave --stills 12 --sample-seconds 8` | 12 张静帧、接触表与 8 秒有声样片 |
| `uv run m2v preview --project examples/traffic-jam-wave --limit-frames 4258` | 完整粗预演 70.97 秒 |
| `uv run m2v render --project examples/traffic-jam-wave` | 一次全片生成并交付；候选 `a2c7f001…`、SHA-256 `b2cb9092…` |
| `uv run m2v qa --project examples/traffic-jam-wave` | `pass`；645 采样、41 页；技术范围见上 |
| `uv run pytest` | 660 passed、4 skipped（637.01 秒，退出码 0） |
| `pnpm -C web typecheck` | 通过 |
| `pnpm -C web build` | 通过（101 modules，6.38 秒；仅有 chunk 体积提示） |
| `pnpm -C web test` | 4 个测试文件、58 个用例通过 |
| `uv run python examples/traffic-jam-wave/scripts/verify-trajectory.py` | 轨迹量测报告写入 `examples/traffic-jam-wave/outputs/verification/` |
| `openspec validate fix-experience-review-and-remaster-traffic-wave --strict --type change` | valid |
| `openspec validate --specs --strict` | 18 项通过 |
| `uv run python .agents/skills/material2video/scripts/sync_docs.py --check` | 类型清单与目录一致 |

## 覆盖限制

- 未播放视频、未连续收听；复核基于完整粗预演逐秒帧序列、静帧、轨迹量测与自动音频信号。
  采样之间的瞬时运动、配音自然度与主观听感不在覆盖范围内。
- 轨迹是预设示意，不复制论文数值，也不证明密度是任何条件下拥堵的唯一原因。
- 手机尺寸复核只验证画面可读性，未验证真实设备、播放器 UI 或平台安全区。
