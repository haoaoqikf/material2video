## Purpose

建立口播语义段、字幕真实时间和画面推理动作之间的稳定契约，使有声与无声预览都能按帧复现“字幕说到哪里，动画解释到哪里”。

## Requirements

### Requirement: 分段口播绑定受控语义节拍
有口播的 v3 场景 SHALL 使用 `narrationSegments` 并由 `beats` 完整绑定；场景 SHALL NOT 使用字符串 `narration`。每个分段 SHALL 具有唯一 id、非空文本和有效 beat 引用。每个 beat SHALL 具有唯一 id、受控 action、至少一个有效目标和非空 meaning。

#### Scenario: 分段口播有效
- **WHEN** 各口播段依次绑定存在的 beat，且 beat 目标均为该幕可定位节点
- **THEN** 完整口播按段顺序拼接，画面可按相同顺序推进语义动作

#### Scenario: 字符串口播
- **WHEN** v3 场景声明字符串 `narration`
- **THEN** schema 拒绝场景并要求改用 `narrationSegments` 与 `beats`

### Requirement: 媒体准备解析真实节拍时间
有声准备 SHALL 以 TTS WordBoundary 为真源，把每个口播段解析为场景内开始包含、结束不包含的帧区间，并在媒体清单中保存逐幕 `resolvedBeats`。字幕、配音和画面 SHALL 共用这些边界；解析失败、倒退、重叠、越界或文本覆盖不完整时 SHALL 失败而不猜测。

#### Scenario: TTS 延长场景
- **WHEN** 实际音频长于分镜声明时长
- **THEN** 系统延长派生场景并重新计算 beat 区间，不覆盖源分镜或要求作者改绝对帧号

#### Scenario: 重复文本仍按段匹配
- **WHEN** 多个口播段包含相同短语
- **THEN** 系统按原文顺序和词边界消费文本，不把后一个短语错误映射到前一处

### Requirement: 无声与有声运行时提供统一节拍状态
无媒体时，系统 SHALL 按分镜声明时长和口播段顺序等比例解析 beat；有媒体时 SHALL 只使用已验证的 `resolvedBeats`。场景树和代码场景 SHALL 获得当前 beat、局部进度和已完成 beat 集合，且状态只由分镜、媒体与当前帧决定。

#### Scenario: 随机访问有声帧
- **WHEN** 渲染器直接访问一个已解析 beat 的中间帧
- **THEN** 场景树与代码场景得到相同的 beat id、局部进度和完成集合

#### Scenario: 无声预览
- **WHEN** 分镜有分段口播但未传媒体清单
- **THEN** 画面仍按声明时长等比例播放全部 beats，并明确属于估算时间轴

### Requirement: 动画论证评审独立报告
评审 SHALL 输出 A1–A8：节拍覆盖、含义声明、状态或关系变化、字幕同步、结尾停留、装饰动画人工裁决、单一焦点和稳定结束。A1–A5、A7–A8 SHALL 可机检并进入严格评审；A6 SHALL 由人工或视觉模型裁决，缺失时显示待评审而非通过。

#### Scenario: 动画只做入场
- **WHEN** 非文字幕虽然有多个元素入场，但没有任何 beat 改变对象状态或关系
- **THEN** A3 失败并指出相关场景

#### Scenario: 人工结论缺失
- **WHEN** A6 没有评分或依据
- **THEN** 报告标记待评审，作品不得被标记为可发布

### Requirement: beat 必须描述前后状态

启用新版导演能力的 beat SHALL 描述受控动作与它对观众的解释，并 SHALL 在需要时补充
变化前状态、变化后状态或两者的关系；仅声明入场方式不得满足语义节拍要求。

`before` / `after` / `relation` 是可选字段，声明时 SHALL 校验非空；
必填字段 SHALL 是 `id` / `action` / `targets` / `meaning`。

#### Scenario: 只有淡入动作
- **WHEN** beat 的 `action` 只表达元素出现，没有任何状态或关系变化
- **THEN** 严格动画评审失败并指出该 beat

#### Scenario: 声明了状态字段但内容为空
- **WHEN** beat 声明了 `before` 或 `after` 但取值为空字符串
- **THEN** 校验报错并指出该字段

### Requirement: 时间轴必须支持跨幕连续对象
媒体与无声时间轴 SHALL 能以稳定节点身份表达相邻场景的继承、变形、拆解、重组或断裂；无法映射时 SHALL 显式报告，不得静默复制节点。

#### Scenario: 节点跨幕变形
- **WHEN** 一个节点在下一幕变为另一种受控原语
- **THEN** 时间轴记录变形关系，渲染器按声明执行或报告不支持该变形

### Requirement: 视觉阶段默认绑定语义节拍
声明了分段口播的场景 SHALL 从已解析 beat 区间派生 `establish`、`change`、`result` 阶段；没有媒体时使用无声估算区间，有媒体时只使用已验证的真实区间。分镜 v3 的每条动作与镜头 SHALL 绑定 beat 或阶段，绝对帧输入一律拒绝，不设置兼容路径。

#### Scenario: 有声场景阶段同步
- **WHEN** 媒体准备延长场景并生成新的 `resolvedBeats`
- **THEN** 节点动效和镜头段随真实区间重新解析，字幕、画面变化与稳定收尾仍使用同一时间轴

### Requirement: 时间轴保留稳定结果阶段
最后一个改变状态或关系的 beat 完成后，时间轴 SHALL 进入结果与稳定阅读阶段；该阶段 SHALL 冻结主要关系和焦点终态，仅允许不改变论证的受控微动。默认稳定阅读时间 SHALL 不少于 12 帧。

#### Scenario: 幕尾仍在换焦点
- **WHEN** 最后一条动作在稳定阅读窗口内继续改变主要焦点或关系
- **THEN** 严格动画评审失败并报告动作结束帧、稳定窗口和受影响节点

### Requirement: 动画编排评审量测语义节奏
动画评审 SHALL 报告镜头持续漂移、错峰密度、视觉状态瞬跳、共享元素首尾连续性和稳定结束。可确定性判断的违反项 SHALL 进入严格评审；“动画是否服务论点”的语义结论仍 SHALL 由人工或视觉模型裁决。

#### Scenario: 动作过密
- **WHEN** 一个错峰组在连续帧中启动过多独立焦点，导致观众无法形成单一阅读顺序
- **THEN** 评审报告场景、节点组、实测间隔与允许阈值
