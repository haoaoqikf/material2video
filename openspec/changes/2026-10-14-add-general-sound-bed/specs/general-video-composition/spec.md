## ADDED Requirements

### Requirement: 通用片受控音床

通用计划 MUST 支持可选的 `soundtrack.music`，声明作品目录内本地相对路径的音频素材、增益、循环与淡入淡出；素材 MUST 为可解码音频，路径 MUST 不可越界。校验 MUST 复用共享声音契约的增益、路径与淡入淡出规则。

通用场景没有 beat 轴，因此计划 MUST 拒绝 `soundtrack.effects` 并说明原因，不得为音效猜一个起点。

声明音床时，系统 MUST 先按全片帧边界拼出整片旁白，再以字幕讲话区间生成闪避包络与音床混合，并把混合结果作为**单条母版音轨**落到第 0 帧；音轨 MUST 覆盖全片帧数。系统 MUST 把声音配置摘要与音轨摘要写入准备记录，使音床素材或参数变化使准备与评审过期。

未声明 `soundtrack` 时，音轨 MUST 保持逐场景轨的既有行为。

#### Scenario: 声明音床后合成为单条母版轨

- **WHEN** 通用计划的场景含口播并声明 `soundtrack.music`
- **THEN** 准备产物只含一条从第 0 帧起、覆盖全片帧数的音轨，且讲话处音床被压低

#### Scenario: 音床素材或增益变化使准备过期

- **WHEN** 更改音床素材内容、`gainDb`、循环或淡入淡出后未重新准备
- **THEN** 渲染拒绝使用旧准备记录并要求重新准备

#### Scenario: 未声明音床保持原行为

- **WHEN** 通用计划不含 `soundtrack`
- **THEN** 音轨仍按逐场景轨摆放，准备记录不含声音配置摘要

#### Scenario: 拒绝音效并说明原因

- **WHEN** 通用计划声明 `soundtrack.effects`
- **THEN** 计划校验失败，指出该场景结构没有 beat 轴、只支持 `soundtrack.music`

#### Scenario: 音床素材路径越界或参数非法

- **WHEN** `soundtrack.music.sourceRef` 使用绝对路径、`..`、反斜线或 URL，或增益、淡入淡出超出允许范围
- **THEN** 计划校验失败并指出具体字段

### Requirement: 通用成片音轨交付规格

通用成片的音轨 MUST 编码为 AAC-LC、44.1kHz、立体声、128k，与文章类型的交付规格一致；MUST NOT 直接沿用 24kHz 单声道源规格，因为该组合会被 Windows Media Foundation 拒绝打开。成片验收 MUST 继续校验音轨可解码且音画时长一致。

#### Scenario: 含音轨的通用成片编码规格

- **WHEN** 渲染带旁白或音床的通用成片
- **THEN** 成片音轨为 AAC-LC、44.1kHz、立体声且可完整解码

#### Scenario: 无声通用成片不受影响

- **WHEN** 通用计划不含任何旁白与音床
- **THEN** 成片不含音轨，验收按无声输出处理

## MODIFIED Requirements

### Requirement: 声音字幕及基础转场

系统 MUST 支持固定帧或口播派生时长、现有 TTS、受控本地音轨与可选音床、硬切和默认 12 帧的交叉淡化。字幕/节拍/音轨 MUST 映射到全片帧，画面及场景音轨共享淡化进度。固定容量口播溢出和父口播覆盖嵌入口播 MUST 失败。音床 MUST 只使用作品目录内的本地素材，且其配置变化 MUST 使准备与评审过期。

#### Scenario: 淡化和口播

- **WHEN** 相邻场景采用淡化且包含声音
- **THEN** 画面和声音同帧淡化，字幕按编译边界显示，容量不足明确失败

#### Scenario: 口播叠加音床

- **WHEN** 通用片同时含口播与音床
- **THEN** 口播保持清晰、音床在讲话区间被压低，两者共用同一条全片音轨
