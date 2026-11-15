# 本机素材推理环境恢复与验证（2026-11-15）

本轮完成模型读取恢复、锁定依赖恢复、四类模型真实推理，以及获取到作品导入的完整技术链路。按简单变更处理：保留现有模型、命令和材料契约，只修复实测暴露的长 GOP 精裁缺陷并记录结果。本页不代表正式视频制作或视觉终审通过。

## 机器与依赖

- Windows 11 专业版，Intel Core Ultra 5 125H，14 核 / 18 线程，约 32 GB 内存；检查时可用约 14 GB，C 盘剩余约 424 GiB。
- Intel Arc 核显；本轮实际使用 CPU，不调用 Intel GPU / NPU 或 CUDA。
- Python 3.12.10；`uv sync --locked --extra index` 成功恢复 49 个包，没有修改 `pyproject.toml` 或 `uv.lock`。
- `doctor` 检查的 12 项推理相关包版本全部匹配模型登记，包括 torch 2.15.0、transformers 5.23.0、faster-whisper 1.2.1、RapidOCR 3.10.0、ONNX Runtime 1.32.0；torch 实际构建为 2.15.0+cpu。av 18.1.0 另按已安装包清单核对，它不在 doctor 的 12 项登记中。
- FFmpeg 7.1、ffprobe 9.0.2 和固定版本 yt-dlp 2026.10.26 可执行。平台下载不在本轮验证范围。

以后恢复或运行推理工具时显式带上 `--extra index`，例如：

```powershell
uv sync --locked --extra index
uv run --locked --extra index m2v author assets doctor --workspace outputs/materials --models outputs/materials/models --json
uv run --locked --extra index m2v author assets models verify --workspace outputs/materials --models outputs/materials/models --json
```

## 文件读取故障与恢复

旧 `outputs/materials/models/` 中四组模型共 20 个文件可以读取文件大小，但读取内容均返回 `PermissionError`，文件 ACL 查询也被拒绝；上层目录 ACL 可以读取。同一目录内 `.hub-cache` 的对应文件全部可读取。没有证据表明模型内容损坏；具体拒绝访问的 ACL 项因无法读取而未确认。

恢复过程没有修改 ACL、所有者或模型登记，也没有重新下载权重：

1. 使用现有 `ModelManager.prepare` 的下载器注入接口，从可读缓存复制到新目录；逐文件验证登记大小与 SHA256，通过后才发布。
2. 先确认所有移动路径位于仓库 `outputs/materials/` 内，且恢复目录和备份目录尚不存在。
3. 保留旧目录为 `outputs/materials/models-unreadable-20261115/`，将已校验的新目录替换为原来的标准模型根；保留并迁回可读的 `.hub-cache`。
4. 在标准根重新验证四组模型；最终 `models verify` 也报告 4/4 通过。随后真实推理均读取这个标准根。

恢复结果在本机 `outputs/materials/runtime-recovery-20261115.json`；旧不可读原件保留供需要时进一步诊断，不作为推理输入。

## 逐项真实运行

输入为既有 5.68 秒合成技术片段，含中文语音、烧录文字和彩条，以及三张 Commons 真实照片（厨房备餐、舞台舞者、过街人群）。技术片段的旁白和文字不证明相应实景出现；它只用于验证语音、OCR、时间窗口和字节绑定。照片沿用原来源快照与摘要，从本地缓存获取。

每项由独立 CLI 进程执行，耗时包含导入、模型加载、摘要核验与写入，并非纯模型计算耗时。控制器每 0.1 秒采样子进程树 RSS 的和，不计控制器；采样峰值可能遗漏瞬时峰值，也不等于全系统内存。以下为开发负载下的单次实测，不是独占机器基准；首次 E5 耗时未进一步拆分归因。

| 工作 | 输入 / 输出 | 耗时 | 采样峰值 RSS |
|---|---|---:|---:|
| ASR | 5.68 秒音轨 → 两句中文、21 个词时间码 | 6.65 s | 615.6 MiB |
| OCR | 视频 3 帧 → 3 条识别 | 9.47 s | 309.6 MiB |
| E5 文本索引 | 字幕、ASR、OCR → 7 条文本向量 | 71.94 s | 1330.0 MiB |
| SigLIP 视觉索引 | 视频 3 帧 → 3 条视觉向量 | 12.42 s | 2060.9 MiB |
| 照片 OCR | 3 张照片 → 3 条识别 | 17.17 s | 584.3 MiB |
| 照片视觉索引 | 3 张照片 → 3 条视觉向量 | 28.11 s | 2488.3 MiB |
| 文本语义查找 | 中文原句 → 1 个候选 | 15.69 s | 1318.4 MiB |
| 照片视觉查找 | “厨房里准备食物的人” → 厨房照片第 1 | 22.92 s | 2078.7 MiB |
| 视频四通道融合查找 | “人群沿着街道行走” → 2 个候选 | 20.85 s | 2732.3 MiB |

ASR 实际输出为“上海城市夜景在黄浦江边亮起”“人群沿着街道行走”，与已知配音文本一致；视频 OCR 识别到“上海城市夜景”“人群沿街行走”。照片 OCR 只验证运行成功，没有将照片中的全部识别结果判为正确。词面与元数据查找也返回非空候选。视频彩条的视觉相似结果只说明通道运行，不能当作夜景或人群画面命中。

三张照片的视觉查找有厨房正例排第 1，但同时返回了彩条负例；不能据此宣称检索准确率。原有跨题材效果边界仍以[素材工作层实测记录](material-acquisition-evaluation.md)为准。

## 获取到作品导入

- 使用新工作库，依次执行 `fetch --local`、七通道 `index`、各通道及融合 `find`、视频与照片 `preview`、25 fps `select --import`。
- 实际查看生成的接触表：视频为带中文文字的彩条测试片段；照片候选第 1 为实际厨房备餐照片。HTML、接触表和短视频已生成。
- 新建 `videos/text-motion/material-runtime-check-20261115/` 技术验证工程，按本工程字体登记从本地缓存恢复两项字体；导入素材 ID 为 `runtime-night-city`。
- 请求视频窗口为 2.84–5.68 秒；输出为 2.80 秒、25 fps、有音轨。实测起点误差 0 us，终点与时长误差均为 -40000 us（一帧），音轨偏移 0 us，符合既有精裁误差要求。
- 作品内媒体实际摘要、正式登记、选择输出与 receipt 摘要一致；正式登记内容摘要与凭据一致。作品内 receipt 及工作库操作均为 `committed`。
- 禁止 `MaterialStore` 构造后调用 `verify_project_media`，仍得到 1 件媒体通过、无问题；证明该校验不需要读取共享工作库。
- 实际 `m2v validate --project videos/text-motion/material-runtime-check-20261115` 退出 0，输出“材料校验通过”。工程仅保存本次导入，不宣称已将片段编排为正式成片。

本机原始输入、命令参数数组、逐项 stdout/stderr、时间与内存记录位于 `outputs/material-runtime-20261115/`，总表为 `benchmark.json`，最终状态为 `end-to-end-completed`；该目录与验证作品、模型、媒体均按既有规则不入库。

## 精裁缺陷、验证与复核

真实候选第一次精裁报 `timeline-unverified`。旧实现通过 ffprobe 的 `%+#60` 读取固定包数；seek 回到前一个关键帧后，60 包可能在请求位置之前耗尽。按 [ffprobe 官方说明](https://www.ffmpeg.org/ffprobe.html)，seek 不精确，相对时长也从实际 seek 点计算，因此改用源 PTS 坐标的绝对终点，覆盖请求点之后一秒，同时计入非零视频原点。实际起点仍从返回的真实帧 PTS 测量，未放宽误差校验。

- 新增长 GOP 回归，分别覆盖零与五秒源原点，以及超出视频末尾仍拒绝的边界；修复前两项都复现失败。
- 修复后仅执行 `tests/common/test_material_selection.py -m media`：6 passed，覆盖新增边界及原有预览、精裁、导入幂等、凭据失败恢复。
- selection 与对应测试的 compileall、`uv lock --check --offline`、Git diff 空白检查通过；没有运行全仓回归。
- 只重试失败的精裁导入；已经完成的模型推理、检索和预览未重跑。首次失败和后续成功的原始日志都保留。

主代理代码自审：**93/100，非独立审查**。逻辑影响限于真实精裁起点测量，不改变 CLI、schema、输出帧率、音轨或一帧误差要求；补齐本地输入协议限制。性能上，长 GOP 需要从前一关键帧读取到请求位置，会比原来过早结束的探测读取更多帧；仍受 120 秒子进程时限约束。现有存储、模型和外部工具均复用，没有新增依赖。

扣分与剩余风险：未覆盖全部容器、极长 GOP 和稀疏/VFR 时间戳组合，未做长片吞吐与并发压力测试；未测试 Intel 加速或平台下载；本轮是环境与技术链路验证，没有进行正式作品视觉终审。当前硬件已能运行这组 CPU 模型，但这些单次短样本耗时不外推为任意长视频的处理速度。
