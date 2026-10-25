# 复利

30秒 / 1920×1080 / 30fps / 900帧。黑底、米白资本、金色当年收益与暗金已取收益，以 **1 枚圆片 = 1,000 元** 的圆片柱/丘解释“收益也会产生收益”。无旁白、无旋律配乐；8.0秒进入无旋律环境床，另有28个同步事件音。

同样一万元、假设年收益率固定10%、无追加投入。颜色只表示资金状态：金色是本轮刚赚到、尚未再投入的收益；米白是已进入下一轮、会继续生息的资本；暗金是已取走、离开增长系统的收益。整片只问“金色最后去了哪里”：左侧被取走变暗金，右侧回吸变米白、继续生息。第30年取出组40,000元（10米白+30暗金，排成40枚整块），再投入组174,494元（158.631米白+15.863金），画面同时给出“相差 134,494 元”。结尾回扣第1年赚的1,000元：取走仍是1,000，再投入到第30年是15,863。固定收益率仅作数学演示，不代表实际投资回报，不计税费及通胀。

## 重建

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
