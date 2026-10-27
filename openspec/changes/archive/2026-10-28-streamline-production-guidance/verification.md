# 流程验证记录

## 范围

本次修改共享 Skill 指导文档、文档投影检查脚本、production 过程证据校验与相关测试；
没有修改公共 CLI、报告字段、合同版本、审核人数、动画能力、固定示例或作品成片。

## 指导整理

- 入口 `SKILL.md` 正文 1278 字符（预算 2000），四份阶段指南 966/768/831/694（预算 3000），
  入口加阶段最大 2244（预算 5000）。
- 阅读路由 `references/guidance-routes.json` 登记 4 个阶段、4 类任务、16 项条件参考、
  3 个类型分流与 7 条规则归属；`guidance_docs.py` 校验目标存在与越界、标题锚点、阶段唯一性、
  触发条件非空与结构版本。
- 长文档拆分：`visual-creative-direction`、`visual-review-rubric`、`reference-video-analysis`、
  `subagent-review`、`code-scene-runtime`、`production-workflow` 的模板、案例与排错按区间原文
  迁至相邻参考文件，原位置保留转介；`rule-migration.json` 记录每段字符数与 sha256，逐段核验
  原文在目标文件中完整存在（七段式一节仅将文内相对锚点改为跨文档链接，已在该条 `adapted` 注明）。
  `entry-migration.json` 记录入口删除的五节及各自的权威落点。
- 修正 4 处活动文档失效引用：`visual-creative-direction-examples.md` 的相对锚点、
  `video-revision.md` 指向已删除的 `SKILL.md#音色选择`/`#常用命令`、`scene-design-and-acceptance.md`
  与 `subagent-review.md` 的 `#设计对照终审同轮`（真实锚点为 `设计对照核心与终审同轮`）。
- 文档检查器忽略模板围栏内的占位链接，避免 `visual-review/risk.mp4` 一类填写示例被误判为活动引用；
  预算上限改为显式常量，并分别定位入口、阶段与合计超限。

## 媒体证据

- `production/media_evidence.py` 只解码主视频流（`-map 0:v:0`）读取长度，纯音频、伪装与损坏
  文件分别给出可读诊断；一帧容差；同次操作缓存成功与失败，不跨查询缓存。
- 报告导入（`acceptance.validate`）与当前状态（`ledger.status`）共用同一校验；坏证据使当前制作
  完成为 false 并列出文件与检查点，历史事件与候选文件不改写，静态检查点不探测视频。
- 未新增系统 `ffprobe` 前提：改用依赖内自带的 ffmpeg（CI 环境无 ffprobe，旧实现会必然失败）。

## 独立规则保全复查与修复

独立只读子代理按入口可达性、迁移逐段比对与强制语气逐项核验，报告的问题已全部修复
（提交 `29232fa`）：

- 住宅类型原先只路由到 `catalog.json` 的材料模板，`housing-timeseries-video.md` 成为不可达的
  孤儿文档；现路由、入口与 README 导航均指向该契约，类型文案带链接。
- 「新增视频类型」的三条操作契约在删除后无真实落点，迁移记录声称的 README 权威不实；
  现写回 `ARCHITECTURE.md#契约与文档`，并修正记录。
- 动态核心过程片段的容量判据原先只存在于阶段短指南，而检查点契约自称唯一依据；现落到
  `checkpoint-gates.md` 与 `subagent-review.md#评审包`，阶段指南保留摘要。
- 方案确定阶段缺 G2 目标关键帧盲审，评审入口会把该轮跳过；现已补入 `stage-plan.md`。
- 补回三条入口级规则：生成产物不能代替可编辑材料、按需检查工具不是完整渲染前置、
  评审帧包从片段或正式成片抽取。
- 音色「用户明确指定优先」在配音契约无落点且有悬空指向；现补入并改链。
- `style.id` 定向改读 `style-pack.md`；SKILL 恢复类型表表头与显式指针；复利示例补指针。
- 迁移记录改用 LF 口径重算基线摘要（原记录混用 CRLF 与 LF，不能自证），并注明
  `production-record-template.md` 一条只迁代码块、该节规则仍留在制作流程。

复查后重跑：`sync_docs.py --check` 通过（entry=1465、plan=1326、rough=928、refine=882、
final=1267）；`pytest -m "not slow"` 904 passed、5 skipped、47 deselected；
`openspec validate --specs --strict` 39 项通过；全部活动文档链接与锚点复查无失效。

## 独立代码复查与修复

独立只读子代理审查过程证据实现，报告的可复现缺陷已全部修复（提交 `f806980`）：

- 起始 PTS 偏移会把 1 秒画面读成 5 秒并放行（`-itsoffset` 样本实测 5.0）；
  现归零首帧后按帧数换算，同类样本读出 1.000000s 并被拒绝。
- 60fps 下不足一帧被微秒截断误拒（59/60 帧测为 0.983333s），30fps 同构造
  只是截断方向相反才通过；量化误差容忍改为 1e-5，两档 fps 均有边界用例。
- 畸形 `window`（长度 1 的列表）抛未捕获 `IndexError`，使 `m2v status` 崩溃；
  现校验为两个递增数值，其余转可读诊断。
- 同一检查点同时有无效与有效通过时，状态既判通过又列出「动态过程证据无效」；
  现只在没有任何有效通过时追加原因并去重。
- 同一检查点绑定 `core-event` 时，G0/G1/G2/G3 的核心报告也被要求视频；现只在
  G4 动态核心轮探测。
- 失败缓存改存原因字符串，不再复用异常实例，避免 traceback 串到首次调用点。

复查后重跑：`pytest -m "not slow"` 923 passed、5 skipped、48 deselected；
`sync_docs.py --check` 通过。

## 验证

- `python .agents/skills/material2video/scripts/sync_docs.py --check`：生成文档一致，阅读预算通过。
- `python -m pytest -m "not slow"`：887 passed、5 skipped、47 deselected。
- 新增 `tests/test_media_evidence.py`（伪装/纯音频/过短/一帧容差/静态豁免/失败缓存与跨操作重验/
  状态只读重验）与 `tests/test_guidance_routes.py`（路由、锚点、触发、预算、归属 16 项）。
- `tests/test_doc_examples.py` 改为按「自入口经阶段指南与路由可达」判断，不再要求专项文档直接
  出现在 `SKILL.md`。
- `openspec validate --specs --strict`：38 项全部通过；`openspec validate streamline-production-guidance --strict` 通过。
- 全部活动文档相对链接与标题锚点复查通过（仅 `openspec/specs/` 目录链接按目录存在）。

## 限制

- 导航与预算检查只证明文档结构与可达性，不证明制作助手实际读到或正确理解规则。
- 媒体容量只证明片段可解码且不短于检查窗，不证明时间窗对应、连续性或讲解成立。
- `test_reference_douyin.py` 在 Windows 上偶发临时文件权限失败，单独重跑通过，与本次改动无关。
