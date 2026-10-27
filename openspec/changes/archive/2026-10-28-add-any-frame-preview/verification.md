# 验证记录

## 变更 B：add-any-frame-preview

### 单元测试

```powershell
$env:PYTHONIOENCODING='utf-8'
uv run pytest tests/test_cinematic_lookdev.py tests/test_cinematic_commands.py -q
# 30 passed
```

新增覆盖：

- `seconds_to_frame`：四舍五入、上下界夹取；`NaN`/`inf`/字符串拒绝。
- `check_frames`：合法帧通过；越界、负值、不属于任何幕、空列表分别失败。归属校验先于浏览器启动。
- `uniform_frames`：两端包含、单帧区间、`count<1`、终点早于起点。
- `sheet_frames`：秒列表去重、单个整数均匀取帧、越界与非法输入。
- `motion_frames`：区间取帧、反向区间、超出成片时长。
- `sheet_columns`：按张数递增列数。
- `contact_sheet` 标注：ASCII 清洗，中文标注不导致 ffmpeg 解析失败。
- 模式互斥：三模式两两互斥、与 `--stills` 互斥。
- `psnr`：完全一致为 `inf`，全黑对全白低于阈值。
- `_image_size`：非 PNG 明确失败。
- CLI：三个参数可解析；转发时未声明 `--stills` 不伪造张数。

### 全量快速回归

```powershell
uv run pytest -m "not slow" -q -p no:randomly
# 100% passed（含 4 个 skip）
```

### 端到端（videos/general/olbers-night）

```
m2v prepare --project videos/general/olbers-night
m2v lookdev --project ... --sheet 1 4 7     # 3 帧，columns=3，产物 outputs/lookdev/sheet.png
m2v lookdev --project ... --motion 1.5 3.5  # 12 帧，columns=4，产物 outputs/lookdev/motion.png
m2v lookdev --project ... --det             # 8 帧全部 pass，psnr 为 null（完全一致），退出码 0
```

拼图实际打开核对过：三格分别标注 `1-1.00s-f30`、`2-4.00s-f120`、`3-7.00s-f210`，字幕与转场由共享 composition 正确合成。

### 过程中发现并修复的两个实现缺陷

1. **标注互相覆盖**：最初的实现把三组 `drawtext` 串在 `tile` 之前。该滤镜链对每个输入帧都执行，三组标注叠在同一位置，结果是每一格都标着最后一个时刻（首轮拼图三格全是 `3-7.00s-f210`）。改为逐张先打标再拼。
2. **filter 解析失败**：标注文本含冒号与空格时 ffmpeg 报 `Error parsing a filter description`。改为只保留数字、字母与点，其余替换为连字符。

### 未覆盖项

- 未在长片（600 秒上限）末段实测取点耗时。按实现推断代价与该幕内最晚时刻成正比；文档已写明「越靠后的时刻越慢」，但无实测数字。
- 未验证 `--still-scale 2` 与三种取点模式组合下的表现：`native_stills` 按 `captureScale` 走同一路径，本轮只跑了 1 倍。规格层面无额外要求，但缺少实测。
