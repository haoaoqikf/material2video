## MODIFIED Requirements

### Requirement: 随附风格示例集合

仓库 SHALL 在 `styles/<style-id>/examples/<slug>/` 分发七个随附风格示例：`vibe-night/fold`、`vibe-fable/pigeon`、`doc-archive/american-science-milestones`、`count-ledger/compound-interest`、`deep-journey/solar-system-journey`、`dark-proof/compound-connect` 与 `dark-proof/luck-on-stage`。全部示例 SHALL 为 general v8、1920×1080，并按各自 `project.json` / 分镜声明的帧率交付；有旁白示例 MUST 按实际旁白时间窗推进，无旁白示例 MUST 按帧预算推进。示例素材 MUST 经导入留证后按 ID 引用，生成媒体 MUST NOT 入库；观众可见文案 MUST NOT 出现仓库内部路径、`SOURCES.md` 或材料查阅提示；组件覆盖 MUST 按示例实际使用的集合检查，不为了覆盖清单引入无关效果。示例题材内容由对应风格规格约束。

#### Scenario: 六个随附示例可校验
- **WHEN** 对原有六部随附示例运行 `m2v validate`，并对有媒体的示例恢复素材后运行 `m2v prepare`
- **THEN** 六部示例均通过 v8 校验，画幅为 1920×1080，帧率与材料一致，旁白或帧预算路径符合声明

#### Scenario: 新增暗场示例可校验
- **WHEN** 对 `dark-proof/luck-on-stage` 恢复音效、运行 `m2v validate` 与 `m2v prepare`
- **THEN** 45 秒 v8 分镜与 1920×1080、30 fps 材料有效，准备只引用本示例输入

#### Scenario: 生成媒体与字体不入库
- **WHEN** 检查 `git ls-files styles`
- **THEN** 不出现 `outputs/`、`assets/media/`、`assets/sound/` 下的生成媒体或字体二进制；恢复配方、分镜、场景与设计文档仍在版本控制中

#### Scenario: 观众文案不暴露内部资料
- **WHEN** 检查七个示例的场景源码与分镜中的观众可见文案
- **THEN** 不出现 `examples/`、`styles/`、`outputs/`、`openspec/`、`.agents/` 路径或内部文档查阅提示
