## Context

现有实现里，六项基础能力都是手写的：抖音页面 RSC 解析、Web Mercator 与 haversine、字体 cmap 二进制解析、冻结帧像素差、进程树内存抓取、各类型材料结构校验。它们大多有成熟、许可证宽松、支持 Windows 的替代品。项目真正的约束是逐帧确定性、离线渲染、证据链与中文错误语义，因此替换必须限定在“工具/数学/解析”层，不能把相机、贴路、量测代理或制作门交给通用库。

## Goals / Non-Goals

**Goals:**

- 用成熟组件替换六项 P0 基础能力，减少易失效的页面解析与重复数学实现。
- 保持现有材料格式、CLI、渲染契约、报告字段和错误语义不变。
- 用可复现的测试和并行对账锁定几何、冻结帧与字体覆盖的结果。
- 新增依赖全部支持 Windows 与 Python 3.11+，许可证与项目兼容。

**Non-Goals:**

- 不替换 Remotion、ffmpeg、Playwright、Edge TTS 等已经在用的外部组件。
- 不替换制作门、证据链、评审包、Painter 量测代理、相机/贴路/标签等核心自研逻辑。
- 不改变视频类型、画幅、帧率、材料 schema 版本或成片内容。
- 不为旧实现保留长期双路径或迁移工具。

## Decisions

### 1. 抖音抓取以 yt-dlp 为主路径

`yt-dlp` 自带 Douyin 提取器，能处理短链跳转、页面信息与直链；项目继续负责保存目录、来源/摘要/许可留证和授权检查。原 Playwright 页面解析保留为 yt-dlp 失败时的自动兜底（`fallback_browser=False` 可关闭），默认路径不启动浏览器。这样可以删除默认路径对 `a_bogus` 页面结构的依赖，同时保留风控或提取器失效时的可操作后路。

### 2. 几何只替换纯数学层

Python 侧：

- `mercantile.xy` / `mercantile.lnglat` 替换 `project` / `unproject`；两者与现有公式逐位一致（已实测）。
- `mercantile.xy_bounds` 提供瓦片轴边界，替换手写瓦片索引；bbox 边界语义用现有测试锁定。
- `geographiclib.Geodesic(6371008.8, 0.0)` 替换手写 haversine；零扁率球体与现有公式数学等价（真实 937 公里路线累计差约 1.3×10⁻⁸ 米）。

Web 侧：

- `@turf/distance` 替换 `haversineMeters`；单位、地球半径与现有实现一致，差异在浮点末位。
- `d3-geo` 的 `geoMercator().scale(6378137).translate([0, 0])` 替换 `projectPoint`；输出与现有局部投影在浮点末位内一致（已实测）。
- `pointAtDistance`、`smoothedPointAtDistance`、`headingAtDistance`、相机、瓦片可见性与标签仍是项目特化逻辑，不交给 turf。

### 3. fontTools 承担 cmap 覆盖

用 `TTFont(...).getBestCmap()` 取得“有字形”的码位集合，替换手写 cmap 格式 4/12 解析。`fontTools` 已用于子集化，提升为必需依赖；子集能力不再因缺少可选依赖而不可用，“缺字即失败”的语义保留。字体文件损坏仍抛可读错误，并按现有 `audit_fonts` 的“跳过认不出的字体”策略处理。

### 4. freezedetect 负责硬判定，采样负责测量

ffmpeg `freezedetect=n=1e-6:d=0.1` 在原生分辨率上产生冻结区间；最长区间与 `status` 由它决定。采样帧仍用于 `minDelta`、`meanDelta`、`duplicateRatio`、`nearStillRatio` 与 banding/aliasing 指标，报告字段保持不变。`longestStillRange` 由冻结区间的秒数换算回采样序号。纯帧列表调用保留为单元测试用的降级路径，生产路径始终传入视频。

### 5. psutil 负责进程树内存

`psutil.Process(pid).memory_info().rss` 加递归子进程求和，替换 CIM/PowerShell 与 `ps` 分支。采样线程、峰值、间隔与“取不到返回 None”的约定不变；`environment()["memoryGiB"]` 改用 `psutil.virtual_memory().total`。

### 6. Pydantic 只做结构层

新增 `src/m2v/core/schema.py`：

- 模型基类固定 `extra="forbid"`、`strict=True`，保持“未知字段拒绝”和“布尔不算数字”的现有语义。
- `validate_model(model, value, path)` 把 `ValidationError` 转成 `M2VError("路径: 中文说明")`，避免 Pydantic 英文默认消息泄露到 CLI。
- 各类型为顶层文档和主要嵌套对象定义模型；业务规则（路线连续性、价格覆盖、投资计算、阶段首尾相接等）仍在原校验器中。

这样结构校验有单一来源，同时不把产品语义塞进通用框架。迁移按类型分批，先做结构最清晰的 building-construction 与 vehicle-showcase，再覆盖 financial、driving-route、road-trip、general。

## Risks / Trade-offs

- **yt-dlp 受平台风控影响**：可能需要 cookies 或更新提取器；保留 `--fallback-browser`，并在失败信息中给出明确指引。
- **几何浮点末位差异**：turf/geographiclib 与手写公式的运算顺序不同，可能在末位产生差异；用现有几何/布局测试和代表帧比对，若超过像素容差则保留手写投影而只替换距离/瓦片。
- **freezedetect 口径变化**：阈值 `n=1e-6` 已用合成冻结片校准；仍可能把极慢运镜判为冻结。保留 `NEAR_STILL_DELTA` 测量项，并对现有代表成片做新旧对账。
- **Pydantic 错误消息变化**：必须逐类型核对测试中的 `match=` 断言；无法保持的中文消息在模型层显式覆盖。
- **依赖体积增加**：新增 yt-dlp、pydantic、fonttools、mercantile、geographiclib、psutil 与前端 turf/d3-geo；这是用可维护性换安装体积，符合本次用户要求。
- **字体许可**：fontTools 只解析字体，不改变字体登记、摘要与许可台账。
