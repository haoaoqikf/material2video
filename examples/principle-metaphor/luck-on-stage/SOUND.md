# 事件音

41 秒，无旁白和配乐。声音与 `storyboard.json` 的命名事件同源：`contact` 表示接触/落定，`travel` 表示迁移/面积展开，`tick` 与 `rolling` 组织记录节拍，`spark` 对应命中或比例锁定，`release` 强调最终比较。高频计数不逐数字叠加完整音效。

六项 CC0 原创合成声源按 `assets/sound-recipe.json` 和固定摘要 `assets/sound-checks.json` 恢复。当前音轨的响度、峰值、时长及检查范围见 [VERIFICATION.md](VERIFICATION.md) 与本目录 `outputs/qa.json`；技术信号不能代替主观听感。

本轮沿用六项声源：开场命中音跟随 `hit-land`，桥段仅在 `portal-enter` 触发低声迁移；去掉两次口号入场音。结尾的 `factor-one` 用轻刻痕节拍，`factor-two` 用轻亮点，均低于公式 `formula-lock` 的主爆。面积9落定保留轻接触，公式主爆仍最强。尾部约39.5秒起保持安静。未复制参考音轨。

三柱段的 `three-start` 与 `nine-start` 仍是起跳迁移声；接触声分别改绑 `three-land`（局部第90帧）与 `nine-land`（第150帧），与球底点抵达、压缩及闪释同帧。`three-lock` 和 `nine-lock` 仅标记柱体生长完成，不再制造延迟接触声。
