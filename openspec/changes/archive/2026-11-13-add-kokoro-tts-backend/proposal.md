## Why

现有配音只有联网的 edge-tts，音色、停顿和波形受远端服务影响，无法固定到本机可复现的声音。Kokoro v1.1-zh 可以在本地合成中文，且模型的时长预测输出可以直接给出词级时间戳；实测可复用现有字幕断句与停顿整形，不需要再引入强制对齐模型。用户已指定用 `zf_027` 重制 `videos/documentary-edit/stop-living-for-others`。

## What Changes

- 新增共享 TTS 后端 `kokoro`（Kokoro-82M-v1.1-zh）：作品在 `project.json` 的 `tts.backend` 声明，音色使用 `zf_027` 这类中国音色名，`tts.rate` 映射为模型 `speed`。edge-tts 仍是默认后端，既有作品不受影响。
- 合成前按文本、音色、语速派生固定随机种子；同版本环境下重复合成逐位一致。时间戳来自模型自身的 `pred_dur` 与中文前端 token，沿用 `cues_from_words` 与现有停顿整形，不建立第二套字幕或节奏路径。
- 语音缓存键纳入后端、模型 revision 与 Kokoro/misaki/torch 版本；准备记录与成片溯源保存实际后端。
- 模型权重不进入 Git：作品内新增 `models/registry.json` 与 `models/fetch.py`，按固定 revision/摘要恢复并校验；缺失时准备失败并给出恢复命令。
- Kokoro 依赖作为作品可选依赖安装；模板和主项目的依赖声明同步，非 Kokoro 作品不承担 torch 体积。
- 当前实现只接受纯中文旁白：数字与拉丁字母会使时间戳 token 无法映射回原文，必须在合成前明确失败，不估算字幕时间。
- 用 `zf_027`、`+20%` 重制 `stop-living-for-others`，重新准备、导出、QA 与独立终审。

## Capabilities

### New Capabilities

- `speech-synthesis-backends`：后端选择、Kokoro 本地合成、确定性、时间戳、缓存与模型恢复的可验证契约。

### Modified Capabilities

- `assistant-voice-selection`：音色选择与实际参数追溯扩展到多后端，音色格式和查询按后端区分。
- `standalone-video-projects`：使用本地 TTS 的作品必须声明依赖并能在自身工程内恢复模型与完成准备。

## Impact

影响共享配音引擎（`src/m2v/engine/tts.py` 及模板/作品 `film_runtime` 镜像）、准备流程与 CLI、作品配置与缓存键、模板依赖与模型恢复、Skill 参考文档和测试；不改变分镜结构、画面渲染、字幕几何或评审格式。验证覆盖后端校验、确定性、时间戳、缓存隔离、脱库恢复，以及本片完整重制与技术/视觉复核。
