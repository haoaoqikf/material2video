# 五种选择，五种人生

约 65 秒、1920×1080、30 fps 的无声横屏作品。世界只有人、道路与世界：同一个白色人物沿同一条道路前进，城市改变机会密度，行业改变地面趋势，伴侣改变方向，投资放大时间差距，学习打开可抵达空间；终幕拉远，五个章节被认回为同一张人生轨迹图。

## 连续事件

| 段落 | 时间预算 | 画面职责 |
|---|---:|---|
| 开场 | 0–6 秒 | 人物行走；几度岔路被拉远放大成两个不同远方 |
| 城市 | 6–16 秒 | 道路、节点与连接生长；另一侧平行人生保持稀疏 |
| 行业 | 16–27 秒 | 两个相同人物同速；一条地面持续上升，一条保持水平 |
| 伴侣 | 27–38 秒 | 第二个人进入；一组轨迹互相修正，另一组拉扯偏离 |
| 投资 | 38–48 秒 | 很小的起点差被时间撑成峡谷与高地 |
| 学习 | 48–57 秒 | 断崖前四次解锁，黑暗地图逐层亮起 |
| 终幕 | 57–65 秒 | 拉远发现同一世界；五个节点分叉出几十条人生轨迹 |

全片无声，无旁白、配乐、音效与素材原声。文字只有开场标题、五个变量名与终幕结论。

## 实现

- `scenes/life.tsx`：React Three Fiber 录制入口、Canvas 与文字层。
- `scenes/world.tsx`：道路、机会网络、移动地形、双轨、生长道路、黑暗地图与终幕分叉树。
- `scenes/lifeMath.ts`：七幕时间表、路径进度、连续镜头、学习解锁与终幕拉远。
- `storyboard.json`：单幕 `life-world`，1950 帧预算与画面文字。

## 重建与复核

```powershell
uv run m2v validate --project examples/five-life-choices
uv run m2v prepare --project examples/five-life-choices
uv run m2v preview --project examples/five-life-choices --start-seconds 0 --end-seconds 8
uv run m2v render --project examples/five-life-choices
uv run m2v qa --project examples/five-life-choices
```

画面基准为 852×479 CSS 像素，另查 393 宽。关键帧与最终候选均需完整时间码证据；独立评审不能依赖审阅界面播放 MP4。生成媒体与评审文件不入库，最终技术与制作结论绑定同一文件摘要。

[视觉设计](DESIGN.md) · [来源与参考边界](SOURCES.md) · [交付验证](VERIFICATION.md)
