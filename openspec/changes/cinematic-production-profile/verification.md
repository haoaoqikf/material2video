# 验证与审查记录

本文件按阶段记录 cinematic 变更的实施与验证结果。任务全部完成后按项目约定同步主规格、归档并提交。

## 阶段 1：口径修正与文档基线（1.1–1.7）

- 固定示例名单改为 buffer-smoothing、darts-trial-and-error、solar-system-journey，并同步横竖屏与时长描述；`AGENTS.md` 的名单此前已正确，无需改动。
- `media-contract.md` 的「节拍音效当前不渲染」改为「已进入母版混音」，并补一条音效混音验收口径（定位起点、越界失败、叠入后仍按同一响度与真峰值复核、素材摘要进指纹）。
- `PROJECT_PLAN.md` 加入 standard/cinematic 双档位与电影级路线；「复杂转场或第二套渲染引擎」改为「不换引擎，以镜头、后期与母版实现」；保留不自动选曲，明确配乐来自本地素材或确定性程序化音床。
- 新增 `references/cinematic-video.md`：参考板、look bible、镜头语法、材质/后期/声音清单、五阶段门禁、20 项检查表、感知评分卡、反模式与成本表。
- `SKILL.md` 增加档位表、cinematic 触发词、阶段门禁与 look-dev 批准例外（standard 自动通过的唯一例外）。
- `production-workflow.md` 增加 cinematic 分支命令；`visual-review-rubric.md` 增加十项评分卡；`design-tokens.md` 说明 cinematic look 不替代作品自由设计。
- 验证：`sync_docs.py --check` 无漂移；文档相对链接 78 项、JSON 示例 13 项全部有效；`test_doc_examples.py` 与 `test_type_catalog.py` 通过。

**实现状态口径**：阶段 1 只交付文档，cinematic 代码尚未落地，因此参考文档与 `SKILL.md` 都显式标注「实现完成前仓库实际可用的仍是 standard 链路」。该标注在阶段 6 更新为「当前支持」。

## 阶段 2：档位、字段与指纹（2.1–2.7）

- `project.json` 新增可选 `productionProfile`（standard/cinematic，缺省 standard）。非法值在 `general` 类型校验阶段失败；金融与住宅类型显式拒绝 `--profile`，不静默按 standard 处理。
- 档位写入准备记录的 `props.productionProfile` 与 `productionProfileSource`（`default`/`project`/`command-line`）、`inputs.profile`、预演记录与成片溯源的 `productionProfile`/`productionProfileSource`。
- 幕级新增 `leadInFrames`（0–1800）、`tailFrames`（0–1800）、`readingHoldFrames`（0–360）；未声明时阅读停留仍为 24 帧，时间轴与既有行为一致。留白计入幕长，旁白窗口整体后移。
- `content.props.shots` 与 `look` 增加类型/范围/未知字段校验，`narrationSegments[].claims` 校验非空、去重与长度上限；错误按 `scenes[<幕>].content.props.shots[<镜头 id>]` 定位。
- 准备指纹与片段缓存键：档位与 `claims` 只在**非默认**时写进录制配置，standard 作品不声明新字段时缓存键与既有片段逐字节一致；`shots`/`look` 本身在 `props` 内，`leadIn`/`tail`/`readHold` 改变幕长与旁白窗口，都会让旧片段失效。
- CLI 新增 `prepare --profile standard|cinematic`，非法值由 argparse 拒绝；实际来源写入准备记录。

### 与任务措辞的一处偏离（2.3）

任务写「镜头时间窗落在旁白段内」。按 60 秒样例的实际时长分布（9 段旁白各约 5–7 秒）与「hero 必须 8–12 秒连续」的硬要求，把 hero 限制在**单段旁白内**在数学上不成立。因此实现的判定是：

- 每个镜头必须落在本幕时长内；
- **声明** `segment` 的镜头必须**完整覆盖**该旁白段的窗口（这是作者对「这个镜头讲的就是这段旁白」的承诺）；
- 没有声明 `segment` 的镜头只查幕时长——冷开场、收尾与跨段 hero 都属于这一类。

`claims` 与镜头的可见性对应关系由 QA 的 claims 检查负责（每条 claims 必须落在至少一个镜头的时间窗内）。该口径已同步写入 `storyboard-schema.md` 与 `cinematic-video.md`。

## 阶段验证结果

- 完整 Python 回归：收集 532 项、528 项通过、4 项跳过、无失败（阶段 1 结束时为 507 项，阶段 2 新增 25 项）。
- 文档相对链接 78 项、JSON 示例 13 项全部有效；`sync_docs.py --check` 无漂移。
- QA 与资产审计模块以自造小媒体与真实成片双向验证；`lookdev` 的取点、样片窗口与接触表有单元测试覆盖。
