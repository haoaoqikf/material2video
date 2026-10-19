# 从电报到大模型

60秒无声历史纪录短片，1920×1080、60 fps、cinematic；固定示例总数保持三个。

画面以真实档案与实物照片为主，原理动画为辅。每项保留年份、短名称和压缩后的贡献说明，但按素材特征采用全幅、留边、细节、示意或镜头承接等不同处理，避免十页同构信息卡片。无旁白、配乐、音效与素材原声；当前链路生成数字静音音轨，最终峰值必须为0。全片只在片尾出现一份简短署名与版权说明，画面中不出现仓库文件名、路径或制作文档指引。

## 逐幕内容与组件

| 场景ID | 时间 | 内容 | 画面与组件 |
|---|---|---|---|
| `opening` | 0–3秒 | 从电报到大模型 | 全幅首飞档案、React / Motion / 帧驱动推移 |
| `telegraph` | 3–7秒 | 摩尔斯电报 | 竖幅实物、React / SVG / 摩尔斯信号带 |
| `telephone` | 7–11秒 | 贝尔电话 | 压暗档案背景、实物画框、React / ECharts 波形 |
| `flight` | 11–19秒 | 莱特兄弟飞机 | 全幅档案横移、React / 帧驱动构图 |
| `trinity` | 19–23秒 | 原子弹 | 竖幅档案、缓慢推进、React / 帧驱动构图 |
| `eniac` | 23–27秒 | ENIAC计算机 | 全幅机柜横移、指示灯、React / 帧驱动构图 |
| `transistor` | 27–31秒 | 晶体管 | 实物细节、截面示意、React / SVG |
| `moon` | 31–39秒 | 阿波罗登月 | NASA 连续影像原速播放、React / 帧驱动 |
| `arpanet` | 39–43秒 | ARPANET | 1970年档案图、初始四节点示意、React / SVG |
| `genome` | 43–47秒 | 人类基因组计划 | 全幅历史照片、双螺旋示意、React / SVG |
| `llm` | 47–55秒 | 大语言模型 | 抽象计算网络、React / SVG，原理示意 |
| `closing` | 55–60秒 | 每一次突破，都有来路。 | 年代刻度、唯一片尾署名、React / Motion / 帧驱动 |

## 制作与重建

```powershell
# 归档素材已内容寻址保存；缺失时按下述脚本重新获取并导入。
uv run python examples/american-science-milestones/assets/fetch.py
uv run m2v validate --project examples/american-science-milestones
uv run m2v prepare --project examples/american-science-milestones
uv run m2v assets audit --project examples/american-science-milestones
uv run python examples/american-science-milestones/scripts/render-rough.py
uv run m2v lookdev --project examples/american-science-milestones --stills 3 --sample-seconds 24
uv run m2v render --project examples/american-science-milestones
uv run m2v qa --project examples/american-science-milestones
```

成片位于 `videos/examples/american-science-milestones/outputs/video.mp4`。源代码、分镜、设计和登记素材入库；生成成片、静帧及缓存不入库。

[视觉设计](DESIGN.md) · [史实与素材来源](SOURCES.md) · [交付验证](VERIFICATION.md)

本示例代码及文案按仓库许可分发；影像素材分别遵循来源许可。成片作为含CC BY-SA素材的改编视听作品按CC BY-SA 4.0分发，署名集中在片尾一处；不暗示任何机构背书。
