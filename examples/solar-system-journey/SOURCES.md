# 科学来源与素材署名

核验日期：2026-10-17。科学说明是中文原创概述；下列网页用于核对事实和口径。

## 科学资料

- [NASA 行星总览](https://science.nasa.gov/solar-system/planets/)：八大行星身份、岩质行星与巨行星分类。
- [NASA 行星参数表](https://nssdc.gsfc.nasa.gov/planetary/factsheet/)：平均日距与天王星倾角。AU 为天文单位，数值按展示精度取近似值；卫星显示的是母星平均日距。
- [NASA 木卫二](https://science.nasa.gov/jupiter/jupiter-moons/europa/)：冰壳及地下海洋证据，不能表述为已发现生命。
- [NASA 土卫六](https://science.nasa.gov/saturn/moons/titan/)：浓厚大气、甲烷与乙烷河湖。
- [NASA 谷神星](https://science.nasa.gov/dwarf-planets/ceres/facts/)：主小行星带中的最大天体与矮行星身份。
- [NASA 冥王星地图](https://science.nasa.gov/resource/pluto-global-color-map/)：新视野号拼接图与心形区域位置。
- [NASA 日球层](https://science.nasa.gov/heliophysics/focus-areas/heliosphere/)：太阳风影响区与星际介质的边界。
- [NASA 奥尔特云](https://science.nasa.gov/solar-system/oort-cloud/facts/)：推测性球状分布及可能延伸到约十万 AU 的外缘；不是已直接观测证实的壳层。

## 固定输入素材

### cinematic 资产升级（2026-10-17）

按实际文件尺寸登记，不采用下载文件名中的“8k”作为分辨率证据。地球日间图为
8192×4096；太阳、木星、土星为 4096×2048；冥王星保留原图 5926×2963。
前四项从 [Solar System Scope 原站](https://www.solarsystemscope.com/textures/) 下载，
保留 INOVE 的 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 署名。
地球夜灯为同源 8192×4096 地图，取代程序化城市点阵；地球法线与高光遮罩取自原作者
TIFF，分别转无损 PNG 与 `roughness = 235 - specular × 0.8` 的 8 bit 粗糙度图，
保留实际 2048×1024 尺寸，不上采样冒充地形精度。云层沿用已登记的灰度图，
云影读取绿色通道，并补偿云层与地表的相对转动。

土卫六颜色图为原生 4096×2048 程序化雾霾；土星环为原生 4096×512 径向纹理，
包含 C/B/A 环和卡西尼缝的艺术轮廓。原图 8192×500 不符合高度门槛，未放大采用。
太阳、土星、木星、冥王星和土卫六的 normal/roughness 是程序化微表面，不是实测高程；
不自发光天体的 emissive 为黑色，太阳自发光使用其日面图，地球使用夜灯图。
生成器和参数在 [assets/materials/generate.py](assets/materials/generate.py)，
原创输出采用 [CC0 1.0](assets/materials/LICENSE.md)。所有 ID、实测尺寸、处理说明、
角色、目标、色彩空间和摘要见 `assets/media-sources.json`，运行时只读取这些已登记输入。

以上升级已落入可编辑材料；look-dev 静帧、样片与 hero 可见性的实际观看记录见 `outputs/visual-notes.md`，look-dev 不设人工确认门禁。

逐项文件摘要、尺寸和来源保存在 [assets/media-sources.json](assets/media-sources.json)。纹理仅用于艺术性球面展示，不用于地形测量。

| 素材 ID | 来源与署名 | 许可及处理 |
|---|---|---|
| sun、mercury、venus、mars、jupiter、saturn、uranus、neptune、moon、clouds、earth、earth-emissive、earth-normal、earth-roughness、sun-emissive | [Solar System Scope / INOVE](https://www.solarsystemscope.com/textures/)，基于 NASA 数据加工 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)；原图或上述明确记录的辅助图转换。颜色和未观测区域可能经艺术调整 |
| titan、rings 与除地球法线/粗糙度外的程序化微表面 | material2video 原创生成器 | [CC0 1.0](assets/materials/LICENSE.md)；艺术示意，不是地形测量 |
| europa | [NASA / JPL-Caltech / USGS，Voyager 拼接图](https://maps.jpl.nasa.gov/tmaps/jupiter.html) | [JPL 图像使用政策](https://www.jpl.nasa.gov/jpl-image-use-policy/)；使用清理过的木卫二拼接地图 |
| pluto | [NASA / JHUAPL / SwRI](https://science.nasa.gov/resource/pluto-global-color-map/) | NASA 媒体使用指南；使用新视野号全局彩色地图，分辨率与观测覆盖不均匀 |

下载原站超时的 Solar System Scope 素材取自保留原始许可声明的公开镜像：[skyplothelper planet_maps](https://github.com/pjcigan/skyplothelper/tree/main/examples/data/planet_maps)（太阳及多数行星）及 [SolarSystem 原始纹理](https://github.com/TanvirAhmedArnab/SolarSystem/tree/main/SourceAssets/ThirdParty/Textures/SolarSystemScope)（金星云层、地球云层、土星环）。镜像不是原创作者；许可仍为原作者的 CC BY 4.0。原作者主页和许可在画面及本文保留。

谷神星的程序化岩质表面、土卫六的雾层、日冕、大气辉光与小天体分布为本示例代码生成的艺术示意。土卫六不透过雾层展示未经观测的地表细节。轨道线、太阳风边界及奥尔特云均非真实比例或实时位置。

## 成片署名

Planet textures: Solar System Scope / INOVE (CC BY 4.0), https://www.solarsystemscope.com/textures/ ; https://creativecommons.org/licenses/by/4.0/ . Additional imagery: NASA/GSFC; NASA/JPL-Caltech/USGS; NASA/JHUAPL/SwRI. 3D lighting and artistic visualization by material2video.

视频为科学传播演示，不表示 NASA、JPL 或素材作者对本项目的认可。
