## Why

项目现有的视觉判断和动效指导分散在 `visual-review-rubric.md`、`creative-production.md`、`explainer-design.md` 与 `design-tokens.md` 中，缺少统一的视觉设计方法和运动设计方法；同时存在一批与帧驱动契约冲突的实现：`--m2v-dur-*` 无消费方且帧数注释自相矛盾，`primitives.ts` 缺省线性缓动，`camera.tsx` 使用无来源的五条临时曲线。

用户要求把 Claude 官方 `frontend-design` 与上游 `motion-design` 作为项目级 skill 接入，以两个 skill 为准，删除项目中不合理、重复或已死的部分，并同步改造运行时。

## What Changes

- 新增项目级 skill `.agents/skills/frontend-design/`：固定官方仓库 `anthropics/skills` 的 `skills/frontend-design/`，提交 `ca45fc496a3436251f191354091d557da31c15b5`（Apache 2.0）。上游 `SKILL.md` 正文原样保留，新增中文 `ADAPTATION.md` 说明视频语境、观察—对照—批评方法、可用与不可用章节。
- 新增项目级 skill `.agents/skills/motion-design/`：固定上游 `LottieFiles/motion-design-skill@f9a8a04`，上游正文原样保留，新增中文 `ADAPTATION.md` 把 ms 时长、UI 交互章节和动画库建议转译为帧驱动视频规则。
- 主 Skill `material2video` 在入口、阅读路由和三个阶段指南中接入两个 skill；规则归属新增「视觉审美」与「运动设计」。
- 深度重写重复的视觉判断：`creative-production.md` 的分层精修、`visual-review-rubric.md` 的判断方法、`explainer-design.md` 的通用审美表述改为引用两个 skill；项目契约、证据、验收、阶段与审核门禁保持在原文档。
- 运行时新增 `web/src/code-scene/motion.ts` 命名曲线库；`camera.tsx` 的 `EasingName` 与 `primitives.ts` 的缺省线性改为显式缓动契约；风格包 `cameraEase` 同步改名。
- 删除死令牌：`--m2v-dur-fast/base/slow`、`--m2v-safe-bottom-with-subtitles`、`--m2v-size-hero`、`--m2v-size-mega`、`--m2v-ink-numeral`。
- 同步 README、ARCHITECTURE、AGENTS 的入口与边界说明，并扩展文档与动效测试。

## Capabilities

### New Capabilities

- `frontend-design`：项目级视觉设计知识 skill 的触发、证据顺序、视频语境适配、反默认清单边界与不可用 UI 规则。
- `motion-design`：项目级运动设计知识 skill 的帧驱动时长、缓动、编排、风格人格与不可用交互规则边界。

### Modified Capabilities

- `scene-motion-primitives`：原语缓动改为必须显式传入，新增共享命名曲线库，禁止缺省线性。
- `stage-guidance-routing`：入口、条件参考与规则归属新增两个项目级 skill。

## Impact

- 文档：`.agents/skills/material2video/SKILL.md`、`references/guidance-routes.json`、`stage-plan.md`、`stage-iterate.md`、`stage-final.md`、`visual-review-rubric.md`、`creative-production.md`、`explainer-design.md`、`design-tokens.md`、`code-scene-runtime.md`、`subagent-review.md`、`checkpoint-gates.md`、`README.md`、`ARCHITECTURE.md`、`AGENTS.md`。
- 新增：`.agents/skills/frontend-design/`、`.agents/skills/motion-design/`。
- 代码：`web/src/code-scene/motion.ts`、`sdk.tsx`、`cinematic/camera.tsx`、`cinematic/postfx.tsx`、`primitives.ts`、`styles/*/tokens.json`。
- 测试：`tests/common/test_guidance_routes.py`、`tests/common/test_doc_examples.py`、`tests/common/test_project_skills.py`、`web/src/code-scene/primitives.test.ts`、`web/src/code-scene/motion.test.ts`。
- 不涉及：视频类型、材料格式、分镜字段、渲染契约、CLI 命令、审核人数与门禁数量。
