# 键盘与火花音效演练

此配方演示新音效链路，独立于本示例的无声成片。将本示例复制到忽略的作品目录（例如 `videos/documentary-edit/sound-exercise`），仅在副本中导入和编辑分镜；不要修改示例成片的无声契约。

```powershell
uv run m2v author sounds catalog
uv run m2v author sounds import --project videos/documentary-edit/sound-exercise --manifest examples/documentary-edit/american-science-milestones/assets/sound-exercise.json
uv run m2v author sounds audit --project videos/documentary-edit/sound-exercise
```

副本分镜中的播放示意（用副本的实际幕 ID 替换 `demo-scene`；60fps，先打字，3秒后右侧火花）：

```json
{
  "soundtrack": {
    "effects": [
      {"assetId": "typing-demo", "sceneId": "demo-scene", "offsetFrames": 0, "gainDb": -12},
      {"assetId": "spark-demo", "sceneId": "demo-scene", "offsetFrames": 180, "gainDb": -16, "pan": 0.7, "fadeOutMs": 30}
    ]
  }
}
```

打字配方的 `eventsMs` 对齐画面按键时间点，镜头至少覆盖火花尾部；切换fps时重新换算 `offsetFrames`。执行 `prepare` 后检查母版波形、实际起点、声道和长度；完整视觉制作仍遵循制作手册。本演练不是已完成听感或视觉评审的作品。

代码合成输出为原创风格化拟音，按 CC0-1.0 使用，生成 WAV 和来源记录留在副本内，不入库。第三方实录的导入格式见[音效库契约](../../../../.agents/skills/material2video/references/article-media-and-sound.md#统一音效库)。
