## Purpose

建立口播语义段、字幕真实时间和画面推理动作之间的稳定契约，使有声与无声预览都能按帧复现“字幕说到哪里，动画解释到哪里”。

## Requirements

### Requirement: 分段口播绑定受控语义节拍
v4 有口播阶段 SHALL 使用 narrationSegments 与 beats；stage、beat、口播段 id SHALL 分别全片唯一。每个 beat SHALL 包含受控 action、有效全局 targets 和非空 meaning；不接受 narration 字符串。

#### Scenario: 有效分段
- **WHEN** 各口播段引用本阶段 beat 且目标存在
- **THEN** 按段顺序拼接口播并推进同一世界中的动作

#### Scenario: 重复 beat id
- **WHEN** 两个阶段声明同一 beat id
- **THEN** 校验拒绝避免全局时间绑定歧义

#### Scenario: 分段口播有效
- **WHEN** 各口播段依次绑定存在的 beat，且 beat 目标均为该阶段可定位节点
- **THEN** 完整口播按段顺序拼接，画面可按相同顺序推进语义动作

#### Scenario: 字符串口播
- **WHEN** v4 场景声明字符串 `narration`
- **THEN** schema 拒绝场景并要求改用 `narrationSegments` 与 `beats`

### Requirement: 媒体准备解析真实节拍时间
prepare SHALL 生成媒体清单 version 4，保存同序 stages 的实际时长与音频及全局 resolvedBeats，区间开始包含、结束不包含。解析 SHALL 以 WordBoundary 顺序消费文本，失败、倒退、重叠、越界或覆盖不完整则失败。旧清单 SHALL 要求重新 prepare；TTS延长不豁免实际全片35～45秒要求。音效 SHALL 以 stageId、beatId 定位。

#### Scenario: TTS 延长阶段
- **WHEN** 实际音频长于声明
- **THEN** 不改源分镜，延长派生阶段并重新推导后续 beat、动作、镜头、字幕和音效

#### Scenario: 重复文本
- **WHEN** 多个段含相同短语
- **THEN** 按原文顺序消费词边界，不错误匹配前一处

#### Scenario: 旧媒体
- **WHEN** 预览或渲染传入 version 1–3 清单
- **THEN** 明确拒绝并提示重新 prepare

#### Scenario: TTS 延长场景
- **WHEN** 实际音频长于分镜声明时长
- **THEN** 系统延长派生场景并重新计算 beat 区间，不覆盖源分镜或要求作者改绝对帧号

#### Scenario: 重复文本仍按段匹配
- **WHEN** 多个口播段包含相同短语
- **THEN** 系统按原文顺序和词边界消费文本，不把后一个短语错误映射到前一处

### Requirement: 无声与有声运行时提供统一节拍状态
无声 SHALL 按阶段声明时长估算 beat，有媒体 SHALL 只使用已验证的全局 resolvedBeats。双轨 SHALL 得到当前阶段、当前 beat、局部进度和全片已完成集合，同帧直接求值一致。

#### Scenario: 寻帧
- **WHEN** 直接访问一个全局 beat 中间帧
- **THEN** 双轨上下文一致并保留此前完成集合

#### Scenario: 无声
- **WHEN** 未传媒体
- **THEN** 按声明时间估算并明确 estimated，不伪造真实边界

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
时间轴 SHALL 使用全局对象身份与状态轨道表达阶段间连续性，不再使用跨幕节点映射或共享元素转场。已完成更新 SHALL 持续到下一次更新，任何帧可以直接求值。

#### Scenario: 累计对象
- **WHEN** 后阶段开始但没有新更新
- **THEN** 沿用先前终态，不重置或复制为新对象

#### Scenario: 节点跨幕变形
- **WHEN** 对象在后续阶段需要改变可见形态
- **THEN** 使用同一全局身份和受控状态或 code 几何纯函数，不能映射到新的独立幕

### Requirement: 视觉阶段默认绑定语义节拍
阶段内建立、变化、结果 SHALL 根据 beat 区间派生，无声使用估算，有声使用真实解析。动作与镜头 SHALL 引用 beatId 或 stageId/phase，禁止绝对起始帧与旧绑定回退。

#### Scenario: 重解析
- **WHEN** 配音延长阶段
- **THEN** 动作和镜头随真实边界移动并保留阶段收尾

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

### Requirement: 媒体派生实际时长独立检查
prepare 完成实际阶段时长解析后 SHALL 检查全片35～45秒，包含口播、停顿及稳定阅读。超出区间 SHALL 保存可诊断结果为不合格并阻断正式输出，报告实际时长、超限或不足量及文案/正常语速/有意义停顿建议；不截断口播，不填充无意义空白。调整后 SHALL 重新prepare并使相关评审失效。

#### Scenario: 声明合格实际超时
- **WHEN** 声明40秒而TTS与阶段停留合计46秒
- **THEN** 报告实际46秒，不合格且不可正式渲染

#### Scenario: 实际不足
- **WHEN** 实际合计34秒
- **THEN** 报告不足及调整建议，不自动补空白

#### Scenario: 实际边界
- **WHEN** 有效派生总时长恰为35或45秒
- **THEN** 时长维度通过，其他门禁仍需通过
