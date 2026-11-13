## Why

用户要求用抖音参考视频的音色重制 `stop-living-for-others`，并另建作品目录。现有 edge-tts 与 Kokoro 后端都只能使用预置音色，无法从参考音频克隆音色。Qwen3-TTS-12Hz-0.6B-Base 已开源，可在本机 CPU 上完成零样本音色克隆；实测固定种子可逐位复现，生成后用 stable-ts 按原文强制对齐可得到真实词边界，能够进入现有字幕断句与停顿整形链路。

## What Changes

- 新增共享 TTS 后端 `qwen3-tts`（Qwen3-TTS-12Hz-0.6B-Base）：作品在 `project.json` 的 `tts.backend` 声明，`tts.voice` 使用 `clone_<slug>`，音色由作品内登记的参考音频、参考文本与语言定义。
- 参考音频、模型权重与对齐模型按作品内 `models/qwen3-tts/registry.json` 登记的大小与 SHA256 校验；缺失或摘要不符时准备前失败，由作品内 `models/qwen3-tts/fetch.py` 恢复。模型二进制不进入 Git。
- Qwen3-TTS 不返回词级时间戳。合成后用 stable-ts 对生成音频做**按原文强制对齐**，得到与 narration 原文逐词对应的真实词边界；零时长 token 通过文本保序合并修复，不按字符比例估算，不从 ASR 自由转写反推。
- `tts.rate` 映射为变速；在变速后的音频上做对齐，词边界与最终音频同源。
- 语音缓存键纳入后端、模型与对齐模型 revision、Qwen/transformers/torch/stable-ts 版本及参考音频摘要；准备记录与成片溯源保存实际后端和音色。
- `m2v voices --backend qwen3-tts` 读取作品内登记的克隆音色；`--backend` 覆盖与主项目、模板、作品运行时镜像同步。
- 新建 `videos/documentary-edit/stop-living-for-others-clone`，复制原作品并仅更换配音后端与音色；原目录及其证据保留。新作品重新准备、渲染、QA 与独立终审。
- 参考音色必须记录用户明确要求与来源；不把用户授权表述为原作者许可。

## Capabilities

### New Capabilities

- `speech-synthesis-backends`：新增 Qwen3-TTS 声音克隆后端的可验证契约（模型与参考音色恢复、确定性、强制对齐时间戳、变速、缓存与失败行为）。

### Modified Capabilities

- `assistant-voice-selection`：音色格式与候选按后端区分，增加克隆音色档案与参考音频摘要的可追溯性。
- `standalone-video-projects`：使用 Qwen3-TTS 的作品必须在自身依赖、模型登记与恢复入口中声明模型、对齐模型、参考音色与许可，并能脱离主项目准备与导出。

## Impact

影响共享配音引擎（`src/m2v/engine/tts.py` 及模板/作品 `film_runtime` 镜像）、新增 `qwen3_tts.py`、CLI 后端与音色查询、准备流程、缓存键、模板可选依赖、作品模型恢复、Skill 参考文档与测试。不改变分镜结构、画面渲染、字幕几何或评审格式。验证覆盖后端校验、参考音色摘要、确定性、强制对齐与零时长修复、缓存隔离、模型恢复，以及新作品完整准备、渲染、QA 与独立终审。
