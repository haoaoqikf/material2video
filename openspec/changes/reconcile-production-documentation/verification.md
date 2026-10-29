# 验证与交付审查

## 自动验证

- `uv run python .agents/skills/material2video/scripts/sync_docs.py --check`：通过，生成投影无漂移；正文预算 entry=1410、plan=2567、iterate=1886、final=1495。
- `uv run pytest tests/test_doc_examples.py tests/test_guidance_routes.py tests/test_production_sources.py tests/test_production_gates.py tests/test_vibe_fable_style.py tests/test_vibe_night_style.py -m "not slow" --capture=sys -p no:cacheprovider`：114 passed，6 deselected。
- 首轮测试 1 failed、113 passed：文档测试仍指已删除入口。修正到 stage-plan 后重跑全部上述测试通过，未削弱链接检查。
- 对本次修改的 15 份 Markdown 补查：287 个相对链接（含目录）和标题锚点有效，JSON 围栏可解析；现有路由检查通过。检查脚本仅本次运行，未添加措辞黑名单测试或新检查器。
- `openspec validate reconcile-production-documentation --strict`：通过；主规格同步与归档前后另做规格验证。
- `git diff --check`：本次差异无空白错误。

## 六类场景复核

以下为文档、现有实现和已有测试的契约复核，不声称执行新的视频制作或实际独立评审。

| 场景 | 核对结果 |
|---|---|
| 低风险作品 | 方案充分时直接采用；G4 普通检查、G5 内部全片检查、一次 G6 新代理终审；无候选数量或 G5 独立报告新增要求 |
| 核心动态风险 | core-event 仍在扩展前验证完整动态窗口，端点静帧不能代替；当前候选仍须 G6，原型不授权未覆盖范围 |
| 重复失败 | repeated-failure 仍要求至少两个实质不同的匿名候选和收益损失比较；通用选案无配额不取消该项；策略源码无变更 |
| 有旁白 | 共享字幕由真实旁白派生；不套用无旁白屏幕字幕单行上限；修改后重新 prepare，保持屏幕字幕与同幕旁白互斥 |
| 无旁白屏幕字幕 | 依既有单行、长度、安全区约定及正式包组件实现；独立技术通过不推断理解通过，未修改校验器或 schema |
| 无声作品 | 样片和交付均无音轨，内部静音母版不进入成片；不要求实际配音、音乐或有声响度指标，许可与视觉证据要求不变 |

## 审查结论

- 关键发现：13 类冲突及遗漏已按 reconciliation.md 落定；保留核心方法、强制证据覆盖和风险升级，未调整独立人数策略。
- 逻辑影响：修正文档所要求的执行范围；运行时和公共接口不变，测试仅更新文档入口路径。历史归档与作品专属要求不改写。
- 性能影响：无运行时代码或算法、计算与 I/O 变更；没有声称获得性能提升。
- 剩余风险：语义一致性由逐项人工核对，结构检查不能证明全部自然语言无歧义；未执行完整渲染、慢浏览器测试或成片观感验证。风格 GUIDE 属于既有包指纹输入，使用这些风格的后续操作可能需重新 prepare；本次未迁移作品或改写已有准备记录。
- 质量评分：92/100。扣分来自自然语言审查无法穷尽全部歧义，以及未通过新成片验证实际制作体验；本次修复范围内的结构与策略回归已通过。
- 暂存范围：仅本次文档、测试入口修复及变更材料；排除 create-perfect-step-film 的已有修改，不加入字体、媒体、缓存或凭据。
