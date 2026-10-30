# 自驾路线视频专题

本文定义 `driving-route` 类型的离线制作规范。类型行为以 [OpenSpec 规格](../../../../openspec/specs/driving-route-video/spec.md) 为准；镜头与验收要求不因本指南的说明顺序而降低。

## 材料与绑定

作品只有两份材料，不使用 general 分镜：

- `request.json`（schema v2）：起终点各含 `city`、`address`、`label`，`strategy` 固定 `highway-first`，`durationSeconds` 为大于 6 的整数（初始化默认 30，首例可显式 60），`canvas` 固定 1080×1920 竖屏，`sourceUsage` 记录使用依据与 `mapTiles` 授权确认。
- `route.json`（schema v3）：当前请求的规范化 SHA-256 摘要、`coordinateSystem: GCJ-02`、两个端点的定位结果、实际路线首尾坐标、按服务顺序的 `steps`（道路名、分段坐标）、API 总距离、`cost`（预计耗时、过路费、收费里程、红绿灯；当前不渲染）、按顺序去重的 `cities`（名称、行政区代码、沿线代表坐标）、`administrativePlaces`（市/县行政区中心点；市辖区不单独列出）、不含凭据的采集记录，以及与请求一致的来源使用依据副本；`mapTiles=true` 时必需 `basemap` 记录。

v1 请求与 v2 路线明确拒绝，需更新请求并重新 `fetch`；不提供静默兼容。请求摘要覆盖全部请求内容（含画面名称、时长、来源使用记录与道路底图确认），不含 Key。任何请求变化都会让旧路线失效；修改起终点、城市、策略、画面名称或时长后必须重新执行 `fetch`。`fetch` 还会按沿线城市请求高德行政区中心点：市辖区不单独保存，只保存市与县/县级市/旗；行政区请求失败则整次取数失败。`prepare` 的输入摘要覆盖两份材料、概览影像与全部跟随瓦片，渲染实现与构建资源进入候选绑定。

结构示意（不是授权证明，`sourceUsage` 必须按实际核验结果填写）：

```json
{
  "schemaVersion": 2,
  "origin": {"city": "上海市", "address": "上海市黄浦区具体地点", "label": "上海"},
  "destination": {"city": "郑州市", "address": "河南省郑州市二七区具体地点", "label": "郑州"},
  "strategy": "highway-first",
  "durationSeconds": 60,
  "canvas": {"width": 1080, "height": 1920},
  "sourceUsage": {
    "verifiedOn": "2026-10-30",
    "documents": [{"title": "授权或许可文档标题", "url": "https://example.invalid/license"}],
    "account": "适用账号与用途范围",
    "purpose": "离线保存路线与道路底图并制作竖屏动画视频",
    "offlineStorage": true,
    "derivativeFrames": true,
    "videoPublication": true,
    "mapTiles": true,
    "attribution": "来源要求的署名文本"
  }
}
```

`route.json` 的每个道路段必须按顺序连接，相邻段端点超过 25 米即拒绝，不画跨缺口直线；路线首尾与定位点超过 1 公里即拒绝。连接多个定位结果、城市级粗匹配或路线端点吸附过远都属于失败，不得自行选择第一个结果。

## 使用依据与取数

高德公开接口文档只支持技术选型，不构成离线保存或视频发布的授权证明。真实取数前必须核验当前账号与用途是否覆盖：

- 路线数据的离线留存；
- 二维衍生画面制作；
- 视频公开发布；
- 使用道路底图时，瓦片的离线留存与衍生使用。

核验结果写入 `request.json.sourceUsage`：核验日期、政策或授权文档引用、适用账号与用途范围、三项覆盖确认、`mapTiles` 确认与署名要求。授权原件保存在仓库外，材料只留非敏感引用与摘要。三项确认未全部为 `true` 时，`fetch` 在发起任何网络请求前失败；`mapTiles` 不为 `true` 时，`basemap` 在取图前失败。不得用截图、换提供方或虚构坐标绕过。

Key 只从环境变量 `M2V_AMAP_KEY` 读取，不写入材料、响应、日志、异常或 Git。取数先定位端点，再以 `strategy=34`（高速优先）规划路线并请求 `cost,cities,polyline`；结果先按离线规则完整校验，再原子替换 `route.json`。失败时旧路线保持不变，不发布半份材料。

底图只使用已授权的高德瓦片，坐标与路线同为 GCJ-02 Web Mercator：普通道路为 style=8（含路网与城市注记），卫星为 style=6（`satellite-tiles`）。`--style satellite` 只替换底图，路线、市/县标签、16× 跟随与时长不变。`basemap` 生成：

- 概览：z8 单张拼接影像，覆盖收束时的标题下方全程内容区；
- 跟随：z12 瓦片走廊，覆盖开场 9× 视野、过渡、16× 跟随位置与前瞻偏移。
- 相机跟随目标使用 0.6 秒对称移动平均（按平均速度折合空间窗口），压低折线拐点造成的逐帧抖动；车辆仍取未平滑的贴路位置。

跟随走廊沿真实相机目标每 1 km 采样视口并集，再按当前时长/帧率逐帧复核；首例约 1648 块，`MAX_CORRIDOR_TILES=2200`。超限直接失败并报告实际块数，不静默降低 zoom。每块 256×256、JPEG q90，记录路径、SHA-256 与投影矩形；目录按计划+瓦片摘要内容寻址（`follow-tiles-*`），计划摘要与清单摘要写入材料。任何瓦片失败都中止并保留旧底图；相同计划与摘要重复执行时复用。`mapTiles=true` 时缺少 `basemap` 会使 validate/prepare/render 失败；`mapTiles=false` 才允许矢量例外。渲染时按当前相机视口只绘制可见瓦片，数据 URI 预加载完成后才截图；结尾 1 秒淡出到概览。

## 命令

```powershell
uv run m2v init --type driving-route --project <slug>
# 填写 request.json（含 sourceUsage 与 mapTiles），设置 M2V_AMAP_KEY 后取数
uv run m2v driving-route fetch --project videos/driving-route/<slug>
# 需要普通道路底图时，确认 mapTiles=true 后取图
uv run m2v driving-route basemap --project videos/driving-route/<slug>
# 卫星底图版本（其他画面契约不变）
uv run m2v driving-route basemap --project videos/driving-route/<slug> --style satellite
uv run m2v validate --project videos/driving-route/<slug>
uv run m2v prepare --project videos/driving-route/<slug>
# 可选局部预演，不能覆盖正式成片
uv run m2v preview --project videos/driving-route/<slug> --start-seconds 0 --end-seconds 6
uv run m2v render --project videos/driving-route/<slug>
```

`validate / prepare / preview / render` 只读取已保存材料，断网且未配置 Key 时仍可执行，不发生外部网络访问。`render` 输出 `outputs/driving-route.mp4`，预演写在 `outputs/previews/`；重复导出在相同有效输入下复用候选。

## 画面与运动契约

- 固定 1080×1920 竖屏、30 fps、无音轨。默认 30 秒；首例显式 60 秒（1800 帧）。首尾各 2 秒，剩余时间为行驶段；显式时长只改变中段行驶时间。
- 地图铺满竖屏，使用浅色普通道路底图，显示路网与城市；顶部两行居中标题（“模拟行程”与“X → Y”），已行驶公里数显示在车辆旁的屏幕空间 pill 中；不显示底部数据面板。地图保持北向，路线与底图共用 GCJ-02 投影。
- 路线使用深蓝已行驶、灰蓝未行驶与浅色小车；文字使用深色加白色描边。开场 2 秒停在起点近景并从 9× 快速推到 16×（ease-out，前段更快），不展示全程；随后 0.5 秒过渡，中段 16× 跟随；结尾 2 秒先用 1 秒拉远到标题带以下的全程，再保持 1 秒，完整显示路线及两端。
- 小车按累计距离沿折线推进，位置始终在真实轨迹上；朝向沿行驶方向取前后窗口的弦向量，端点处只用朝内窗口，急弯与角度跨界不突然翻转。已走路线端点与小车共用同一插值结果。
- 市名与县/县级市名来自 `administrativePlaces[].center`，统一 30 px、字重 700、8 px 白色描边固定在屏幕空间绘制；市辖区（名称以“区”结尾）不单独标注，由市名覆盖。标签固定在中心点上方、坐标取整到整数像素，靠近边缘时向内收；避让车辆、端点、标题带、车辆旁里程、高速名与彼此重叠；跟随时只画当前视域内中心点。
- 车辆旁 pill 显示“已行驶 X 公里”，随车移动但不随车旋转；靠近标题、边缘或端点时换到另一侧，不显示“全程”。不显示实时路况、实时车速或导航指令。
- 署名按来源要求显示，字号小于主体信息，置于右下角次要位置且不遮挡路线、城市名或车辆。

## 验证与完成边界

`render` 自动验收帧数、画幅、帧率、时长、无音轨与输入绑定，并保留溯源和候选记录。`preview` 只作局部检查，不替代全片复核。

首个作品上海人民广场到郑州二七广场另需独立子代理对当前候选执行视觉评审：路线与贴路转向、镜头衔接、16 倍清晰度与稳定性、路网与城市可读性、两行标题、开场近景与结尾全程，关闭全部必改项后才算首例制作完成。技术自动验收通过、缺少当前候选独立视觉评审时，只能报告技术交付。

作品材料、真实响应、底图影像与生成媒体留在忽略的内容目录或外部内容根，不加入 Git；共享代码、测试与本指南纳入版本控制。
