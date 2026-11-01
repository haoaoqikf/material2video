## 1. 项目级 skill 落地

- [x] 1.1 新增 `.agents/skills/frontend-design/`，固定官方提交 `ca45fc4`，保存 `LICENSE.txt`、`UPSTREAM.md`、中文 `ADAPTATION.md`。
- [x] 1.2 新增 `.agents/skills/motion-design/`，固定上游提交 `f9a8a04`，保存 `LICENSE`、`UPSTREAM.md`、中文 `ADAPTATION.md`。
- [x] 1.3 调整两个 `SKILL.md` 的 frontmatter 描述到视频语境，并在顶部指向 `ADAPTATION.md`，差异写入 `UPSTREAM.md`。

## 2. 主 Skill 接入

- [x] 2.1 `material2video/SKILL.md` 增加两个条件参考入口。
- [x] 2.2 `guidance-routes.json` 增加条件路由与「视觉审美」「运动设计」规则归属。
- [x] 2.3 `guidance_docs.py` 与路由测试同步新规则归属。
- [x] 2.4 `stage-plan.md`、`stage-iterate.md`、`stage-final.md` 各增加读取时机。
- [x] 2.5 `subagent-review.md`、`checkpoint-gates.md` 写明知识 skill 不改变隔离、轮次与门禁。

## 3. 深度重写重复指导

- [x] 3.1 `creative-production.md` 分层精修改为引用 Frontend Design 的观察—对照—批评与运动质量清单，保留证据、返工与反平庸规则。
- [x] 3.2 `visual-review-rubric.md` 的审美判断方法改为引用两个 skill，保留验收维度与证据闭环。
- [x] 3.3 `explainer-design.md` 增加 Frontend Design 链接，删除与通用视觉设计重复的表述，保留全部项目专属诊断。
- [x] 3.4 `design-tokens.md` 删除死令牌与自定动效时长，改为帧驱动参考与命名曲线。
- [x] 3.5 `reference-style.md` 的 L3 判断补 Frontend Design 链接，八项量化指标保持权威。

## 4. 动效运行时

- [x] 4.1 新增 `web/src/code-scene/motion.ts` 命名曲线库并从 `sdk.tsx` 导出。
- [x] 4.2 `camera.tsx` 替换 `EasingName` 与 `ease()`，`postfx.tsx` 同步改名。
- [x] 4.3 `primitives.ts` 删除缺省线性，要求显式缓动；更新测试。
- [x] 4.4 `styles/*/tokens.json` 的 `cameraEase` 改为新命名。
- [x] 4.5 `code-scene-runtime.md` 更新原语缓动与命名曲线说明。

## 5. 删除死项与入口文档

- [x] 5.1 删除 `tokens.css` 中 `--m2v-dur-*`、`--m2v-safe-bottom-with-subtitles`、`--m2v-size-hero`、`--m2v-size-mega`、`--m2v-ink-numeral`。
- [x] 5.2 更新 `README.md`、`ARCHITECTURE.md`、`AGENTS.md` 的入口与边界说明。
- [x] 5.3 更新 `test_doc_examples.py` 的可达性去重，使同级 skill 可被检查。

## 6. 验证与提交

- [x] 6.1 运行 `uv run python .agents/skills/material2video/scripts/sync_docs.py --check`。
- [x] 6.2 运行 `uv run pytest`。
- [x] 6.3 运行 `pnpm -C web test` 与 `pnpm -C web build`。
- [x] 6.4 检查暂存内容，只提交本变更相关文件。
- [x] 6.5 完成任务后归档并同步 `openspec/specs/`。
