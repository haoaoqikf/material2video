## 背景

现有 `tts.py` 以「后端 → 音色格式 → 合成 → 词边界 → 缓存键」为统一链路，edge-tts 与 Kokoro 都能返回真实词边界。Qwen3-TTS Base 模型支持零样本克隆，但 `generate_voice_clone` 只返回波形与采样率，不返回文本 token 的时长或对齐信息。新增后端不能绕开现有字幕与停顿整形契约，也不能用字符比例估算时间。

## 决策

### 1. 后端标识、音色格式与作品属性

`tts.backend` 接受 `edge-tts`、`kokoro`、`qwen3-tts`，省略仍为 `edge-tts`。Qwen3-TTS 音色必须是 `clone_<slug>`，与实际音色档案解耦；音色档案保存在作品内 `models/qwen3-tts/registry.json` 的 `voices` 数组，包含：

- `voice`：`clone_<slug>`，与 `project.json` 对应；
- `refAudio`：参考音频在 `models/files/` 下的相对路径；
- `refText`：参考音频的逐字文本；
- `language`：例如 `Chinese`；
- `sha256` / `bytes`：参考音频摘要与大小；
- `source` 与 `authorization`：来源平台、作品 ID、作者、用户明确要求的原文与使用范围。

切换音色或参考音频摘要都会改变缓存键与准备指纹；不把参考音频放进 `assets/` 的成片媒体映射，避免被误用为画面或音床。

### 2. 模型与对齐模型按作品恢复

新增 `models/qwen3-tts/registry.json`，登记：

- Qwen3-TTS 主权重、config、tokenizer 文件与 speech tokenizer（约 2.5GB）；
- stable-ts 使用的 `Systran/faster-whisper-small` 对齐模型（约 486MB）；
- 每个文件的 `role`、`file`（相对 `models/files/`）、`bytes`、`sha256` 与许可。

`models/qwen3-tts/fetch.py` 默认离线从 `M2V_TTS_CACHE`、`models/.cache`、`models/files/` 查找；显式 `--download` 才联网。Qwen 文件优先使用 ModelScope（`MODELSCOPE_ENDPOINT` 可覆盖），对齐模型使用 `HF_ENDPOINT`（默认 `https://huggingface.co`）。下载后校验摘要，拒绝覆盖漂移文件。模型与对齐文件都放在 `models/files/` 下，沿用现有 `.gitignore`，不新增需要忽略的二进制目录。

### 3. 合成与确定性

- 使用 CPU、`torch.float32`、`attn_implementation="eager"`，避免作品依赖 CUDA 与 flash-attn。
- 同一进程内按模型目录缓存模型、按音色缓存 `voice_clone_prompt`，避免每段重建参考编码。
- 每次合成前以 `sha256(seedVersion|voice|refSha256|rate|text)` 派生 32 位种子并 `torch.manual_seed`；实测同一文本两次生成的 PCM 摘要一致。采样参数沿用模型 `generation_config.json`（`do_sample=true`、`temperature=0.9` 等），不改为贪心。
- `tts.rate` 用 librosa `time_stretch` 实现不变调变速；`+20%` → `rate=1.2`。变速在生成后、对齐前完成。

### 4. 时间戳：按原文强制对齐

没有采用：

- 字符比例估算：现有字幕契约明确禁止猜测时间。
- ASR 自由转写后与原文做 diff：中文转写文本常与原文不等，现有 `_walk_words` 要求 token 是原文子串，会误判。
- 自建强制对齐模型：stable-ts 已提供成熟的按原文对齐，能与现有 faster-whisper small 模型复用。

流程：

1. 生成并变速，写临时 WAV。
2. `stable_whisper` 以 `faster-whisper-small` 对**最终音频**与**旁白原文**执行 `align(audio, text, language="zh")`。
3. 取 `segments[].words`，去除空白；按原文顺序校验每个 token 是原文子串。
4. 零时长 token 修复：无标点的零时长 token 并入下一个有时长 token 的文本前缀；带标点的零时长 token 并入前一个 token 的文本尾；最后一个零时长 token 并入前一个。合并只改 token 分组，不改任何时间值，也不新增估算时间。
5. 交给现有 `cues_from_words` 做最终单调性、覆盖与标点校验；失败即准备失败，不写时间轴。

stable-ts 返回的 `word.start/end` 是模型对齐结果，不是按字符比例推导；修复只处理退化的零长度边界。

### 5. 输入限制

当前版本只接受中文旁白（允许中文标点与空白）。数字和拉丁字母在中文对齐中可能被改写或无法稳定映射回原文，必须在合成前失败并提示改写或改用 edge-tts；不跳过时间戳、不估算。

### 6. 速率、缓存与版本

`scene_cache_key` 对 `qwen3-tts` 加入：

- 后端标识、模型 revision、对齐模型 revision；
- `qwen-tts`、`transformers`、`torch`、`stable-ts`、`faster-whisper`/`ctranslate2` 版本；
- 音色档案摘要（参考音频 SHA256 + 参考文本 + 语言）；
- 生成器种子版本。

切换后端、模型、对齐模型、参考音频或参考文本都会生成新缓存，不命中旧音频。

### 7. 兼容与边界

这是新增后端，不改变 edge-tts/Kokoro 的既有配置、缓存键或行为。作品运行时与主项目、模板保持镜像；旧作品不自动升级。新作品从当前模板复制运行时，旧作品目录与证据保留。

### 8. 本片重制

新目录 `videos/documentary-edit/stop-living-for-others-clone`，只改 `project.json` 的 `tts` 与作品 id/标题无关字段；分镜、画面、字幕文本、音床、场景代码保持不变。参考音色取参考视频 60–68 秒的完整句，参考文本经转写与人工校正。首轮按原作品 `+20%` 准备后，12 条字幕超过 9 字/秒、全片仅 29.6 秒；改为 `-10%`，使全片时长接近原作品 39.5 秒并恢复阅读舒适度。语速是配音参数，不改变分镜、字幕文本与画面；不截断口播。

## 复现与验证

- 配置：后端/音色格式匹配；非法组合、缺失模型、摘要不符在合成前失败。
- 确定性：同文本两次生成的 PCM 摘要一致；变速后仍一致。
- 对齐：真实词边界单调、覆盖原文、落在音频内；零时长 token 合并后 `cues_from_words` 通过。
- 缓存：切换后端/参考音频不命中旧缓存。
- 恢复：清空 `models/files/` 后 validate 失败，`fetch.py --download` 恢复且摘要一致。
- 本片：prepare、validate、QA、全片 render 与独立终审；核对时长、字幕、音床与参考音色相似度。
