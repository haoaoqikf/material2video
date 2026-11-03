## Context

`openspec/specs/` 是当前产品行为的权威。调研发现同一行为被多份规格重复描述，且旧事实未随实现更新。本变更只处理规格权威与文档事实，不改变运行时行为。

## 决策

### 1. general 以 `article-explainer` 为唯一规格

`article-explainer` 已被 `prepared-and-subtitles.md`、`storyboard-schema.md` 与 `video-production-workflow` 明确引用为 general 行为来源；`general-video-composition` 在仓库现行文档中没有被引用，且其“初始化 60 fps”与代码、`video-frame-rate`、`article-explainer` 的 30 fps 冲突。

迁移方式：
- `article-explainer` 新增三条要求，内容取自 `general-video-composition`，并按当前实现修正：
  - 统一制作契约（拒绝 `productionProfile`/`--profile`、旧字段与旧模板；保留 shots/look 与缓存失效规则）；
  - 无声音声明作品交付零音频流；
  - 运动载体优先。
- `general-video-composition` 的四条要求全部移除。其 v8 自由代码场景要求已由 `article-explainer` 的 v8 要求覆盖，不重复迁入。
- 归档后删除 `general-video-composition` 规格目录，避免留下无要求的空能力。

### 2. 路径迁移只由 `article-workspace` 维护

两份规格的“逐作品路径迁移”文本与场景高度重复。`article-workspace` 负责工作区、内容根与归属推导，迁移属于其职责；`modular-video-production` 的统一入口要求仍保留 `relocate` 命令，但不重复定义迁移细节。

### 3. 示例名单只由 `article-explainer` 维护

`article-explainer` 的“随附风格示例集合”已包含名单、通用校验、素材留证与不入库要求；`vibe-fable-style` 只保留风格包自身的示例声明、旁白/文字模式和指纹隔离，不再复制名单。

### 4. 过期事实直接修正，不保留历史分支

- 现行规格描述当前行为，不保留旧版本兼容叙述；v4 分镜、旧迁移范围与“两个/三种示例”均改为当前事实。
- Purpose 中的 TBD 直接补写；不新增“历史说明”章节，历史细节留在归档变更与作品验证记录中。

### 5. 独立评审口径对齐代码

`checkpoint-gates` 与 `ledger.py` 只把 `isolation=independent-subagent` 计为独立；`subagent-review` 把“外部评审”列为执行方式，容易被读成可替代独立子代理。修改参考文档明确计数规则，不改变门禁与代码。

## 风险与边界

- 本变更不动代码、材料、渲染、命令参数或审核人数；风险主要在规格文本迁移遗漏。
- 验证时逐条核对被移除要求的独有内容是否已在 `article-explainer` 或 `article-workspace` 中存在。
- 不处理六个风格规格与 GUIDE 的参数重复；该问题需要逐包重写验收条款，另立变更。
- 不处理 `openspec/changes/archive/` 中的历史路径与旧倍率；历史记录不改写。

## 验证

1. `openspec validate consolidate-duplicated-spec-authorities --strict` 通过。
2. 归档前后 `grep` 确认没有文档再引用 `general-video-composition`。
3. `sync_docs.py --check` 通过。
4. 相对链接与锚点检查通过。
5. 运行默认测试层；本变更不改代码，测试用于确认没有意外产品契约变化。
