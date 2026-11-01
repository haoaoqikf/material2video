## ADDED Requirements

### Requirement: 阶段指南必须以决策表组织

三份阶段指南 SHALL 以决策表或等价短清单组织，分别回答：

- 方案确定：要决定什么、写入 `DESIGN.md` 哪一块、何时读哪个 skill；
- 制作与迭代：要验证什么、用什么证据、何时调用两个 skill 观察；
- 最终验收：要接受什么、G5/G6 如何执行、问题如何关闭。

阶段指南 MUST NOT 复述通用视觉或运动理论；方法 SHALL 指向项目级 skill，项目特有的叙事、讲解、证据、门禁与类型契约 SHALL 保留活动链接。

#### Scenario: 制作助手进入阶段
- **WHEN** 助手读取当前阶段指南
- **THEN** 能直接定位本阶段要产出的内容和要调用的 skill，不需要先读完整创作手册

#### Scenario: 通用方法更新
- **WHEN** 两个项目级 skill 更新了通用方法
- **THEN** 阶段指南只更新链接或项目验收条件，不复制新的理论段落

### Requirement: 删除文档必须迁移活动路由

删除或合并项目文档时，`guidance-routes.json`、入口、阶段指南、README、ARCHITECTURE、AGENTS 与示例中的活动链接 SHALL 迁移到新权威位置。MUST NOT 留下指向已删除文件或失效锚点的活动链接。

#### Scenario: 合并流程文档
- **WHEN** `creative-production.md` 并入 `production-workflow.md`
- **THEN** 路由、阶段指南、README、示例与测试全部指向 `production-workflow.md` 的活动锚点

#### Scenario: 删除评审文档
- **WHEN** `director-review-and-edit.md` 并入 `visual-review-rubric.md`
- **THEN** G5/G6 与导演审查路由迁移到复核文档，文档可达性测试通过
