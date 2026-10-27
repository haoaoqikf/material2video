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
