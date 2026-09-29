# 缓冲区标杆示例

六幕水箱隐喻，目标 45–60 秒。分镜中的口播为单一真源；[口播设计](script-design.md) 与 [动作设计](motion-design.md) 记录目的和动作依据。

```powershell
uv run python examples/buffer-smoothing/assets/generate.py
uv run python .agents/skills/article2video/scripts/prepare.py --storyboard examples/buffer-smoothing/storyboard.json
uv run python .agents/skills/article2video/scripts/production.py status --storyboard examples/buffer-smoothing/storyboard.json
```

共享动画工具用法见 [代码场景契约](../../.agents/skills/article2video/references/code-scenes.md)，声音见 [媒体契约](../../.agents/skills/article2video/references/media-contract.md)。声音输入素材的 [CC0 许可](assets/LICENSE.md) 随仓库分发。

本地配音、评审视频、production.json 和成片位于忽略目录 `videos/examples/buffer-smoothing/`。仓库内评审记录用于说明实际验收版本，不应复制为新版本的通过结论；重新生成或修改输入后必须重新评审。
