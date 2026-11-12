## MODIFIED Requirements

### Requirement: 随附风格示例集合

仓库 SHALL 在目录 `styles/<style-id>/examples/<slug>/` 分发以下随附风格示例：`doc-archive/american-science-milestones`、`count-ledger/compound-interest` 与 `deep-journey/solar-system-journey`。全部示例 SHALL 为 general v8、1920×1080，并按各自 `project.json` / 分镜显式声明的帧率交付；有旁白示例 MUST 按实际旁白时间窗推进，无旁白示例 MUST 按帧预算推进。示例素材 MUST 经导入留证后按 ID 引用，生成媒体 MUST NOT 入库；观众可见文案 MUST NOT 出现仓库内部路径、`SOURCES.md` 或材料查阅提示；组件覆盖 MUST 按示例实际使用的集合检查，不为了覆盖清单引入无关效果。示例的题材内容契约由对应风格规格的「示例作品」Requirement 约束。

#### Scenario: 五个随附示例可校验

- **WHEN** 对 `styles/<style-id>/examples/<slug>/` 下的五个示例运行 `m2v validate`，并对有媒体的示例恢复素材后运行 `m2v prepare`
- **THEN** 五个示例均通过 v8 校验，画幅为 1920×1080，帧率与各自 `project.json` / 分镜一致，旁白或帧预算路径符合各自声明

#### Scenario: 生成媒体与字体不入库

- **WHEN** 检查 `git ls-files styles`
- **THEN** 不出现 `outputs/`、`assets/media/`、`assets/sound/` 下的生成媒体或字体二进制；恢复配方、分镜、场景与设计文档仍在版本控制中

#### Scenario: 观众文案不暴露内部资料

- **WHEN** 检查五个示例的场景源码与分镜中的观众可见文案
- **THEN** 不出现 `examples/`、`styles/`、`outputs/`、`openspec/`、`.agents/` 路径或“详见/查看/参见文档”式内部指引

> 2026-11-12 内容清理：已删除用户指定作品的专属内容；本档案仅保留其余历史范围，不代表本轮重新验证。
