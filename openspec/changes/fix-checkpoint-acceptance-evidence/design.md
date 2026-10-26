## Context

现有七门保持不变。仓库中复利作品、README、视觉创意文档由其他任务修改，本任务避开这些已有改动；README 只追加独立能力说明并按补丁暂存，不纳入其他代理的既有段落改动。

## Goals / Non-Goals

完成三项已确认修复。不改精制阶段推断，不优化素材依赖范围，不制作或重渲染视频，不追溯升级在制合同。

## Decisions

- 合同 version 维持 1，新增可选 acceptanceChecks 布尔声明，新作必须为 true；缺省在制合同不追加验收。此为用户要求的在制保护，不是版本迁移层。
- 现有 review 报告新增 acceptance 列表：按 checkpointId、kind、window、status、observations 和证据摘要登记；设计兑现额外登记五个维度及导演条件、关键帧、动画三方证据。机器只校验执行覆盖，不做审美评分。
- G4 核心/A 镜头要求 independent-subagent 的 blind visual-event；可由 G5 批量回绑。设计兑现用单独 consistency 报告绑定 G6，须已有同检查的独立盲审；G6 要覆盖全部核心检查点，不替代原有两名终审。
- 采样提取纯函数，合并步长、文字、可选 statePlan 与 A 级时间结构的边界前后帧，裁到检查点窗口内。statePlan 按局部半开窗声明 expected，复用对象断言逻辑。
- 门保留自身 evidenceStatus/checkStatus；新增 prerequisites 和 ready。自身通过但前置未完成时汇总状态为等待前置，自身过期仅由摘要/依赖变化触发。

## Risks / Trade-offs

- 新增证明材料增加记录成本 → 复用隔离评审与现有事件；不重跑渲染，状态查询只读。
- 对照污染盲审 → consistency 仅在对应独立 blind 观察已有后导入，不计审美通过。
- 边界采样不证明所有连续运动 → 保留密度检查与独立完整窗口评审，不宣称彻底自动验收。
- 同源多角色及摘要不能证明真实审美独立 → 沿用隔离调用的人工执行契约，不自动作美学结论。
