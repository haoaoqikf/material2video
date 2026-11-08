# 七例原地独立化记录

本记录对应任务 4.1–4.7。七部示例均保留原主题、scene.id、分镜内容与视听目标；生成文件归作品所有，主项目仅作为组件与实现参考。

## 共同改造

- 每例新增 `package.json`、`pnpm-lock.yaml`、`pyproject.toml`、`uv.lock`、TypeScript／Vite／Remotion 配置、`scripts/`、本地 `film_runtime`、`fonts/`、`src/` 与 `project.json` v3。
- 场景从主项目 SDK 改为作品内相对导入；只复制实际采用的模块与第三方依赖。构建器拒绝 `m2v/*` 和作品外路径。
- 字体按实际采用登记：基础 Inter／Noto Sans SC；fold 增加 Noto Serif SC 子集；compound-connect 增加 KaTeX 0.19.1 WOFF2。字体二进制不入库。
- 音效配方改为 `film_runtime.sound-synthesis` 命名空间；`fetch.py` 与媒体恢复只导入作品本地模块。
- 每例 README 增加本地安装、恢复、构建、预览与导出步骤。

## 逐例采用范围

| 示例 | 采用的本地组件／依赖 | 说明 |
|---|---|---|
| text-motion/fold | 受控上下文、Painter、字体与事件声 | 保留九幕相机时间轴、宋体与事件声 |
| data-evolution/compound-interest | 上下文、motion 组件、路径、动画工具、roughjs、事件声与音床 | 保留精确数学与 29 秒视听契约 |
| data-evolution/compound-connect | 上下文、公式、图表几何、路径、事件效果、D3 形状、KaTeX | 保留公式与事件声 |
| principle-metaphor/pigeon | 上下文、Painter、事件 | 保留主体、分层舞台与事件声 |
| principle-metaphor/luck-on-stage | 上下文、Painter、路径、动态场、事件效果 | 保留路径、圆形尝试与事件声 |
| spatial-3d/solar-system-journey | 上下文、R3F、drei、后期、Three、镜头套件、媒体 | 保留 15 段旁白、音乐与事件声 |
| documentary-edit/american-science-milestones | 上下文、ECharts 图表、媒体、动画工具 | 保留 12 幕真实媒体、事实与图表 |

## 完整导出与技术检查

| 示例 | 时长／规格 | 成片 SHA-256 | 准备指纹 | 本地 QA |
|---|---|---|---|---|
| text-motion/fold | 33 秒，1920×1080，30 fps | `5ea4c266a52dcaf05ae8ddabf15fc18b33ccacbf99dc246f33ba12468d98d532` | `54569c1427e06865928d4858be3b50940e111293012a29ef9afbb903d644882b` | pass |
| data-evolution/compound-interest | 29 秒，1920×1080，30 fps | `1615ec13045b3e3b570d9ee78ecbd7126d1884d0a9118768cab21082d3c2d281` | `028ba2a65662151c9fe3058c1fbc2ea6beb8daa4619b1c6f22fd7b3ea3ce1ca6` | pass |
| data-evolution/compound-connect | 40 秒，1920×1080，30 fps | `9386f533f9d15fce3f61ac076d83597c26ecfc96b146bd4ed2cdca08cb3a927a` | `08f8e86d29711ec88129e31e206b8fc3f5e3fe141073068fdc4ec48426b8fd22` | pass |
| principle-metaphor/pigeon | 33 秒，1920×1080，30 fps | `53f2656d3273d36ed99316f14a5e3a8dbe05b9363bea1165003b7dccca7d5ea1` | `ba331fdba0197d96f570771ea490b85cb3aaf36f8161ef2e28225f4cafb5105d` | pass |
| principle-metaphor/luck-on-stage | 41 秒，1920×1080，30 fps | `ec70f8ca9195b9425e96343fd3a921a48efeec237b7534f6b9e4360f2427660f` | `bfbb5f39f6b2f1de6cfbad93986fcec871db3f37e81cdd750a5cbf2492355e9b` | pass |
| documentary-edit/american-science-milestones | 30 秒，1920×1080，60 fps | `1a14366e97eb904e4eca6deb126c30f1e06e113825283ea37b5de611e8df5e90` | `f091a40d138bde6732b34d10e40e70954ffaeef6ce46b2a7c5aab3c2ab8e072d` | pass |
| spatial-3d/solar-system-journey | 174.55 秒，1920×1080，60 fps | `045f3151ff6340faec15b532e350d1f4e367d49934773d16ef46b27c6e400ece` | `7b177c640807d159ba5f21d846d3b7ba363ad69bf5636a5ae712020e34c6e530` | pass |

代表帧以 `ffmpeg` 从当前成片直接抽取到忽略目录 `.cache/review-frames/`，逐张查看：fold 的珠串与宋体字幕、compound-interest 的双列收益对照与结论、compound-connect 的差值图表与粒子封面、pigeon 的实验室舞台、luck-on-stage 的概率盘与期望网格、documentary 的摩尔斯电报／晶体管／大语言模型真实媒体与图表均正常；未发现空白、错位、字体回退或素材缺失。该查看是技术性代表帧复核，不替代独立美术评审。

- 所有导出均完整解码并通过本地 QA；`compound-connect` 在使用 `--jobs 4` 时遇到一次采集进程长时间无输出，改为 `--jobs 1` 后完整通过；未据此宣称多进程在所有负载下稳定。
- `spatial-3d/solar-system-journey` 完整导出 10473 帧／174.55 秒，15 段旁白全部命中本地缓存；首次并行渲染在音频封装阶段超时一次，单独重跑后完整通过。代表帧复核了水星段、木星／土星段与奥尔特云收尾，行星材质、镜头、字幕和声道正常。
