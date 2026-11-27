# 《太阳系之旅》：让镜头显露土星环，而不是让环长出来

[仓库首页用的土星帧](../site/assets/hero.jpg)不是独立绘制的宣传图。[展示资源脚本第 35、123 行](../../scripts/build-site-assets.py#L123)从示例成片的第 61 秒取这一帧。向前追，它落在 `saturn-hero` 的观察窗口内。这个镜头的任务是让观众先看见薄边，再辨认出完整的环面；环的几何不变，变化来自镜头在同一个三维世界里移动。本文只追这一站，从素材到成片逐段定位，不把设计目标当作新的实测结论。

## 一、分镜决定什么时候看见什么

[场景设计第 24 行](../../examples/spatial-3d/solar-system-journey/design/scenes/solar-journey.md#L24)写的是暗侧起步、先显环、再稳定逆光观察。落实到[分镜第 4–18 行](../../examples/spatial-3d/solar-system-journey/storyboard.json#L4)，画幅为 1920×1080、每秒 60 帧，`solar-journey` 是由 `scenes/journey.tsx` 绘制的一整个代码场景。土星不是一个新的 Remotion 合成片段，它只是场景 `props.shots` 中的一条镜头。

[分镜第 4498–4505 行](../../examples/spatial-3d/solar-system-journey/storyboard.json#L4498)给出 `saturn-hero` 的目标 `saturn`、关联旁白 `saturn-line`、以及半开区间 `[3355, 4038)`。按分镜帧率换算，窗口始于约 55.92 秒，终于 67.30 秒，共 683 帧。[第 4827–4836 行](../../examples/spatial-3d/solar-system-journey/storyboard.json#L4827)登记镜头视野角 `44`、注视目标 `saturn` 和 `dof: 0`；[第 8734–8736 行](../../examples/spatial-3d/solar-system-journey/storyboard.json#L8734)另记旁白及其 `holdFrames: 404`。镜头的进出站区间不等于旁白窗口。看全片时，前后过场连着同一个世界，而不是一开口就跳切到另一张土星图。

若想重做这一站，不必从几百行路点倒推意图。[行程表第 79–85 行](../../examples/spatial-3d/solar-system-journey/scenes/journey-plan.json#L79)把讲述参考时点记为 56 秒，并分开记录进入、讲述后和过场预算；[路径生成器第 343–347 行](../../examples/spatial-3d/solar-system-journey/scripts/lib/paths.mjs#L343)再以土星位置为锚，将径向、高度和切向偏移变成路点。[第 460–464 行](../../examples/spatial-3d/solar-system-journey/scripts/lib/paths.mjs#L460)把绕行预算拆成显环和观察，显环最多取两秒且不超过绕行预算的一半；这两个速度阶段仍属同一镜头。改方案时先动行程和生成规则，用[示例说明第 33 行](../../examples/spatial-3d/solar-system-journey/README.md#L33)的入口重建，然后再以更新后的分镜帧区间复核，而不是只改镜头说明文字。

## 二、源码把素材和机位变成同一幅画面

先分清球体和环的两条来源。[素材配方第 77–82、91–94 行](../../examples/spatial-3d/solar-system-journey/assets/recipe.json#L77)中，球体贴图由登记的 NASA GLB 提取，环用登记的径向颜色与透明度纹理。分别记录摘要，不能用外观相似的文件互换。[恢复脚本第 32–33 行](../../examples/spatial-3d/solar-system-journey/assets/fetch.py#L32)取归档材料生成 `saturn` 图；[场景布局第 20–21 行](../../examples/spatial-3d/solar-system-journey/scenes/layout.tsx#L20)设定土星半径为 `1.85`、土卫六从属于土星。这些是场景坐标中的编排参数，不是天文测量值。

[世界源码第 225–243 行](../../examples/spatial-3d/solar-system-journey/scenes/world.tsx#L225)用 `1.24` 和 `2.27` 倍的行星半径建环，生成 192 段圆周几何，再按每个顶点离中心的距离重写纹理坐标。这样颜色与透明度纹路沿半径分布，不会把矩形贴图当花纹沿圆周重复。[第 380–383 行](../../examples/spatial-3d/solar-system-journey/scenes/world.tsx#L380)把环、薄大气和外围尘粒挂在同一颗星球上。看近环面时它自然压成一条细边；离开环面后，原来就存在的内外边界才分开，不需要给环加缩放动画。

机位由源码按帧求值。[入口第 9–30、38–49 行](../../examples/spatial-3d/solar-system-journey/scenes/journey.tsx#L19)按帧选择镜头，传给三维世界；[相机路径第 16–19、30–49 行](../../examples/spatial-3d/solar-system-journey/scenes/flight.ts#L16)由分镜路点建 Catmull–Rom 曲线，再对相邻帧位置作对称滤波。跨站时插值的是朝向四元数，而不是把注视点从一颗星拉到另一颗星的直线中间，见[第 55–72 行](../../examples/spatial-3d/solar-system-journey/scenes/flight.ts#L55)。[三维场景第 45–64 行](../../examples/spatial-3d/solar-system-journey/scenes/solar-system.tsx#L45)把本帧位置、朝向和视野角写入相机。整个土星窗口实际使用 44 度视野；不要把单改分镜某站的 `fov` 当作缩放捷径，当前 `createFlight` 的取值逻辑只处理片头视野向 44 度收拢。

## 三、采集与合成分别核对

准备好[示例的依赖、字体与素材](../../examples/spatial-3d/solar-system-journey/README.md)后，从作品目录可用 `pnpm run preview --start-seconds 55.916666667 --limit-frames 683` 请求该窗口；完整导出用 `pnpm run render`。入口由[作品的 `package.json` 第 10–11 行](../../examples/spatial-3d/solar-system-journey/package.json#L10)交给本地运行时。采集并不是录制屏幕播放：[采集器第 38–65 行](../../examples/spatial-3d/solar-system-journey/runtime/python/film_runtime/types/scene_film/code_scenes/capture.py#L38)换算所需的场景帧区间并登记生成的片段；[第 463–504 行](../../examples/spatial-3d/solar-system-journey/runtime/python/film_runtime/types/scene_film/code_scenes/capture.py#L463)驱动浏览器到目标帧并截取 PNG；[第 578–596 行](../../examples/spatial-3d/solar-system-journey/runtime/python/film_runtime/types/scene_film/code_scenes/capture.py#L578)检查编号连续性后用 FFmpeg 编码。预览所需区间与缓存补采区间不必完全相同。

随后，[导出器第 186–229 行](../../examples/spatial-3d/solar-system-journey/runtime/python/film_runtime/types/scene_film/explainer_render.py#L186)将已采集片段交给 Remotion 的 `SceneFilm`，合成画面后再按项目声音配置混音封装。[组件第 37–75 行](../../examples/spatial-3d/solar-system-journey/src/scene-film/SceneFilm.tsx#L37)将片段按时间线铺入合成，并在片段上方放字幕。若想复核这个镜头，用窗口开头、中段及结束前的帧看环面如何揭示，用合成后的同一时间点核对字幕是否挡住主体，再看接向天王星的边界。宣传图只证明一个时点的构图，不能替代这三项检查。

这也给出了排查顺序。可在[导出器第 189 行](../../examples/spatial-3d/solar-system-journey/runtime/python/film_runtime/types/scene_film/explainer_render.py#L189)区分预览与全片的输出目标，免得把局部片段当成 120 秒成片。若采集帧里的环纹已不对，先查贴图摘要与径向 UV；若环面变化方向不对，先查路径路点，而不是增加高光；若帧里主体可辨但合成后被挡，再查字幕时点和安全区。这样才能知道要改的是素材、场景，还是合成。
