# 复利

29秒 / 1920×1080 / 30fps / 870帧。开场用全屏主题卡“复利的力量”点题，再进入同样一万、两种做法的比较；黑底、米白资本、金色当年收益与暗金已取收益，以 **1 枚圆片 = 1,000 元** 的圆片柱/丘解释“收益也会产生收益”。无旁白、无旋律配乐；8.0秒进入无旋律环境床，另有25个同步事件音。

同样一万元、假设年收益率固定10%、无追加投入。颜色只表示资金状态：金色是本轮刚赚到、尚未再投入的收益；米白是已进入下一轮、会继续生息的资本；暗金是已取走、离开增长系统的收益。整片只问“金色最后去了哪里”：左侧被取走变暗金，右侧回吸变米白、继续生息。第30年取出组40枚（10米白+30暗金整块），再投入组约174.5枚（158.631米白+15.863金）；结果屏只给“30 年后的总资产”与两列枚数，随后 S6 硬切到丘顶特写，16枚金片逐枚沉入白堆并变白，拉回后只剩175枚全白本金，再进入结论“让收益，也成为本金。”与片名“复利”。固定收益率仅作数学演示，不代表实际投资回报，不计税费及通胀。

## 重建

后续重制按[素材选择规范](../../.agents/skills/material2video/references/visual-material-selection.md#视频优先与代码适用场景)判断：本片的数量、收益归队与再投入过程适合代码精确合成，无需为视频优先额外寻找外部素材；如新增真实外部画面，再执行视频优先、图片补位。本说明不改变现有作品与评审状态。

```powershell
uv run python examples/compound-interest/assets/fetch.py
uv run m2v validate --project examples/compound-interest
uv run m2v prepare --project examples/compound-interest
uv run m2v preview --project examples/compound-interest --start-seconds 8 --end-seconds 13
uv run m2v render --project examples/compound-interest
uv run m2v qa --project examples/compound-interest
```

成片位于 `videos/examples/compound-interest/outputs/video.mp4`。目录与项目 ID 为 `compound-interest`；不提供旧五选择兼容入口。

- [制作设计与参考迁移](DESIGN.md)
- [数学口径、素材与声音来源](SOURCES.md)
- [验证与制作状态](VERIFICATION.md)

环境床与事件音按 [固定配方](assets/recipe.json) 恢复，已有摘要不符文件拒绝覆盖。视频、声音和评审图片为派生产物，不入库。最终制作结论以VERIFICATION绑定的文件版本为准。

本示例未声明可选风格，沿用作品自身设计；风格机制与后续包接入见[风格契约](../../.agents/skills/material2video/references/style-pack.md)。
