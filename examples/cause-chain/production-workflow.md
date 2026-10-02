# 制作流程示例

`production.template.json` 展示《启动摩擦》示例（v4 单场景树世界，四个阶段 `claim`／`loop`／`turn`／`reverse`）的导演阶段分配与待评审结构。当前制作标准是正文与最终口播各130～170字（目标约150字），声明和媒体实际成片各35～45秒。

先在口播改写和分镜前审查文章长度、核心观点集中度与单场景适配。AI 阅读原文后记录观点、建议隐喻和依据；失败或依据不足时保留原文、给出意见和合规候选稿并停止。只有用户明确采用候选稿且重新审查通过后才进入制作。已确认的制作输入通过后，正式作品首次接入时按当前分镜生成记录；已有记录不要直接重建模板，以免丢失返工和历史记录：

```powershell
uv run python .agents/skills/article2video/scripts/production.py template `
  --storyboard examples/cause-chain/storyboard.json `
  --out videos/examples/cause-chain/production.json
```

输入审查命令与候选采用步骤见[输入文章审查](../../.agents/skills/article2video/references/input-review.md)。

完成配音后，AI 助手读取文章、分镜与 `review.md` 里的画面结论自动填写关键幕角色、全片节奏和逐阶段起始/变化/结果。关键幕角色可以重合；本示例的关键幕是 `claim`（opening）、`loop`（core）、`turn`（climax）。

AI 助手必须生成并打开联系表、关键幕样片和全片有声评审版，查看实际画面后才能填写评审；缺少或打不开所需画面时保持 `pending`。每项完成的评审写入 `assessment`，标注 `reviewer: "ai"`、模型与会话标识，以及支持结论的材料 SHA-256。旧版 `review.md` 或历史成片不会自动迁移为当前版本的通过结论。修改输入后重新生成相应材料并复评：媒体变化只使动态评审过期，分镜或共享渲染资产变化使静态和动态评审都过期。

静态材料按分镜声明时长生成；关键幕样片和全片有声评审版按实际媒体时间轴生成：

```powershell
uv run python .agents/skills/article2video/scripts/production.py keyframes `
  --storyboard examples/cause-chain/storyboard.json
uv run python .agents/skills/article2video/scripts/production.py samples `
  --storyboard examples/cause-chain/storyboard.json `
  --media videos/examples/cause-chain/outputs/media/media.json
uv run python .agents/skills/article2video/scripts/production.py rehearsal `
  --storyboard examples/cause-chain/storyboard.json `
  --media videos/examples/cause-chain/outputs/media/media.json
```

静态评审的 `assessment.materials` 引用 `keyframes` 摘要，关键幕动态评审引用 `samples`，全片动态评审引用 `rehearsal`；摘要从对应 `materials.*.sha256` 复制。发现问题时在 `rework` 增加带问题、修改方向与返回阶段的条目；必改项保持打开直至新版本复查通过。修改分镜会使所有评审失效，配音变化使动态评审失效，引用文件被替换也会使评审过期。`production.py status` 的门禁全部通过后，再运行 `render.py`。仓库只保存抽象模板，不保存运行产物或真实作品评审结果。

返工记录的字段示例（片段）：

```json
{
  "id": "R-LOOP-01",
  "sceneIds": ["loop"],
  "dimension": "静态构图",
  "problem": "闭环箭头压住顶部卡片文字",
  "direction": "改用 flow 链与 connector 回路箭头，避免几何重叠",
  "returnStage": "loop",
  "severity": "required",
  "status": "open"
}
```

修改并重新试制后，才可把该项改为以下复查形式；`fingerprints` 三个值必须逐字复制当前 `production.json`，不可使用旧版本：

```json
{
  "status": "resolved",
  "recheck": {
    "status": "pass",
    "evidence": "全片预演中最后一步结束后停留 18 帧，结果完整可读",
    "fingerprints": {
      "storyboard": "当前分镜指纹",
      "assets": "当前共享资产指纹",
      "media": "当前媒体指纹"
    }
  }
}
```
