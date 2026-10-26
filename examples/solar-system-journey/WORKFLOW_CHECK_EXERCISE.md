# 视觉事件与设计兑现：规则演练

这是沿用太阳系题材的**假设情景推演**，不是当前成片的新评审、独立观察或问题关闭证据。不改变本例设计、代码、素材、输出与启动时合同，也不触发重制。规则以[制作流程](../../.agents/skills/material2video/references/production-workflow.md#视觉事件检查)为准。

## 粗片：这个镜头发生了什么值得看的变化？

| 假设情景 | 判定与下一步 |
|---|---|
| 相机靠近一颗球，标签淡入，但原目标中的尺度关系始终不可见 | 只有形式动作，核心变化未成立；回到事件或导演顺序，不以运动流畅放行 |
| 拉远后原本占满画面的地球变成太阳旁的小点，完整窗口清楚建立尺度关系 | 运镜承担尺度发现，可认定有效事件；仍须分别验证理解与表现，不能只看两张端点 |
| 两组距离文字重组，清楚揭示原本混淆的距离口径 | 文字本身承担认知揭示，不因文字主导否决 |
| 结果画面保持，供观众观察已揭示关系 | 按消化用途和时间预算检查，不强制添加移动 |
| 只有建立与结果两张图，不能确认中途关系如何发生 | 证据不足，补完整事件窗口与关键变化帧，不判通过 |
| 事件单独成立，但与前后场连接后揭示提前泄露 | G5 登记跨场问题，调整承接，再复查相关 G4/G5 证据 |

## 精制：导演方案 → 目标关键帧 → 最终动画

假设导演方案要求「先建立地球，再揭示其与太阳的尺度关系」，独立目标关键帧用强烈主体比例与清楚的空间层级表达结果。对照检查如下：

| 假设实现 | 判定与下一步 |
|---|---|
| 最终画面比例接近目标图，但动画只在一闪而过时呈现结果 | 时间兑现失败，修揭示与消化窗口；端点相似不足以关闭问题 |
| 主体比例被改小，标签和光效占据中心，尺度对比被削弱 | 构图、冲击力与注意力未兑现；局部问题回 G4，不以技术 QA 通过关闭 |
| 材质与目标图不同，但主体比例、空间、注意力与时间目标均成立 | 非实质媒介差异可记录依据与收益／损失后保留，无需像素一致 |
| 实现改成另一种核心揭示，作者认为更好，但没有更新目标和评审 | 不能事后改目标放行；更新设计及目标图，重做受影响评审 |
| C 级标题镜头没有独立目标图 | 只核对用途、时间和可读性，图像对照不适用，不伪造通过 |
| 只有制作助手看过方案和动画 | 可记录作者对照，不替代适用的独立评审；缺项仍未完成 |

## 隔离与在制保护

1. 独立评审先只收中性动画证据，记录实际看见的变化。
2. 保存观察后，再收独立 consistency 包（目标图与中性条件）；完整导演方案由制作助手关联，理由与旧结论不入包。
3. 对照不计独立审美通过，G6 仍检查当前文件与必改项闭环。
4. 更新前已启动且未明确启动重制的作品保持原合同，不追加两项验收、不重跑 prepare、不改状态与旧报告。

本演练只验证规则对这些情景的推导结果；不能证明真实动画已达到上述效果。


## 结构化完成凭据示例

以下是报告 `acceptance` 中的单项示例，摘要为占位，必须替换为真实文件摘要才可导入；它不是本例真实评审。新作合同另声明 `acceptanceChecks: true`。

```json
{
  "checkpointId": "scale-result",
  "kind": "design-fulfillment",
  "window": [0, 120],
  "status": "pass",
  "observations": "实际观察与三方对照摘要，不能只写符合设计",
  "evidence": [{"path": "review-pack/example/comparison.png", "sha256": "REPLACE_WITH_SHA256"}],
  "dimensions": {
    "composition-scale": {"status": "pass", "observations": "主体比例与角度的对照证据"},
    "spatial-hierarchy": {"status": "pass", "observations": "前后关系与遮挡的对照证据"},
    "impact": {"status": "pass", "observations": "对比与释放的实际观察"},
    "attention": {"status": "pass", "observations": "关键时刻视觉中心的实际观察"},
    "timing": {"status": "pass", "observations": "建立、揭示与消化时机的实际观察"}
  },
  "design": {
    "direction": [{"path": "review-pack/example/neutral-conditions.json", "sha256": "REPLACE_WITH_SHA256"}],
    "keyframes": [{"path": "design/keyframes/scale.png", "sha256": "REPLACE_WITH_SHA256"}],
    "animation": [{"path": "review-pack/example/window.mp4", "sha256": "REPLACE_WITH_SHA256"}]
  }
}
```

视觉事件项使用相同 checkpointId/window/status/observations/evidence，kind 改为 `visual-event`，省略 dimensions 和 design。它在 G4/G5 的 blind 报告内导入；设计兑现在 G6 的 consistency 报告内导入，须先有同一 checkId 的独立 blind 观察。两个报告仍使用[检查点契约](../../.agents/skills/material2video/references/checkpoint-gates.md#表达检查的完成凭据)规定的完整字段。

| 修复验证情景 | 应得到的结果 |
|---|---|
| 启用合同，核心镜头只有通用独立通过报告 | G4 待评审，missingAcceptance 列出 visual-event |
| 只有两名终审，没有五维对照 | G6 待评审，不以技术或盲审通过替代兑现 |
| 先交对照，后补独立盲审 | 对照导入失败，保持先观察后对照 |
| 凭据证据文件被替换 | 旧凭据不再计入有效覆盖，需当前证据 |
| 文字只在步长之间的一帧出现 | 自动补出现、离开及前后帧，核对闪现状态 |
| 状态计划中途错数但结果帧正确 | 中途断言失败，不能以端点放行 |
| G1 自身通过，但缺 G0 | evidenceStatus=通过，status=等待前置，prerequisites 包含 G0 |
| G1 合同摘要实际改变 | evidenceStatus/status=过期，补 G0 不会修复旧证据 |
| 更新前在制合同未声明 acceptanceChecks | 不补本轮新凭据要求，不重写既有制作证据 |
