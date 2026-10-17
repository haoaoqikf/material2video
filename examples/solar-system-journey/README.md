# 太阳系之旅：从太阳到奥尔特云

写实 3D 科普示例，1920×1080、60 fps，中文旁白与烧录字幕，目标实际片长 55～65 秒。它是仓库里唯一的 **cinematic 档**样板：9 章、3 个 hero 镜头、单程向外的镜头语言、4K 级资产、确定性后期与母版音轨。另外两个示例保持 standard。

以逐站向外旅行为线索，介绍太阳、内行星、地月、小行星带、木星、土星、冰巨星、柯伊伯带与太阳系边缘。全片只有一幕 `solar-journey`，九段旁白驱动十一个镜头。可编辑源文见 [article.md](article.md)，编排见 [storyboard.json](storyboard.json)，视觉依据见 [DESIGN.md](DESIGN.md)，科学资料与许可见 [SOURCES.md](SOURCES.md)，验证范围与剩余限制见 [VERIFICATION.md](VERIFICATION.md)。

全片是同一个完整太阳系三维模型（Three.js / React Three Fiber / Drei），相机沿一条向外推进的连续路径穿过各章，只在三次章节转折回望；镜头之间不硬切，边界在 0.5 秒内平滑混合朝向、FOV、滚转与曝光。画面由真实三维网格、球面纹理、太阳位置点光源与环境补光、独立云层、大气辉光、透明土星环与粒子结构构成，叠加电影级后期（Bloom、DOF、grain、vignette、色散与内置调色档）。地球、土星与奥尔特云是三处 hero 连续镜头。岩质凹凸和外太阳系结构为艺术示意，不用于精确历算或科学测量；大小、距离、自转速度非同比例，奥尔特云尚未直接观测证实。

## 旁白与画面对应

| 镜头 ID | 旁白段 ID | 章节 | 实现与推进 |
|---|---|---|---|
| cold-open | — | 冷开场 | 日面边缘极特写，日珥升起；无旁白留白 |
| sun-pullback | sun-0 | 太阳 | 从日面拉到总览，日冕与轨道渐显 |
| inner-planets | inner-0 | 内行星 | 水星陨坑掠过，落在金星云顶 |
| earth-hero | home-0 | 地月（hero） | 夜面灯光 → 晨昏线日出 → 海面高光 → 云影，月球前景虚化 |
| rock-belt | rock-0 | 小行星带 | 火星红色尘土，穿越稀疏小行星带 |
| jupiter-giant | giant-0 | 木星 | 大红斑正对，云带流动，木卫二冰纹 |
| saturn-hero | rings-0 | 土星（hero） | 环从侧刃到展开、逆光冰晶、卡西尼缝、土卫六雾霾 |
| ice-giants | ice-0 | 冰巨星 | 天王星侧躺、海王星风暴 |
| kuiper-pluto | kuiper-0 | 柯伊伯带 | 冥王星心形区域，柯伊伯带粒子 |
| oort-hero | edge-0 | 边缘（hero） | 日球层顶气泡边界、彗星、拉远到太阳成点 |
| oort-hold | — | 收尾 | 静置留白，太阳成为一个亮点 |

主体和文字避让共享字幕安全区；顶部是章节进度轨，不是常驻左栏。太阳、行星、卫星与轨道始终存在，镜头按 `shots` 的时间窗推进。素材先本地导入留证，录制期间不请求外网。

## 重现制作

```powershell
uv run m2v validate --project examples/solar-system-journey
python examples/solar-system-journey/assets/sound/generate.py  # 声音素材不入库，先本地生成
uv run m2v general input-review --storyboard examples/solar-system-journey/storyboard.json
# 阅读完整源文并填写 outputs/input-review.json，然后继续。
uv run m2v prepare --project examples/solar-system-journey
uv run m2v lookdev --project examples/solar-system-journey
# 实际观看静帧与样片，把时间码、问题与复查写进 outputs/visual-notes.md；不阻断后续步骤
uv run m2v preview --project examples/solar-system-journey
uv run m2v qa --project examples/solar-system-journey
uv run m2v render --project examples/solar-system-journey
```

项目已保存服务返回音色中的云扬和选择理由；同一段旁白的候选 A/B 样片放在 `outputs/voice-ab/`。音乐床与三个音效是同目录 `assets/sound/generate.py` **原创合成**的（无第三方采样，CC0 1.0，许可见 `assets/sound/LICENSE.md`），输出逐字节可复现；**素材本身不入库**，全新克隆后按上面的命令先生成再准备。准备与源文审查记录位于本例 outputs/，完整预演和成片位于 videos/examples/solar-system-journey/outputs/。代码、源文、设计稿、固定纹理、声音生成器与来源记录纳入 Git，生成媒体不入库。

录制采用共享受控时钟按 60 fps 顺序逐帧采集；`look.motion` 支持 hero 子帧运动模糊与 2 倍 SSAA，但本片为控制约 25 分钟的整片耗时采用 1 子帧、1× 采集，原生 2× 像素细节由 `m2v lookdev` 的 4K 静帧承担。机器负载只影响制作耗时。修改源码后需重新 prepare 与完整 preview，旧片段缓存不复用。

