# 从电报到大模型

约30秒无声档案短片，1920×1080、60 fps、统一制作。面向中国普通观众横屏手机播放；以中文名称和短贡献说明为主，ENIAC与ARPANET仅在首次出现时作为辅助识别。保留十项顺序与贡献边界，开场直接以登月档案和中文主题建立观看理由。

## 时间线

| 场景ID | 时间 | 内容 | 画面推进 |
|---|---:|---|---|
| `opening` | 0–2秒 | 美国科学高光时刻 | 登月档案首帧直入主题 |
| `telegraph` | 2–4秒 | 摩尔斯电报 | 电键与信号传播 |
| `telephone` | 4–6秒 | 贝尔电话 | 实物与语音波形 |
| `flight` | 6–9秒 | 动力飞行 | 飞机档案与人物尺度 |
| `trinity` | 9–11秒 | 三位一体核试验 | 克制呈现历史影像及代价 |
| `eniac` | 11–13.5秒 | 埃尼阿克计算机（ENIAC） | 机柜和人物尺度 |
| `transistor` | 13.5–16秒 | 晶体管 | 实物接结构示意 |
| `moon` | 16–19秒 | 阿波罗11号登月 | NASA连续影像 |
| `arpanet` | 19–21.5秒 | 阿帕网（ARPANET） | 四节点连接示意与1970年地图 |
| `genome` | 21.5–23.5秒 | 人类基因组计划 | 历史照片与序列示意 |
| `llm` | 23.5–28秒 | 大语言模型 | 中文 ChatGPT 示意交互逐字生成；全球研究积累为主体、产品为实例 |
| `closing` | 28–30秒 | 唯一署名与版权说明 | 两行大字简短静定署名，无重复标题 |

无旁白、配乐、音效与素材原声；输出按作品契约无音轨或全程数字静音。全片只显示一份极简片尾署名，观众画面不含仓库文件名、路径、内部材料或查阅指引。完整来源、作者、许可及改动记录保留于作品材料。

## 重建与验收

示例媒体不入库；首次重建先运行恢复入口，下载与转换结果按登记摘要、尺寸和时长校验，已正确的文件直接复用。失败会明确报错且不改写已有素材。

```powershell
uv run python examples/american-science-milestones/assets/fetch.py
uv run m2v validate --project examples/american-science-milestones
uv run m2v prepare --project examples/american-science-milestones
uv run m2v assets audit --project examples/american-science-milestones
uv run python examples/american-science-milestones/scripts/render-rough.py
uv run m2v lookdev --project examples/american-science-milestones --stills 4 --sample-seconds 24
uv run m2v render --project examples/american-science-milestones
uv run m2v qa --project examples/american-science-milestones
```

前两秒审美考虑属于定性创作复核：看开场帧序列与手机尺寸下的主题识别和视觉/信息钩子，不虚构实际平台跳出率。成片位于 `videos/examples/american-science-milestones/outputs/video.mp4`，生成媒体与复核图像不入库。

[视觉设计](DESIGN.md) · [史实与素材来源](SOURCES.md) · [交付验证](VERIFICATION.md)

附属[键盘与火花音效演练](assets/SOUND_EXERCISE.md)用于在作品副本验证统一音效库，不改变本示例的无声成片。

本示例代码及文案按仓库许可分发；含CC BY-SA素材的改编视听作品依CC BY-SA 4.0分发，片尾集中署名，不暗示素材作者或机构背书。
