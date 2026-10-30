# 自驾路线视频专题

本文定义 `driving-route` 类型的离线制作规范。类型行为以 OpenSpec 规格为准；镜头与验收要求不因本指南的说明顺序而降低。

## 材料与绑定

作品只有两份材料，不使用 general 分镜：

- `request.json`（schema v1）：起终点各含 `city`、`address`、`label`，`strategy` 固定 `highway-first`，`durationSeconds` 为大于 6 的整数（初始化默认 30），`canvas` 固定 1920×1080，`sourceUsage` 记录使用依据。
- `route.json`（schema v1）：当前请求的规范化 SHA-256 摘要、`coordinateSystem: GCJ-02`、两个端点的定位结果、实际路线首尾坐标、按服务顺序的 `steps`（道路名、分段坐标）、API 总距离、不含凭据的采集记录，以及与请求一致的来源使用依据副本。

请求摘要覆盖全部请求内容（含画面名称、时长和来源使用记录），不含 Key。任何请求变化都会让旧路线失效；修改起终点、城市、策略、画面名称或时长后必须重新执行 `fetch`，不得继续复用旧准备记录。`prepare` 的输入摘要覆盖两份材料，渲染实现与构建资源进入候选绑定。

结构示意（不是授权证明，`sourceUsage` 必须按实际核验结果填写）：

```json
{
  "schemaVersion": 1,
  "origin": {"city": "上海市", "address": "上海市黄浦区具体地点", "label": "上海"},
  "destination": {"city": "郑州市", "address": "河南省郑州市二七区具体地点", "label": "郑州"},
  "strategy": "highway-first",
  "durationSeconds": 30,
  "canvas": {"width": 1920, "height": 1080},
  "sourceUsage": {
    "verifiedOn": "2026-10-30",
    "documents": [{"title": "授权或许可文档标题", "url": "https://example.invalid/license"}],
    "account": "适用账号与用途范围",
    "purpose": "离线保存路线并制作二维动画视频",
    "offlineStorage": true,
    "derivativeFrames": true,
    "videoPublication": true,
    "attribution": "来源要求的署名文本"
  }
}
```

`route.json` 的每个道路段必须按顺序连接，相邻段端点超过 25 米即拒绝，不画跨缺口直线；路线首尾与定位点超过 1 公里即拒绝。连接多个定位结果、城市级粗匹配或路线端点吸附过远都属于失败，不得自行选择第一个结果。

## 使用依据与取数

高德公开接口文档只支持技术选型，不构成离线保存或视频发布的授权证明。真实取数前必须核验当前账号与用途是否覆盖：

- 路线数据的离线留存；
- 二维衍生画面制作；
- 视频公开发布。

核验结果写入 `request.json.sourceUsage`：核验日期、政策或授权文档引用、适用账号与用途范围、三项覆盖确认、署名要求。授权原件保存在仓库外，材料只留非敏感引用与摘要。三项确认未全部为 `true` 时，`fetch` 在发起任何网络请求前失败；不得用截图、换提供方或虚构坐标绕过。

Key 只从环境变量 `M2V_AMAP_KEY` 读取，不写入材料、响应、日志、异常或 Git。取数先定位端点，再以 `strategy=34`（高速优先）规划路线并显式请求 `polyline`；结果先按离线规则完整校验，再原子替换 `route.json`。失败时旧路线保持不变，不发布半份材料。

## 命令

```powershell
uv run m2v init --type driving-route --project <slug>
# 填写 request.json（含 sourceUsage），设置 M2V_AMAP_KEY 后取数
uv run m2v driving-route fetch --project videos/driving-route/<slug>
uv run m2v validate --project videos/driving-route/<slug>
uv run m2v prepare --project videos/driving-route/<slug>
# 可选局部预演，不能覆盖正式成片
uv run m2v preview --project videos/driving-route/<slug> --start-seconds 0 --end-seconds 6
uv run m2v render --project videos/driving-route/<slug>
```

`validate / prepare / preview / render` 只读取已保存材料，断网且未配置 Key 时仍可执行，不发生外部网络访问。`render` 输出 `outputs/driving-route.mp4`，预演写在 `outputs/previews/`；重复导出在相同有效输入下复用候选。

## 画面与运动契约

- 固定 1920×1080、60 fps、无音轨。默认 30 秒：前 3 秒全程建立，中段 24 秒行驶，最后 3 秒车辆停在终点并拉回全程；显式时长只改变中段行驶时间。
- 地图保持北向，使用深蓝底、灰蓝未行驶路线、青色已行驶路线与浅色小车；只绘制真实路线、端点、必要道路名称和来源署名，不补造城市路网，不使用卫星图或三维地形。
- 小车按累计距离沿折线推进，位置始终在真实轨迹上；朝向用沿线前后各 20～200 米（路线总长的 0.1%）合成单位向量，急弯与角度跨界不突然翻转。已走路线端点与小车共用同一插值结果。
- 跟随时镜头放至全程视图的 2.5 倍，目标取车辆前方沿线位置；进入跟随与结尾拉回都用平稳过渡。开场与收束必须完整显示路线及两端；跟随时车辆始终可见，当前视域内承担信息的道路与地名不被不合理裁切。
- 文字只承担主题、地点、道路名称、距离结果和必要署名。里程只显示 API 返回的总距离与沿路进度，不把压缩行程冒充实时车速或实时导航。署名按来源要求显示，字号小于主体信息，置于次要位置且不遮挡路线、端点或小车。

## 验证与完成边界

`render` 自动验收帧数、画幅、帧率、时长、无音轨与输入绑定，并保留溯源和候选记录。`preview` 只作局部检查，不替代全片复核。

首个作品上海人民广场到郑州二七广场另需独立子代理对当前候选执行视觉评审：路线与贴路转向、镜头衔接、地名可读性、开场全程与结尾收束，关闭全部必改项后才算首例制作完成。技术自动验收通过、缺少当前候选独立视觉评审时，只能报告技术交付。

作品材料、真实响应与生成媒体留在忽略的内容目录或外部内容根，不加入 Git；共享代码、测试与本指南纳入版本控制。
