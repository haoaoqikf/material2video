# 多日地图游记视频

`road-trip` 制作真实路线的多日竖屏地图游记：1080×1920、30 fps、有旁白、字幕、
音效与程序化音床。作品只有一份 `trip.json`，每日路线放在 `routes/day-XX.json`，
由 `trip.json` 引用，不进入作品材料清单。

## 适用范围

- 需要连续多天、沿真实道路前进的游记；路线由高德驾车服务取数并离线保存。
- 旁白至少一段；无旁白作品不属于本类型，请使用 `driving-route`。
- 不导入照片、实拍或三维车；不做横屏版本。
- 不兼容旧材料：`trip.json` 与每日路线都只接受当前 `schemaVersion: 1`。

## 材料

### `trip.json`

```json
{
  "schemaVersion": 1,
  "title": "成都 → 拉萨：318 川藏南线七天",
  "start": {"city": "成都市", "address": "成都市天府广场", "label": "成都"},
  "end": {"city": "拉萨市", "address": "拉萨市布达拉宫广场", "label": "拉萨"},
  "routePreference": "g318",
  "targetSeconds": 180,
  "sourceUsage": {
    "verifiedOn": "2026-10-31",
    "documents": [{"title": "高德开放平台服务条款", "url": "https://lbs.amap.com/"}],
    "account": "授权账号与用途范围",
    "purpose": "离线保存路线、二维衍生画面与视频发布",
    "offlineStorage": true,
    "derivativeFrames": true,
    "videoPublication": true,
    "mapTiles": true,
    "attribution": "地图数据 © 高德地图"
  },
  "sources": [
    {"id": "s1", "title": "折多山海拔资料", "url": "https://example.com/source", "publisher": "来源机构"}
  ],
  "days": [
    {
      "id": "day-01",
      "title": "成都 · 翻越二郎山",
      "subtitle": "从平原进入横断山脉",
      "destination": {"city": "康定市", "address": "康定市炉城镇", "label": "康定"},
      "via": [{"city": "雅安市", "address": "雅安市雨城区", "label": "雅安"}],
      "route": "routes/day-01.json",
      "basemapStyle": "road",
      "narration": [{"id": "day-01-opening", "text": "第一天从成都出发，沿川藏南线向西。"}],
      "cards": [{"id": "day-01-card", "title": "折多山垭口", "facts": [
        {"id": "altitude", "label": "海拔", "value": "4298 米", "sourceId": "s1"}
      ]}],
      "landmarks": []
    }
  ],
  "effects": [
    {"id": "day-01-start", "anchor": {"kind": "day-start", "dayId": "day-01"}, "builtin": "transition", "gainDb": -22}
  ]
}
```

规则：

- 不接受手填总里程、每日时长或起终点坐标；画面里程与时间轴从路线和实测口播派生。
- 每日 `route` 固定为 `routes/<天 id>.json`；`days[].id` 必须形如 `day-01` 且唯一。
- 数据卡事实带 `value` 时必须提供 `sourceId`，并指向 `sources` 中已登记来源。
- 旁白段可选 `anchor`，把地标句对齐到当天路线里程碑：
  `{"kind": "landmark", "landmarkId": "..."}` 或 `{"kind": "arrival"}`；
  未声明时按顺序紧接上一段播放。锚点只影响时间轴，不改变路线材料。
- 音效来源四选一：`builtin`、`synthesis`、`assetId`、`sourceRef`。
- 音效锚点：`trip-start`、`trip-end`、`day-start`、`day-arrival`、
  `segment-start`、`segment-end`、`landmark`；按天锚点必须同时写 `dayId`。
- `targetSeconds` 是软目标：旁白更长时成片随口播增长，超过 600 秒直接失败。

### `routes/day-01.json`

由 `m2v road-trip fetch` 生成，不应手改。它保存定位点、真实道路步骤、成本、
城市与行政区，以及 via 与地标在步骤链上的位置。`requestDigest` 只覆盖
`dayId`、`start`、`destination`、`via`、`routePreference` 与坐标系；修改旁白、
卡片或时长不会让路线失效，修改 via 或目的地会。

## 命令

```bash
uv run m2v init --type road-trip --project 318-chuanzang
uv run m2v road-trip fetch --project <作品目录>
uv run m2v road-trip basemap --project <作品目录>
uv run m2v prepare --project <作品目录> --voice zh-CN-YunxiNeural
uv run m2v preview --project <作品目录> --start-seconds 0 --end-seconds 30
uv run m2v render --project <作品目录>
```

- `fetch`：第 1 天定位行程起点，第 N 天起点取第 N−1 天终点；每天按 via 顺序分段
  规划并合并。凭据只从 `M2V_AMAP_KEY` 读取；三项使用确认与 `mapTiles` 未落实时
  不发起网络请求。全部路线先在内存中校验，再逐份原子替换；失败恢复旧路线。
- `basemap`：生成全局概览、每日概览与每日跟随瓦片走廊。走廊只依赖路线与静态
  布局，改旁白不需要重新取图。单日上限 2200 块，全片上限 6000 块 / 500 MB，
  超限失败并报告实际值。
- `prepare`：逐段合成旁白并生成同步字幕，混入音效与 30 秒程序化音床，母版归一化
  到 −14 LUFS / ≤−1 dBTP。准备记录只保存底图路径与摘要，不内嵌 data URI。
- `render/preview`：正式成片必须带音轨；预演从母版切出对应区间，只写入
  `outputs/previews/`。

## 画面契约

- 每日镜头：章节卡 → 8× 推近到 12× → 12× 匀速跟随 → 收束到当天概览；
  最后一天结束后可继续收束到全局概览。
- Day 4 在怒江七十二拐窗口把跟随倍率平滑提高到 14×；窗口与倍率来自
  `web/src/types/road_trip/layout.json`，不逐帧计算。
- 跟随段相机平移对齐整像素；底图、路线与标签共享同一重采样相位。
- 章节卡与数据卡不得遮挡字幕安全区；字幕安全区来自 `web/src/frames.json`。
- 渲染时注入本地静态服务地址，只挂载当前视口可见瓦片；全程不访问外网。

## 验收

1. `m2v validate` 通过；材料与路线的摘要已记录。
2. `m2v road-trip basemap` 复用或生成底图，并核对每日走廊与全片预算。
3. Day 4 单日样片先通过技术验收与独立视觉评审，再进入全片。
4. 全片复核：轨迹与材料一致、日间衔接连续、旁白字幕同步、响度达标、
   无外网请求、独立评审必改项全部关闭。

作品材料、底图、音床与成片属于内容，不进入版本控制；类型代码、测试与文档进入版本控制。
