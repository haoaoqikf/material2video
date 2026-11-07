# 验证记录

## 自动检查

- `sync_docs.py --check` 通过：生成块与权威来源一致，导航、JSON 示例及正文预算有效；入口 1556、研究 2202、设计 997、制作 849 字符。
- `quick_validate.py .agents/skills/material2video` 通过。首次因运行环境缺 PyYAML 未启动校验，随后用 `uv run --with pyyaml python -X utf8` 临时环境完成，未改变项目依赖。
- `python -m py_compile src/m2v/production/reviews.py` 通过。
- OpenSpec 本变更严格校验通过。
- 实施提交 `c8fe1b31` 后，同步 3 份主规格、4 个既有 requirement，逐块核对增量且保留全部原场景；`openspec validate --specs`：38 份规格通过。这是规格结构检查，不是全仓测试。
- 定向 pytest 首轮 9 个用例中 8 个通过，链接检查发现示例遗留的 10 处旧流程链接；修正相关 5 份文档后仅重跑失败节点，1 个通过。不同用例合计 9 个通过，未运行全仓回归。

覆盖节点：

```text
tests/common/test_guidance_routes.py::test_current_routes_and_budgets_pass
tests/common/test_doc_facts.py::test_tracked_markdown_links_and_anchors_resolve
tests/common/test_doc_facts.py::test_open_specs_are_retired_only_through_archive
tests/common/test_media_reviews.py::test_local_trial_without_design_or_board_and_readonly_state
tests/common/test_media_reviews.py::test_reference_without_observable_conditions_is_rejected_before_pack
tests/common/test_media_reviews.py::test_target_comparison_follows_own_blind_observation
tests/common/test_media_reviews.py::test_neutral_conditions_are_withheld_until_blind_import
tests/common/test_media_reviews.py::test_removing_target_cannot_close_original_visual_failure
```

第 5 个节点有两个参数用例。首次 pytest 的缓存写权限警告不影响测试断言；失败节点重跑禁用缓存插件。

## 独立变更审查

新上下文代理 `selection_change_review` 审查全部差异、规格、报告导入逻辑和相关测试覆盖。发现一处 P3：研究指南仍用“验证可实现性”，弱于要求实际重现；已修复并经该代理定点复核关闭，无剩余已知发现。

逻辑变化限于包内人读提示：trial 增加人工选案依据，consistency 区分参考用途并保留整体品质。review v2 字段、摘要、隔离、失败关闭规则及 final 待验范围不变。性能仅增加少量提示文本，无新增依赖、渲染或媒体 I/O。代码与流程审查评分 95/100；剩余限制是人读提示依赖执行者判断，不能由单元测试证明实际审美提升。

## 行为演练

演练不导入正式评审，不改写历史通过或失败，不将静态观察扩为动态和声音结论。

### 真实静态任务的接续决定

新上下文代理 `selection_forward_trial` 接收用户原始“按新流程重新设计，只设计看图片”请求、当前技能及已有六张静态稿。先只读取匿名媒体清单的 6 张原生图和 6 张 393 宽图，保存盲看；随后读取原中性条件、原研究已选参考用途及 3 张实际参考图。没有提供用户此前否定、作者推荐、旧 pass 或预期拒绝答案。

盲看发现前两张拱体/时间轴有主体吸引力，后四张主要回到大数字与图表；六个不同场景不足以证明同内容候选已比较。对照后确认已有暖浅底、独立主体、分层轮廓和主信息可读，但认为橙色层面厚且均匀、明暗与层缝不足，柱面细分仍主要是平面竖纹。原条件解答了账户数值语义疑问，但画面中持续投入区间仍宜更明确。

实际决定为“值得集中打磨，当前不作为后续完整设计品质标准”；下一步只用关键终值对照内容试制一个主体由层片/细分单元构成的静态候选，保留零基线和高度金额编码，再与现稿和参考比较。没有建议批量加效果或补无关动态。其从具体差距导出了单场试验，而非凭局部特征兑现继续铺开。

原始清单、摘要、真实时间与观察保留在作品忽略区 `outputs/selection-workflow-eval-20261107/` 的 `blind/`、`comparison/`、`blind-observations.md` 和 `comparison-observations.md`；不提交图片、文章或旧评审。演练只验证这一次任务的观察与下一步决策，未实际返工出新图，没有旧/新流程对照实验，不能证明审美已提升、耗时已减少或今后都能选出好方案。

### 局部修订边界

新上下文代理 `selection_revision_trial` 仅接收当前技能与模拟任务：已有有效实际基线，只将第 2 张图的一个错字改正，其他按原设计。没有提供期待答案或本次变更说明。

代理选择按局部简单修订推进：先确认“第 2 张图”的来源，不直接等同第 2 场；复用有效研究/基线，不重开选案或周期；只重出受影响图片，核对文字、排版和手机尺寸，过期证据按实际范围补取，不以旧通过替代。没有擅自生成全片或宣称已经改图。该项验证的是决策边界，未实际修改或渲染作品。
