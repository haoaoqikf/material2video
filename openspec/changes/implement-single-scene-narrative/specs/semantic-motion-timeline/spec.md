## Purpose

以全片唯一 beat 与状态时间轴同步口播、对象、镜头、字幕和媒体派生阶段。

## MODIFIED Requirements

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

### Requirement: 时间轴必须支持跨阶段连续对象
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

## ADDED Requirements

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
