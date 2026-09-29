# 制作流程示例

`production.template.json` 展示《启动摩擦》示例的导演场景分配与待填写评审结构。零值指纹表示待生成；正式作品用命令按当前输入生成记录：

```powershell
uv run python .agents/skills/article2video/scripts/production.py template `
  --storyboard examples/cause-chain/storyboard.json `
  --out videos/examples/cause-chain/production.json
```

完成配音后，重新生成模板并传入 `--media videos/examples/cause-chain/outputs/media/media.json`，再填写角色场景、全片节奏和逐幕起始/变化/结果。关键幕角色可以重合。

已有作品首次接入时也从当前分镜和媒体生成模板；旧版 `review.md` 或历史成片不会自动迁移为新流程的通过结论。修改输入后重新生成相应材料并复评：媒体变化只使动态评审过期，分镜或共享渲染资产变化使静态和动态评审都过期。

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

按联系表和有声样片填写 `reviews`。发现高潮节奏平时，在 `rework` 中增加 `severity: "required"`、`status: "open"` 的条目，并说明问题、修改方向与返回阶段。修改分镜会使所有评审失效，配音变化使动态评审失效。只有在新材料上记录通过结论和依据，才能关闭必改项。`production.py status` 的闸门全部通过后，再运行 `render.py`。仓库只保存抽象模板，不保存运行产物或真实作品评审结果。

返工记录的字段示例（片段）：

```json
{
  "id": "R-TAKEOFF-01",
  "sceneIds": ["takeoff"],
  "dimension": "rhythm",
  "problem": "高潮与前一幕推进速度接近，结果没有停留",
  "direction": "延后最后一步进入，并保留稳定结果帧",
  "returnStage": "motion",
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
