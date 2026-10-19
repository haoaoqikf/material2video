# 从电报到大模型

120秒无声历史纪录短片，1920×1080、60 fps、cinematic；替换原缓冲示例，固定示例总数保持三个。

画面以真实档案与实物照片为主，原理动画为辅。每项依次显示年份、名称和一句说明；无旁白、配乐、音效与素材原声。当前链路生成数字静音音轨，最终峰值必须为0。

## 逐幕内容与组件

| 场景ID | 时间 | 内容 | 画面与组件 |
|---|---|---|---|
| `opening` | 0–6秒 | 从电报到大模型 | React / Motion / SVG / 帧驱动档案运动 |
| `telegraph` | 6–16秒 | 摩尔斯电报 | React / Motion / SVG / 帧驱动档案运动 |
| `telephone` | 16–26秒 | 贝尔电话 | React / Motion / ECharts / SVG / 帧驱动档案运动 |
| `flight` | 26–36秒 | 莱特兄弟飞机 | React / Motion / SVG / 帧驱动档案运动 |
| `trinity` | 36–46秒 | 原子弹 | React / Motion / SVG / 帧驱动档案运动 |
| `eniac` | 46–56秒 | ENIAC计算机 | React / Motion / SVG / 帧驱动档案运动 |
| `transistor` | 56–66秒 | 晶体管 | React / Motion / SVG / 帧驱动档案运动 |
| `moon` | 66–76秒 | 阿波罗登月 | React / Motion / SVG / 帧驱动档案运动 |
| `arpanet` | 76–86秒 | ARPANET | React / Motion / SVG / 帧驱动档案运动 |
| `genome` | 86–96秒 | 人类基因组计划 | React / Motion / SVG / 帧驱动档案运动 |
| `llm` | 96–106秒 | 大语言模型 | React / Motion / SVG / 帧驱动档案运动，原理示意 |
| `closing` | 106–120秒 | 每一次突破，都有来路。 | React / SVG / 帧驱动档案运动 |

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

本示例代码及文案按仓库许可分发；影像素材分别遵循来源许可。成片作为含CC BY-SA素材的改编视听作品按CC BY-SA 4.0分发，署名见片尾及SOURCES；不暗示任何机构背书。
