# 太阳系之旅：从太阳到奥尔特云

写实 3D 科普示例，1920×1080、60 fps，中文旁白与烧录字幕，目标实际片长 165～180 秒。替换原选择示例，另外两个示例保留。

以逐站向外旅行为线索，介绍太阳、八大行星、代表卫星、矮行星、小天体带和不同定义下的边界。可编辑源文见 [article.md](article.md)，编排见 [storyboard.json](storyboard.json)，视觉依据见 [DESIGN.md](DESIGN.md)，科学资料与许可见 [SOURCES.md](SOURCES.md)，验证范围与剩余限制见 [VERIFICATION.md](VERIFICATION.md)。

全片是同一个完整太阳系三维模型（Three.js / React Three Fiber / Drei），相机在总览、行星与卫星近景之间来回飞行，不替换场景中的天体。画面由真实三维网格、球面纹理、太阳位置点光源与环境补光、独立云层、大气辉光、透明土星环与粒子结构构成。太阳、地球和土星是三处代表画面。岩质凹凸和外太阳系结构为艺术示意，不用于精确历算或科学测量；大小、距离、自转速度非同比例，奥尔特云尚未直接观测证实。

## 旁白与画面对应

| 场景 ID | 旁白段 ID | 科普内容 | 实现与推进 |
|---|---|---|---|
| solar-journey | sun-0 | 太阳 | 同一模型，相机飞近与返回 |
| solar-journey | inner-0 | 水星 | 同一模型，相机飞近与返回 |
| solar-journey | inner-1 | 金星 | 同一模型，相机飞近与返回 |
| solar-journey | home-0 | 地球 | 同一模型，相机飞近与返回 |
| solar-journey | home-1 | 月球 | 同一模型，相机飞近与返回 |
| solar-journey | rock-0 | 火星 | 同一模型，相机飞近与返回 |
| solar-journey | rock-1 | 谷神星 | 同一模型，相机飞近与返回 |
| solar-journey | giant-0 | 木星 | 同一模型，相机飞近与返回 |
| solar-journey | giant-1 | 木卫二 | 同一模型，相机飞近与返回 |
| solar-journey | rings-0 | 土星 | 同一模型，相机飞近与返回 |
| solar-journey | rings-1 | 土卫六 | 同一模型，相机飞近与返回 |
| solar-journey | ice-0 | 天王星 | 同一模型，相机飞近与返回 |
| solar-journey | ice-1 | 海王星 | 同一模型，相机飞近与返回 |
| solar-journey | kuiper-0 | 冥王星 | 同一模型，相机飞近与返回 |
| solar-journey | edge-0 | 日球层顶 | 同一模型，相机飞近与返回 |
| solar-journey | edge-1 | 奥尔特云 | 同一模型，相机飞近与返回 |

主体和文字避让共享字幕安全区；导航仅表示介绍顺序。太阳、行星、卫星与轨道始终存在，镜头按实际旁白窗口推进并返回总览。素材先本地导入留证，录制期间不请求外网。

## 重现制作

```powershell
uv run m2v validate --project examples/solar-system-journey
uv run m2v general input-review --storyboard examples/solar-system-journey/storyboard.json
# 阅读完整源文并填写 outputs/input-review.json，然后继续。
uv run m2v prepare --project examples/solar-system-journey
uv run m2v preview --project examples/solar-system-journey
uv run m2v render --project examples/solar-system-journey
```

项目已保存服务返回音色中的云扬和选择理由。准备与源文审查记录位于本例 outputs/，完整预演和成片位于 videos/examples/solar-system-journey/outputs/；三张交付关键画面放在该作品的 stills/。代码、源文、设计稿、固定纹理和来源记录纳入 Git，生成媒体不入库。
