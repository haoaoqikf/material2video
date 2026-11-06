# 复利

29秒 / 1920×1080 / 30fps / 870帧。开场用全屏主题卡“复利的力量”点题，再进入同样一万、两种做法的比较；黑底、米白资本、金色当年收益与暗金已取收益，以 **1 枚圆片 = 1,000 元** 的圆片柱/丘解释“收益也会产生收益”。无旁白、无旋律配乐；8.0秒进入无旋律环境床，另有25个同步事件音。

2026-11-01 按 `frontend-design` / `motion-design` 升级表现层：金色只用于圆片状态、两柱共用对称列轴、四级字阶与命名缓动；数学、时序、声音与圆片计数不变。

2026-11-03 接入最近加入的共享动效组件：S2 当年收益读数随金币从 0 滚到 1,000，S5 结果枚数（40 枚／约 174.5 枚）在 21.0 秒上浮淡入，S6 结论逐字显影；使用共享 `RollingNumber`、`SlideIn` 与 `TextBlock`，数学、分镜、870 帧、相机、事件音与检查点断言不变。

同样一万元、假设年收益率固定10%、无追加投入。颜色只表示资金状态：金色是本轮刚赚到、尚未再投入的收益；米白是已进入下一轮、会继续生息的资本；暗金是已取走、离开增长系统的收益。整片只问“金色最后去了哪里”：左侧被取走变暗金，右侧回吸变米白、继续生息。第30年取出组40枚（10米白+30暗金整块），再投入组约174.5枚（158.631米白+15.863金）；结果屏只给“30 年后的总资产”与两列枚数，随后 S6 硬切到丘顶特写，16枚金片逐枚沉入白堆并变白，拉回后只剩175枚全白本金，再进入结论“让收益，也成为本金。”与片名“复利”。固定收益率仅作数学演示，不代表实际投资回报，不计税费及通胀。

## 重建

前十次圆片落点声明在 `storyboard.json` 的 `scenes[0].events`；场景和对应音效共用 `drop-1`～`drop-10`。修改一项事件帧后重新 prepare，即可共同移动该次落点与声音；落点按整数帧量化。此改动需重新生成与复核，历史成片验证不自动覆盖当前材料。

后续重制按[素材选择规范](../../../.agents/skills/material2video/references/visual-material-selection.md#视频优先与代码适用场景)判断：本片的数量、收益归队与再投入过程适合代码精确合成，无需为视频优先额外寻找外部素材；如新增真实外部画面，再执行视频优先、图片补位。本说明不改变现有作品与评审状态。

```powershell
uv run python examples/data-evolution/compound-interest/assets/fetch.py
uv run m2v validate --project examples/data-evolution/compound-interest
uv run m2v prepare --project examples/data-evolution/compound-interest
uv run m2v preview --project examples/data-evolution/compound-interest --start-seconds 8 --end-seconds 13
uv run m2v render --project examples/data-evolution/compound-interest
uv run m2v qa --project examples/data-evolution/compound-interest
```

成片位于 `examples/data-evolution/compound-interest/outputs/video.mp4`。目录与项目 ID 为 `compound-interest`；不提供旧五选择兼容入口。

- [制作设计与参考迁移](DESIGN.md)
- [数学口径、素材与声音来源](SOURCES.md)
- [验证与制作状态](VERIFICATION.md)

环境床与事件音按 [固定配方](assets/recipe.json) 恢复，已有摘要不符文件拒绝覆盖。视频、声音和评审图片为派生产物，不入库。最终制作结论以VERIFICATION绑定的文件版本为准。

本示例的画面组件与参数保存在本作品 `scenes/`，可独立重建。
