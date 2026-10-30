# 住宅类型移除验证与审查

## 范围与结果

- 正式类型只保留 `financial-timeseries` 与 `general`；住宅目录模板、Python 专用包、Remotion composition、专用测试和制作指南已删除。
- 旧住宅类型初始化和旧清单的校验、准备、预演、渲染、评审模板、评审、状态均明确拒绝；8 个退役用例覆盖错误类型及无产物写入。
- 删除前核验了本地绝对目标 `C:\D_Merged_From_D\project\first-party\material2video\videos\housing-timeseries`，删除后确认不存在；金融与 general 作品目录保留。删除的住宅作品为 `zhengzhou-housing-2002-2024`，内容及产物未加入 Git。

## 验证

- 全量 Python 快测 `uv run pytest -m "not slow" -q` 已执行至结束：1043 项中 1030 项通过、6 项跳过，7 项失败均为该测试进程在修正前已加载的退出码断言。未发现其他失败；修正后按下述相关子集复跑通过，不重复执行未变化的全套。
- 相关 Python 回归：`uv run pytest tests/test_general_type.py tests/test_styles.py tests/test_general_frame_rate.py tests/test_single_pass_delivery.py tests/test_guidance_routes.py tests/test_optional_visual_review.py tests/test_production_gates.py -m 'not slow' -p no:cacheprovider -q` 通过，170 项通过、2 项因当前 Windows 用户不能创建符号链接而跳过，5 项 slow 排除。
- 前端：`pnpm -C web test`，10 个文件、131 项测试通过。
- 构建：`pnpm -C web build` 通过，包含 TypeScript 检查；Vite 提示压缩后包超过 500 kB，不影响构建，本次无新增依赖。
- 文档：`sync_docs.py --check`、阅读路由与预算通过；修改文档 324 个相对链接及 JSON 示例检查通过。
- 契约：`openspec validate remove-housing-timeseries --strict` 通过。
- Git：暂存差异格式检查通过，无新增或修改的二进制、作品媒体、依赖、缓存与凭据。

## 独立审查

执行者：独立子代理 `/root/review_removal`，只读审查代码、测试、制作指南和 delta 规格，未参与实施。

- 关键发现：新增旧作品生命周期测试误将既有 CLI 错误退出码写为 2，已修正为 1；初始化拒绝仍为 2。独立复跑退役测试 8 项全部通过，未发现剩余阻断问题。
- 逻辑影响：旧类型执行路径退出，保留类型继续使用原注册及渲染流程；金融仍使用的共享生命周期与渲染管线保留，仅删除住宅退出后的无调用函数与分支。
- 性能影响：移除专用代码，无新增计算、网络访问、文件 I/O 或依赖；金融与 general 的算法和渲染参数不变。
- 剩余风险：未为本次能力删除重渲染完整影片，slow 真实浏览器/渲染测试未全量执行；符号链接检查受本机权限限制。旧归档中的住宅引用保留为历史，不代表现有能力。
- 代码质量：96/100；扣分主要来自完整渲染未在本轮独立验证。

## 主规格同步与归档

- 实施提交：`283c447`。任务全部完成后同步 7 个能力的 delta，6 个保留能力共更新 17 项要求、重命名 1 项；完整保留原有场景，新增旧住宅类型拒绝场景。
- 退役 `openspec/specs/housing-timeseries/spec.md` 及其 Purpose（年度住宅销售均价独立无声折线类型），删除其最后 2 项要求并移除空目录，已启用 `retire_capabilities: true`。如仅需恢复旧规格文件供查阅，可运行 `git checkout 283c447 -- openspec/specs/housing-timeseries/spec.md`；这不会恢复已删除的本地作品。
- keynote Purpose 清除已退役类型措辞。同步后逐个 delta 比较通过，`openspec validate --specs --strict` 为 44 项通过、0 项失败。
- 按项目约定归档至 `openspec/changes/archive/2026-10-30-remove-housing-timeseries/`；此前归档历史保留。
