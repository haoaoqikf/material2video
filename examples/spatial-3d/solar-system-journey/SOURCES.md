# 科学来源与素材署名

## 两分钟重构的复核（2026-11-10）

本轮重新读取[Solar System Scope纹理页](https://www.solarsystemscope.com/textures/)、[JPL图像政策](https://www.jpl.nasa.gov/jpl-image-use-policy/)、[NASA媒体政策](https://www.nasa.gov/nasa-brand-center/images-and-media/)及[CC0说明](https://creativecommons.org/publicdomain/zero/1.0/)，核对科普三维展示用途、署名、第三方标注和无背书条件。逐项用途及日期已登记到`assets/media-sources.json`的usage；本轮主动替换土星环、谷神星表面/法线、土星云带与配对几何，移除土星三张程序化辅助图，其他既有素材作者、许可及摘要不变，不把镜像视为授权主体。无人物或机构标志入片。

土星环经独立对照后主动更换：弃用旧程序化等距线纹，改用原作者Solar System Scope的`2k_saturn_ring_alpha.png`（2048×125，CC BY 4.0）。原站下载超时后由[保留原许可的镜像](https://github.com/TanvirAhmedArnab/SolarSystem/tree/main/SourceAssets/ThirdParty/Textures/SolarSystemScope)恢复，实际文件与Git LFS登记摘要`4b0644b2f3ef259fd0bfaedd9dc52f9e7d9738f65f50363e8c4dd19f650d7334`一致；经正式素材导入入口登记并更新固定配方。这是有来源和许可的主动换件，不是恢复失败时接受摘要漂移。文件不修改，径向映射及透光、阴影为艺术处理。

火星古水流表述核对[NASA Mars Facts](https://science.nasa.gov/mars/facts/)，只概述古河谷/三角洲/湖床证据。奥尔特云继续明确为推测性结构。具体参考及实际查看范围见[研究](RESEARCH.md)；参考文件只用于对照，不进入成片素材。当前120秒版仍在制作，以下旧版时长和复核只说明历史。

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

### cinematic 资产升级（2026-10-17，历史；本轮替换见下文）

按实际文件尺寸登记，不采用下载文件名中的“8k”作为分辨率证据。地球日间图为
8192×4096；太阳、木星、土星为 4096×2048；冥王星保留原图 5926×2963。
前四项从 [Solar System Scope 原站](https://www.solarsystemscope.com/textures/) 下载，
保留 INOVE 的 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 署名。
地球夜灯为同源 8192×4096 地图，取代程序化城市点阵；地球法线与高光遮罩取自原作者
TIFF，分别转无损 PNG 与 `roughness = 235 - specular × 0.8` 的 8 bit 粗糙度图，
保留实际 2048×1024 尺寸，不上采样冒充地形精度。云层沿用已登记的灰度图，
云影读取绿色通道，并补偿云层与地表的相对转动。

土卫六颜色图为原生 4096×2048 程序化雾霾；旧版土星环曾使用4096×512程序化径向纹理，本轮已替换为上文登记的原作者2048×125径向图，
旧生成图包含 C/B/A 环和卡西尼缝的艺术轮廓；旧轮当时未放大采用8192×500候选。该历史取舍不评价本轮2048×125原件，当前径向贴图按实际用途核验，不冒充二维照片的高度精度。
太阳、木星、冥王星和土卫六的 normal/roughness 是程序化微表面，不是实测高程；旧版土星三张辅助图已移除，当前土星用NASA几何法线与固定粗糙度。
不自发光天体的 emissive 为黑色，太阳自发光使用其日面图，地球使用夜灯图。
生成器和参数在 [assets/materials/generate.py](assets/materials/generate.py)，
上述原创辅助图输出采用 [CC0 1.0](assets/materials/LICENSE.md)，不包含本轮换用的CC BY 4.0土星环。所有 ID、实测尺寸、处理说明、
角色、目标、色彩空间和摘要见 `assets/media-sources.json`，运行时只读取这些已登记输入。

以上升级已落入可编辑材料；look-dev 静帧、时间标注帧序列、量测与自动音频信号的复核记录见作品 `outputs/visual-notes.md`，不要求播放样片或试听音色，也不设人工确认门禁。

逐项文件摘要、尺寸和来源保存在 [assets/media-sources.json](assets/media-sources.json)。媒体不入库，按 [assets/recipe.json](assets/recipe.json) 与 [assets/fetch.py](assets/fetch.py) 恢复；配方只记录固定下载地址与生成步骤，不自动更换来源或接受新摘要。纹理仅用于艺术性球面展示，不用于地形测量。

| 素材 ID | 来源与署名 | 许可及处理 |
|---|---|---|
| sun、mercury、venus、mars、jupiter、uranus、neptune、moon、clouds、earth、earth-emissive、earth-normal、earth-roughness、sun-emissive、rings | [Solar System Scope / INOVE](https://www.solarsystemscope.com/textures/)，基于 NASA 数据加工 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)；原图或上述明确记录的辅助图转换。颜色和未观测区域可能经艺术调整；当前rings为原作者径向图 |
| saturn、ceres、ceres-normal及土星数值几何 | [NASA VTAD三维资源](https://science.nasa.gov/3d-resources/) | NASA媒体准则涵盖模型纹理与多边形数据；固定原包、成员/视图及变换见下文，不标为本项目原创模型 |
| titan 与除地球法线/粗糙度外的程序化微表面 | material2video 原创生成器 | [CC0 1.0](assets/materials/LICENSE.md)；艺术示意，不是地形测量 |
| europa | [NASA / JPL-Caltech / USGS，Voyager 拼接图](https://maps.jpl.nasa.gov/tmaps/jupiter.html) | [JPL 图像使用政策](https://www.jpl.nasa.gov/jpl-image-use-policy/)；使用清理过的木卫二拼接地图 |
| pluto | [NASA / JHUAPL / SwRI](https://science.nasa.gov/resource/pluto-global-color-map/) | NASA 媒体使用指南；使用新视野号全局彩色地图，分辨率与观测覆盖不均匀 |

下载原站超时的 Solar System Scope 素材取自保留原始许可声明的公开镜像：[skyplothelper planet_maps](https://github.com/pjcigan/skyplothelper/tree/main/examples/data/planet_maps)（太阳及多数行星）及 [SolarSystem 原始纹理](https://github.com/TanvirAhmedArnab/SolarSystem/tree/main/SourceAssets/ThirdParty/Textures/SolarSystemScope)（金星云层、地球云层、土星环）。镜像不是原创作者；许可仍为原作者的 CC BY 4.0。原作者主页和许可在画面及本文保留。

旧版谷神星的程序化岩质表面（本轮已移除）、土卫六的雾层、日冕、大气辉光与小天体分布为本示例代码生成的艺术示意。土卫六不透过雾层展示未经观测的地表细节。轨道线、太阳风边界及奥尔特云均非真实比例或实时位置。

## 成片署名

Planet textures: Solar System Scope / INOVE (CC BY 4.0), https://www.solarsystemscope.com/textures/ ; https://creativecommons.org/licenses/by/4.0/ . Additional imagery: NASA/GSFC; NASA/JPL-Caltech/USGS; NASA/JHUAPL/SwRI. Ceres textures and Saturn model/cloud atlas: NASA Visualization Technology Applications and Development (VTAD), https://science.nasa.gov/3d-resources/ . 3D lighting and artistic visualization by material2video.

视频为科学传播演示，不表示 NASA、JPL 或素材作者对本项目的认可。

## 2026-10-18音乐与事实复核（历史）

2026-10-18检索NASA太阳系概览与奥尔特云资料，参考Cassini土星逆光构图；具体用途见DESIGN.md。`assets/sound/score.wav` 为生成器按当时分镜时长（220.5秒）生成的原创旋律配乐，不含第三方采样，按同目录LICENSE.md的CC0许可使用；生成WAV不入库。

## 当前两分钟版声音与恢复

2026-11-10版原创配乐为120秒，地球、土星、外层稀疏窗口由当前分镜派生；没有第三方采样。五项声音的来源与CC0许可、摘要、时长及生成输入见[声音配方](assets/sound/recipe.json)和[生成器](assets/sound/generate.py)。正常恢复使用`--restore`，已有音轨漂移或生成结果不匹配固定摘要时失败，不自动接受新摘要；默认生成用于作者重新登记。完整发布署名沿用上方“成片署名”。

## 谷神星官方模型贴图（终审返工采用）

采用[NASA Ceres 3D Model](https://science.nasa.gov/resource/ceres-3d-model/)，署名 **NASA Visualization Technology Applications and Development (VTAD)**。按[NASA媒体使用准则](https://www.nasa.gov/nasa-brand-center/images-and-media/)用于科普三维模拟，不暗示NASA背书；来源页未标第三方版权。只解包原图，场景光影、压缩尺度与球面仍为艺术展示，不宣称实测地形或实时位置。

| 项目 | 来源与摘要 |
|---|---|
| 固定原包 | [Ceres_1_1000.usdz](https://assets.science.nasa.gov/content/dam/science/psd/solar/2023/09/c/Ceres_1_1000.usdz)，SHA-256 `c103dca27770db8facff946476bcafa2a3cc9244f541ac086e33da86417850c5` |
| ceres | 原成员`0/image1.jpg`，4096×2048，SHA-256 `0eccee05b9c3744c89c53735b9757f4d13c9b696523350778e907d847880d637` |
| ceres-normal | 原成员`0/image0_norm.jpg`，2048×1024，SHA-256 `7727b4e4ce9ba601da48f8e6373ac8156a7272e4522ace741526fc03ad27fe64` |

恢复入口仍为`assets/fetch.py`与固定`assets/recipe.json`，验证整包及两张图片，不接受来源或预期摘要漂移；恢复失败不覆盖已有素材，成功时按固定配方恢复。噪声探索方案未采用，不保留兼容分支；完整署名与许可另保存在素材台账。


## NASA土星云带与配对几何（2026-11-10）

来源：[Saturn 3D Model / NASA VTAD](https://science.nasa.gov/resource/saturn-3d-model/)，NASA媒体准则明确涵盖模型纹理和多边形数据，用于科普展示并署名，不暗示NASA背书。原包为`Saturn_1_120536.glb`，SHA-256 `8dbfde533b13e938408d8aded1d1ce48a084806233f67775371d83013dba7d38`。当前color来自images[0]、bufferView[4]的4096×3072原PNG，SHA-256 `2b4628833c2610ac6677f729376c00440a6bc4df4f85b4928519179e37536f4b`，仅提取、不重编码；此图是专属UV图集，不是4096×2048经纬图。替换旧Solar System Scope土星颜色图，其他原作者贴图许可保留。

几何为mesh[0]，1649顶点、3072三角。位置除以原模型半径500后按当前作品半径缩放，保留扁球极轴比0.9020380249、原法线与三角索引；UV仅翻转V一次，配合TextureLoader原有flipY=true。第三方数值几何位于[scenes/data/saturn.json](scenes/data/saturn.json)，不是原创模型，也不嵌入图片或base64；当前JSON SHA-256 `8b97acb78cd8462df62c2a2170a8e6f7c3bcc4f5037fd0a7310728b6a2c5a5b4`。提取器[assets/materials/saturn.py](assets/materials/saturn.py)校验原包、chunk/view/accessor边界，拒绝不支持的变换、稀疏和压缩输入。维护时可用`--model <原GLB> --geometry scenes/data/saturn.json --image <原PNG输出路径>`复现；常规素材恢复只恢复已登记原PNG，不改写Git中的代码源数据。JSON中的来源、mesh/accessor及提取变换字段仅作溯源，当前不渲染；运行时读取已提取的positions、normals、uv、triangles和polarRatio。

不保留旧土星程序化normal、roughness和黑色emissive，采用原几何法线、固定粗糙度及非自发光材质，避免专属UV与经纬微表面图错误配对。当前登记贴图32项。主环仍是原作者CC BY 4.0图；径向密度、HG形状散射、反照光、按标称半径球体的遮挡近似和固定弱尘层均为艺术展示近似，尤其按标称赤道半径的球体近似通常会高估扁球极区遮挡；它不是严格外接球或扁球解析遮挡，不宣称实测光深度或辐射。

机制参考：[PBRT phase functions](https://pbr-book.org/3ed-2018/Volume_Scattering/Phase_Functions)及[NASA PIA17172原图说明](https://pds-rings.seti.org/press_releases/pages/PIA17xxx/PIA17172.html)。后者明确说明外围弱环在参考图中经过增强；本片弱尘层的半径、密度、颜色和视距LOD是压缩空间下的艺术转化，不拿参考图亮度当真实量测。本片继续采用原Cassini媒体作为整体品质目标，不以新增机制自动视为达标。
