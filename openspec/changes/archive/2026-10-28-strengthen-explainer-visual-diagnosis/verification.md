# 验证记录

## 变更 A：strengthen-explainer-visual-diagnosis

### 文档检查

```powershell
uv run python .agents/skills/material2video/scripts/sync_docs.py --check
# 生成文档与权威来源一致，无需改动
# 阅读预算（正文字符）：entry=1278、plan=1111、rough=928、refine=831、final=1206
```

预算均在上限内（入口 2000、阶段 3000、合计 5000）。新增 `visual-diagnosis.md` 不在阶段预算内，作为条件路由按需展开。

### 单元测试

```powershell
uv run pytest tests/test_doc_examples.py tests/test_guidance_routes.py -q
# 26 passed
```

- 路由目标、标题锚点、触发条件、规则归属全部可解析。
- `visual-diagnosis.md` 的相对链接（`explainer-design.md#找一个形象`、`reference-style.md`、`checkpoint-gates.md`）与新增锚点 `一症状--成因--改法`、`二画得像它本身` 均校验通过。

### 全量快速回归

```powershell
$env:PYTHONIOENCODING='utf-8'; uv run pytest -m "not slow" -q -p no:randomly
# 100% passed（含 4 个 skip）
```

注：未设 `PYTHONIOENCODING=utf-8` 时，pytest 捕获子进程 GBK 输出会抛 `UnicodeDecodeError` 并记为 ERROR，但单独运行同一文件全部通过。这是终端编码问题，与本次改动无关。

### 规则保全核对

「可见变化」七类定义现在只有 `visual-creative-direction.md#5-可见变化` 一处权威。逐处核对被改写的摘要：

| 文件 | 改后保留的结论 | 权威定义中的对应原文 |
|---|---|---|
| `creative-production.md` | 每个抽象观点至少对应一种可见变化，禁止只显示名称、图标或说明文字 | 「只显示名称、图标或说明文字不算」 |
| `production-workflow.md` | 至少一种可见变化 | 「每个核心观点至少一种」 |
| `article-to-storyboard.md` | 至少一种可见变化 | 同上 |
| `scene-design-and-acceptance.md` | 「出现某个对象」不算可见变化 | 同「只显示名称…不算」 |
| `explainer-design.md` | 七类之一 | 表格七行 |
| `visual-review-rubric.md` | 至少一种可见变化 | 同上 |

未丢失任何判定口径；六处均保留可自查的一句结论，不依赖跳转。

### 未覆盖项

- 未做视频实际制作验证：本变更只改文档与阅读路由，判据与门槛表的实际使用效果须在后续作品制作中检验。
- 独立子代理评审未执行：本变更为文档与导航层改动，不改变任何验收门禁、渲染契约或审核职责，按 `AGENTS.md`「简单变更不降低交付要求」执行验证、同步文档与提交，未新增评审轮次。
