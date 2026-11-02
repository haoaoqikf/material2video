## Why

上一轮调研确认项目已经大量复用 Remotion、ffmpeg、Playwright、edge-tts 等成熟组件，但仍有六项基础能力是手写实现：抖音页面解析、地理/瓦片数学、字体 cmap 解析、冻结帧判定、进程树内存观测与材料结构校验。它们要么依赖易变的第三方页面结构，要么把成熟的数学/解析/系统能力重复实现了一遍，维护成本和失效风险都高于引入成熟组件。

本变更只替换这六项 P0 能力，保留项目真正的核心自研部分：逐帧确定性、离线契约、制作证据链、Painter 量测代理与专用画面。替换后对外的材料格式、命令、渲染契约和报告结构保持不变；确有口径变化的项（冻结帧）用并行对账和测试锁定。

## What Changes

- **抖音参考素材抓取**改用 `yt-dlp` 作为主路径：使用其 Douyin 提取器获取页面信息与直链，保留现有来源、摘要、许可与授权留证；原浏览器解析实现降级为 yt-dlp 失败时的自动兜底（可用内部参数关闭），默认不启动 Playwright。
- **地理/瓦片数学**改用成熟库：Python 侧用 `mercantile` 替换手写 Web Mercator 与瓦片索引，用 `geographiclib` 的零扁率球体替换手写 haversine；Web 侧用 `@turf/distance` 替换手写球面距离，用 `d3-geo` 的 `geoMercator` 替换手写投影。镜头、平滑、贴路相位与标签层仍是项目特化逻辑。
- **字体 cmap 覆盖检查**改用 `fonttools`：删除手写 cmap 二进制解析，`fonttools` 从可选依赖提升为运行时依赖；缺字即失败、单字体严格检查与跨字体并集检查的语义不变。
- **冻结帧检测**改用 ffmpeg `freezedetect`：硬判定与最长冻结区间由 ffmpeg 产生，采样的重复率/近似静止率/画面指标仍保留；报告字段形状与阈值语义不变。
- **进程树内存观测**改用 `psutil`：替换 Windows CIM/PowerShell 与 POSIX `ps` 分支，保留采样间隔、峰值语义与 `None` 缺项约定。
- **材料结构校验**引入 Pydantic v2 作为结构层：各类型的顶层文档、必填字段、类型、未知字段与数值边界由模型校验；路线连续性、价格覆盖、投资计算等业务语义仍由现有校验器负责。错误消息统一转换为现有的 `路径: 中文说明` 形状。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `reference-media-acquisition`：抖音参考素材默认改用 yt-dlp 提取，浏览器解析保留为兜底。
- `driving-route-video`、`road-trip`：地理与瓦片数学改由成熟库提供，画面契约与材料格式不变。
- `font-coverage`：cmap 覆盖判定改由 fontTools 提供，判定语义不变。
- `material-sourcing`、`general-video-composition`：技术 QA 的冻结帧硬判定改由 ffmpeg freezedetect 提供，报告字段不变。
- `remotion-renderer`：性能报告中的进程树内存改由 psutil 采样，报告字段不变。
- `modular-video-production`：材料结构校验增加 Pydantic 结构层，业务语义校验保持不变。

## Impact

- Python 依赖：新增 `psutil`、`fonttools`（由可选转必需）、`mercantile`、`geographiclib`、`yt-dlp`、`pydantic`。
- Web 依赖：新增 `@turf/distance`、`@turf/helpers`、`d3-geo` 与 `@types/d3-geo`。
- 代码：`src/m2v/reference/`、`src/m2v/types/driving_route/`、`src/m2v/types/road_trip/`、`src/m2v/core/fonts.py`、`src/m2v/core/schema.py`（新增）、`src/m2v/engine/qa.py`、`src/m2v/engine/perf.py`、`web/src/types/driving_route/route.ts` 及各类型材料模块。
- 文档：`README.md`、`ARCHITECTURE.md`、字体恢复说明、`docs/PROJECT_PLAN.md` 的依赖与能力描述。
- 不改变作品材料 schema 版本、CLI 命令、渲染画幅、报告字段或已有成片；不为兼容旧实现保留双路径分支。
