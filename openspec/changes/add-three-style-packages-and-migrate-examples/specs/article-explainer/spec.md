## REMOVED Requirements

### Requirement: 换站必须有空间过渡

**Reason**: 该要求只约束太阳系一镜到底作品的站点相机与过场路径，属于视频专属制作契约，不是通用讲解能力；继续留在 `article-explainer` 会让通用规格硬编码单一题材。

**Migration**: 原 Requirement 与全部 Scenario 迁入 `deep-journey-style` 的「示例换站必须有空间过渡（视频专属）」Requirement；示例作品路径改为 `styles/examples/deep-journey/solar-system-journey/`。

### Requirement: 太阳系独立行星必须具有清楚的视觉分离

**Reason**: 该要求只约束太阳系示例的独立行星布局与构图，属于视频专属制作契约。

**Migration**: 迁入 `deep-journey-style` 的「示例独立行星必须具有清楚的视觉分离（视频专属）」Requirement，内容与 Scenario 保留。

### Requirement: 太阳系换站必须按段核定简洁连续的节奏

**Reason**: 该要求只约束太阳系示例的换站预算与节奏，属于视频专属制作契约。

**Migration**: 迁入 `deep-journey-style` 的「示例换站必须按段核定简洁连续的节奏（视频专属）」Requirement，内容与 Scenario 保留。

### Requirement: 固定示例的内容驱动演示

**Reason**: 该要求把三个具体作品的题材、时长、帧率、旁白、声音与画面内容写成通用 `article-explainer` 的固定集合；删除顶层 `examples/` 后，路径与“仅分发三个固定示例”的事实不再成立。三个作品的详细内容属于视频专属，不应继续放在通用能力规格。

**Migration**: 通用部分改由本 delta 新增的「随附风格示例集合」Requirement 承担；三个作品的题材内容分别迁入 `doc-archive-style`、`count-ledger-style`、`deep-journey-style` 的「风格示例作品（视频专属，不属于包）」Requirement。路径统一为 `styles/examples/<style-id>/<slug>/`，产物写作品自身 `outputs/`。

### Requirement: 科学里程碑重制必须验证审美流程改进

**Reason**: 该要求只约束 `american-science-milestones` 的十项内容、30 秒结构、LLM 镜头、片尾署名与四张基准，属于视频专属制作契约。

**Migration**: 迁入 `doc-archive-style` 的「科学里程碑示例必须保持内容与审美契约（视频专属）」Requirement，路径改为 `styles/examples/doc-archive/american-science-milestones/`，全部内容与 Scenario 保留。

## ADDED Requirements

### Requirement: 随附风格示例集合

仓库 SHALL 在保留目录 `styles/examples/<style-id>/<slug>/` 分发 5 个随附风格示例：`vibe-night/fold`、`vibe-fable/pigeon`、`doc-archive/american-science-milestones`、`count-ledger/compound-interest` 与 `deep-journey/solar-system-journey`。全部示例 SHALL 为 general v8、1920×1080，并按各自 `project.json` / 分镜显式声明的帧率交付；有旁白示例 MUST 按实际旁白时间窗推进，无旁白示例 MUST 按帧预算推进。示例素材 MUST 经导入留证后按 ID 引用，生成媒体 MUST NOT 入库；观众可见文案 MUST NOT 出现仓库内部路径、`SOURCES.md` 或材料查阅提示；组件覆盖 MUST 按示例实际使用的集合检查，不为了覆盖清单引入无关效果。示例的题材内容契约由对应风格规格的「示例作品」Requirement 约束。

#### Scenario: 五个随附示例可校验

- **WHEN** 对 `styles/examples/` 下的五个示例运行 `m2v validate`，并对有媒体的示例恢复素材后运行 `m2v prepare`
- **THEN** 五个示例均通过 v8 校验，画幅为 1920×1080，帧率与各自 `project.json` / 分镜一致，旁白或帧预算路径符合各自声明

#### Scenario: 生成媒体与字体不入库

- **WHEN** 检查 `git ls-files styles/examples styles`
- **THEN** 不出现 `outputs/`、`assets/media/`、`assets/sound/` 下的生成媒体或字体二进制；恢复配方、分镜、场景与设计文档仍在版本控制中

#### Scenario: 观众文案不暴露内部资料

- **WHEN** 检查五个示例的场景源码与分镜中的观众可见文案
- **THEN** 不出现 `examples/`、`styles/examples/`、`outputs/`、`openspec/`、`.agents/` 路径或“详见/查看/参见文档”式内部指引
