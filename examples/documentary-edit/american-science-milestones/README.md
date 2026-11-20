# 从电报到大模型

30 秒档案短片，1920×1080、60 fps，面向中文横屏观看。1844 年馆藏电报纸带开启十项科技节点，末段用中文生成示意回应电报。全片保持档案主体、短中文结论和事实边界。

## 时间线

| 场景ID | 时间 | 内容 | 画面推进 |
|---|---:|---|---|
| `opening` | 0–1.5 秒 | 从电报到大模型 | 纸带原件、片名与电键拟音 |
| `telegraph` | 1.5–3.5 秒 | 摩尔斯电报 | 延续同一纸带，在手写 W 下方揭示对应的国际摩尔斯码 |
| `telephone` | 3.5–5.5 秒 | 贝尔电话 | 装置、膜片与波形 |
| `flight` | 5.5–8 秒 | 莱特兄弟首飞 | 飞机与奔跑的人同框 |
| `trinity` | 8–10.5 秒 | 三位一体核试验 | 真实档案与静音停顿 |
| `eniac` | 10.5–12.5 秒 | ENIAC 计算机 | 机柜与操作人员 |
| `transistor` | 12.5–15 秒 | 晶体管 | 贝尔实验室档案中的点接触器件和三角尖端 |
| `moon` | 15–18.5 秒 | 阿波罗 11 号登月 | NASA 16 毫米档案中，旗帜旁两名宇航员的连续动作 |
| `arpanet` | 18.5–21 秒 | 阿帕网（ARPANET） | 四个节点依次连成 1969 年末拓扑 |
| `genome` | 21–23.5 秒 | 人类基因组计划 | 测序照片与碱基序列示意 |
| `llm` | 23.5–28 秒 | 大语言模型 | 两条纸带依次呈现电报提问和生成答句 |
| `closing` | 28–30 秒 | 必要署名 | 晶体管照片出处与图像处理 |

声音由按分镜事件触发的少量拟音组成。核试验段静音。完整来源、作者、许可及改动记录保留在作品材料。

## 重建与验收

实拍与代码的取舍、实际参考和选案记录见[研究](RESEARCH.md)。制作验证和证据覆盖见[验证记录](VERIFICATION.md)。

示例媒体不入库；首次重建先运行恢复入口，下载与转换结果按登记摘要、尺寸和时长校验，已正确的文件直接复用。失败会明确报错且不改写已有素材。

首次恢复登月片段使用 `imageio-ffmpeg` 提供的 FFmpeg 7.1 Windows 构建，以复现已登记的媒体摘要。已有且校验通过的片段直接复用。

```powershell
uv run --directory examples/documentary-edit/american-science-milestones --frozen python assets/fetch.py
uv run m2v prepare --project examples/documentary-edit/american-science-milestones
uv run m2v assets audit --project examples/documentary-edit/american-science-milestones
uv run m2v render --project examples/documentary-edit/american-science-milestones
uv run m2v qa --project examples/documentary-edit/american-science-milestones
uv run m2v status --project examples/documentary-edit/american-science-milestones --history
```

前两秒审美考虑属于定性创作复核：看开场帧序列与手机尺寸下的主题识别和视觉/信息钩子，不虚构实际平台跳出率。成片位于 `examples/documentary-edit/american-science-milestones/outputs/video.mp4`，生成媒体与复核图像不入库。

[视觉设计](DESIGN.md) · [史实与素材来源](SOURCES.md) · [交付验证](VERIFICATION.md)

附属[键盘与火花音效演练](assets/SOUND_EXERCISE.md)可在作品副本验证统一音效库。

本示例的原创代码、文档和文稿采用 [MIT 许可证](LICENSE)。依赖、字体和外部档案的许可见[第三方声明](THIRD_PARTY_NOTICES.md)，实际采用范围见[素材台账](SOURCES.md)。

本示例的画面组件与参数保存在本作品 `scenes/`，可独立重建。

## 本地运行

本示例是独立工程，可以直接在作品目录运行，也可以由 `m2v` 委托同一入口：

```powershell
pnpm install --frozen-lockfile --ignore-workspace
uv sync --frozen
pnpm run setup --download --install-browser
pnpm run validate
pnpm run build
pnpm run render
```

字体缺失时把文件放入 `M2V_FONT_CACHE` 或 `fonts/.cache/`，再执行 `uv run python fonts/fetch.py`；摘要不符会拒绝覆盖。媒体与音效按 `assets/` 配方恢复。环境与恢复细节见[独立基础模板说明](../../../templates/standalone/README.md)。
