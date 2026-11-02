## 1. 依赖与变更材料

- [x] 1.1 在 `pyproject.toml` 增加 `psutil`、`fonttools`、`mercantile`、`geographiclib`、`yt-dlp`、`pydantic`，移除只服务字体子集化的可选依赖分组并同步 `uv.lock`。
- [x] 1.2 在 `web/package.json` 增加 `@turf/distance`、`@turf/helpers`、`d3-geo` 与 `@types/d3-geo`，同步锁文件。
- [x] 1.3 更新 README、ARCHITECTURE 与字体恢复说明中的依赖/能力描述。

## 2. 抖音参考素材改用 yt-dlp

- [x] 2.1 新增 yt-dlp 适配层，输出与现有 `normalize_detail` 相同的规范化详情；短链、图文、视频与失败信息保持可读。
- [x] 2.2 `reference.douyin.fetch` 默认走 yt-dlp，失败时自动退回浏览器（可关闭）；来源、摘要、许可与 `recipe.json` 留证不变。
- [x] 2.3 更新抖音相关测试，覆盖 yt-dlp 成功、提取失败与浏览器兜底选择。

## 3. 地理与瓦片数学改用成熟库

- [x] 3.1 Python `driving_route/geometry.py` 使用 `mercantile` 与 `geographiclib`，删除手写投影/haversine/瓦片索引。
- [x] 3.2 检查 `road_trip` 复用路径与新实现一致，瓦片范围边界语义不变。
- [x] 3.3 Web `route.ts` 使用 `@turf/distance` 与 `d3-geo` 替换手写距离/投影，保留贴路、镜头与标签逻辑。
- [x] 3.4 增加跨语言/固定坐标夹具测试，现有 Python 与前端几何/布局测试全部通过。

## 4. 字体 cmap 覆盖改用 fontTools

- [x] 4.1 `core/fonts.py` 用 `TTFont.getBestCmap()` 实现覆盖集合，删除手写 cmap 解析。
- [x] 4.2 调整 `SubsetUnavailable` 与缺失依赖分支，更新字体相关测试与文档。

## 5. 冻结帧检测改用 freezedetect

- [x] 5.1 `engine/qa.py` 增加 freezedetect 调用与日志解析，硬判定和最长冻结区间由 ffmpeg 产生。
- [x] 5.2 保留采样指标与报告字段；把冻结区间换算回采样序号。
- [x] 5.3 用合成冻结片与现有代表成片做新旧对账，更新 QA 测试。

## 6. 进程树内存观测改用 psutil

- [x] 6.1 `engine/perf.py` 用 psutil 重写进程树内存与物理内存总量，删除 ctypes/PowerShell/ps 分支。
- [x] 6.2 保留采样器接口与报告字段，更新性能测试。

## 7. 材料结构校验引入 Pydantic

- [x] 7.1 新增 `src/m2v/core/schema.py`：严格模型基类、中文错误转换与顶层文档校验入口。
- [x] 7.2 为 building-construction 与 vehicle-showcase 定义结构模型并接入 `load_project`，删除重复的结构检查。
- [x] 7.3 为 financial、driving-route、road-trip、general 定义结构模型并接入；业务语义校验保持不变。
- [x] 7.4 逐类型运行材料测试，核对 `match=` 断言与错误路径。

## 8. 验证与交付

- [x] 8.1 运行 `uv run pytest` 与受影响的 `uv run pytest -m "not slow"`；运行 `pnpm -C web test` 与 `pnpm -C web build`。
- [x] 8.2 抽查代表作品的验证/准备与几何输出，确认材料、报告与画面契约无回归。
- [ ] 8.3 检查暂存内容，提交实施结果；同步 `openspec/specs/` 并归档变更。
