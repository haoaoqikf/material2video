## 1. 契约与运行时

- [x] 1.1 扩展 `capture` 子 schema（`mode/jobs/blockFrames/verifyFrames`），pure 隐含全局时间；运行时字段不进入缓存键。验证：`uv run pytest tests/test_code_scenes.py -q`。
- [x] 1.2 `capture-clock.js` 增加绝对 `seek`，`host.tsx` 增加 `startAt`/`seekToSubframe` 与 `captureStartFrame` 初始挂载。验证：新增浏览器慢测，pure 场景可倒序 seek。
- [x] 1.3 `_capture` pure 分支只遍历目标帧；`lookdev.native_stills` 直接 seek；`--det` 对 pure 场景乱序验证。

## 2. 纯性验证与缓存

- [x] 2.1 静态闸门：作品根与所选风格包源码扫描；拒绝计时器/随机源/CSS 动效/`useFrame`/ECharts/自走媒体。验证：`tests/test_source_policy.py`。
- [x] 2.2 动态探针：正序/倒序 PSNR ≥ 60 dB，receipt 记录 `verified/contract/probes/minPsnr`；pure 缓存要求 `verified=true`。
- [x] 2.3 把 PSNR 抽到中立模块；`implementation_inputs()` 纳入采集实现并升级 contract。

## 3. 分块并行采集

- [x] 3.1 块对齐、`materialize` 扩展窗口与 `mediaStartFrame` 同步。验证：先预览后全片，块复用、帧数一致。
- [x] 3.2 在 `capture.py` 增加块调度与拼接，新增 `worker.py` 作为分块子进程入口；失败清理、已成功块保留。验证：`jobs=2` 与 `jobs=1` 帧数/PSNR 一致。
- [x] 3.3 更新 `tests/_helpers.py` 夹具签名。

## 4. 分段最终渲染

- [x] 4.1 新增 `engine/remotion/segments.py`：元数据校验、区间切分、逐段验收、concat、总帧数复核。验证：`tests/test_render_segments.py`。
- [x] 4.2 `explainer_render._generate` 接入 `jobs>1`，音频拼接后统一 mux；`--jobs` 不进入 delivery binding。
- [x] 4.3 CLI `--jobs`、`VideoType` 能力标记与 general 适配器；其他类型拒绝 `jobs>1`。验证：CLI 非法值在渲染前失败。

## 5. 文档、示例与归档

- [x] 5.2 更新 `code-scene-runtime.md`、`storyboard-schema.md`、`README.md`、`ARCHITECTURE.md`。
- [x] 5.3 长片只读基准：`earth-night-lights` 后段预览、`labor-rights-ten-events` jobs 对照；记录耗时、帧数、PSNR。
- [x] 5.4 全量验证、提交、归档并同步主规格。

> 2026-11-12 内容清理：已删除用户指定作品的专属内容；本档案仅保留其余历史范围，不代表本轮重新验证。
