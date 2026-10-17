## MODIFIED Requirements

### Requirement: 通用作品视觉设计与实际观看

制作助手 MUST 在编写场景前确定画幅并记录作品视觉设计，用户未指定时采用横屏。设计 MUST 包含参考依据、视觉隐喻、字体配色、开场/核心/结尾构图、运动与镜头承接以及声音意图。助手 MUST 检查代表关键帧，并实际观看含运动、转场和声音的代表片段；发现问题 MUST 记录时间位置、修改和复查。无法观看 MUST 明确说明，MUST NOT 虚构通过。

standard 档的设计与观看记录 MUST NOT 成为 CLI 导出门禁，不新增用户逐次确认。cinematic 档 MUST 在 look-dev 阶段产出 3–5 张 4K 静帧与 20–30 秒有声样片，MUST 在铺全片前取得用户确认；hero 镜头实看、20 秒样片与用户确认 MUST 成为导出前的质量门禁。该确认仅限 cinematic 档，standard 不受影响。

cinematic 档的设计 MUST 额外包含参考板（3–5 张静帧、1–2 段运动参考、1 段声音参考）、look bible（配色、主光比、镜头焦段、颗粒/LUT、曝光策略、黑位）与镜头清单（每段旁白对应的 shot、tier、camera、focus、exposure、post、claims）。参考板与镜头清单位于作品 `DESIGN.md` 或 `outputs/` 记录中，MUST NOT 只写形容词。

#### Scenario: 未指定画幅
- **WHEN** 用户仅提供内容
- **THEN** 助手以横屏规划并记录视觉依据，再制作关键画面与代码

#### Scenario: 观看发现问题
- **WHEN** 代表片段存在节奏、构图或声音问题
- **THEN** 记录具体位置，修改相关材料后重新准备并检查

#### Scenario: 纯 CLI
- **WHEN** 有效 standard 材料通过技术验收与当前完整预演，但没有视觉设计或观看记录
- **THEN** CLI 不因缺失这些记录而阻断导出

#### Scenario: 电影级未经 look-dev
- **WHEN** cinematic 作品未产出 4K 静帧、20 秒有声样片或未经用户确认
- **THEN** 铺全片与正式导出被阻断，并指出缺失的 look-dev 产物

## ADDED Requirements

### Requirement: 电影级制作档位与质量门禁

系统 MUST 提供 standard 与 cinematic 两个制作档位。standard MUST 保持现有自动验收、默认编码与无新增确认的快速链路；cinematic MUST 增加 look-dev、镜头清单、后期、声音设计、资产质量与用户确认。用户明确要求「电影级、极致、惊艳、发布级、品牌片」时，助手 MUST 使用 cinematic，MUST NOT 静默按 standard 交付；选择 cinematic 时必须先说明约 2–4 倍的制作与渲染成本。

cinematic 的流程 MUST 为 Brief → Look-dev → Hero → Full film → QA/确认：

- Brief MUST 记录受众、平台、时长、情绪目标、必须看到的特征与参考板。
- Look-dev MUST 产出 3–5 张最终画质 4K 静帧、20–30 秒有声样片、至少 2 个旁白音色的 A/B 与配乐/音效意图；用户确认后才能铺全片。
- Hero MUST 先完成至少 3 个 hero 镜头；每个 hero SHOULD 为 8–12 秒连续镜头，允许例外但必须记录理由。
- Full film MUST 完成全片、声音设计与 UI；实际时长符合作品目标。
- QA/确认 MUST 运行技术检查与 claims 可见性，把成片交给用户实际观看并询问是否通过；未获用户确认 MUST NOT 标记 cinematic 完成。

cinematic 的 QA MUST 覆盖：接触表、冻结/重复帧、banding、aliasing、字幕对比度、响度/真峰值、音画同步、claims 可见性与 hero 实看记录。技术检查通过但用户未确认时 MUST 报告为未完成，MUST NOT 用「自动验收通过」代替电影级结论。

#### Scenario: 用户要求电影级
- **WHEN** 用户明确要求电影级、极致或发布级成片
- **THEN** 助手切换到 cinematic，说明成本，并先交付 look-dev 静帧与有声样片

#### Scenario: 用户未通过
- **WHEN** 技术 QA 全部通过但用户看片后表示不通过
- **THEN** 作品不标记 cinematic 完成，记录用户指出的位置并返工

#### Scenario: 无法观看
- **WHEN** 助手无法实际观看 hero 或样片
- **THEN** 如实说明，不得声称已通过电影级验收，也不得用自动检查替代观看结论

#### Scenario: 标准档不受影响
- **WHEN** 作品未选择 cinematic
- **THEN** 继续使用 standard 的自动验收与现有编码，不触发 look-dev 或用户确认

### Requirement: 旁白主张与画面可见性

系统 MUST 接受旁白段可选 `claims`，记录本段旁白声称的画面特征（如大红斑、心形区域、木卫二冰纹）。prepare/preview MUST 把 claims 与该时间窗内的 shot、目标朝向和可见性检查绑定；cinematic 作品在 claims 对应画面上不可见时 MUST 阻断或要求显式记录例外。standard 作品未声明 claims 时 MUST 保持现有行为。

claims 检查 MUST NOT 依赖图像识别模型作为唯一判据；SHOULD 使用 shot 元数据、目标朝向、可见性配置与人工抽帧确认的组合。无法自动判定时 MUST 标记为待人工确认，MUST NOT 静默通过。

#### Scenario: 旁白声称大红斑
- **WHEN** 某段旁白声明 claims 包含“大红斑”，且该段时间窗内木星朝向使大红斑不可见
- **THEN** cinematic 准备或预演报告该 claim 不可见，要求调整镜头/自转相位或记录例外

#### Scenario: 标准作品未声明 claims
- **WHEN** standard 作品没有 claims 字段
- **THEN** 时间轴、准备记录与现有验收保持不变

#### Scenario: 自动无法判定
- **WHEN** claims 无法由元数据自动确认可见性
- **THEN** 标记为待人工抽帧确认，不写成通过
