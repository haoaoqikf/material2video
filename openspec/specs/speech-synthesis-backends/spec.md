# speech-synthesis-backends Specification

## Purpose
使作品可以在联网的 edge-tts、本地 Kokoro 中文配音或本地 Qwen3-TTS 声音克隆之间选择，并保证音色、参考音色、语速、时间戳、可复现合成、缓存隔离、模型恢复与不受支持输入的失败行为可验证、可追溯。

## Requirements

### Requirement: 作品可声明合成后端

作品 MAY 在 `project.json` 的 `tts.backend` 声明 `edge-tts`、`kokoro` 或 `qwen3-tts`。有自身旁白的 `documentary-edit` 作品省略后端时 MUST 使用 `kokoro`，其他类型省略时 MUST 使用 `edge-tts`。音色 MUST 符合所选后端的格式：edge-tts 为 `zh-CN-XxxNeural`，Kokoro 为 `z[fm]_NNN`，Qwen3-TTS 为 `clone_<slug>`。命令行 `--backend` MUST 覆盖作品声明，优先级为「命令行 > 作品配置 > 默认」。后端与音色不匹配、未知后端 MUST 在合成前失败并列出可用后端；无自身旁白的作品 MUST 不因后端或音色缺失失败。

#### Scenario: 纪实口播默认使用 Kokoro
- **WHEN** `documentary-edit` 作品有自身旁白，配置了合适的 Kokoro 音色且省略后端
- **THEN** 准备记录使用 Kokoro 与所选音色，合成前校验本地模型

#### Scenario: 后端与音色匹配
- **WHEN** 作品声明 `backend=qwen3-tts`、`voice=clone_tuixiu` 并执行准备
- **THEN** 使用 Qwen3-TTS 克隆音色合成，并在准备记录中保存实际后端与音色

#### Scenario: 后端与音色不匹配
- **WHEN** 作品声明 `backend=qwen3-tts` 却写 `zf_027` 或 edge-tts 风格音色，或反向组合
- **THEN** 在发起合成前失败，指出音色格式与后端不一致

### Requirement: Kokoro 合成绑定固定模型并可离线恢复

Kokoro 后端 MUST 固定模型仓库与 revision，使用 `Kokoro-82M-v1.1-zh` 的中文音色。模型、config 与所选音色 MUST 通过作品内 `models/registry.json` 登记的大小与 SHA256 校验；缺失、摘要不符或越界 MUST 失败，不覆盖已有文件。恢复 MUST 由作品内入口完成并支持离线缓存与 `HF_ENDPOINT` 镜像；恢复完成后 MUST 可在断网下重复合成。模型权重 MUST NOT 进入 Git。

#### Scenario: 模型缺失
- **WHEN** `models/files/` 中没有模型或所选音色
- **THEN** 准备失败并给出运行作品内恢复命令的提示，不自动联网下载

#### Scenario: 摘要不符
- **WHEN** 已存在的模型文件大小或 SHA256 与登记不符
- **THEN** 恢复与准备失败，保留原文件并报告不符项

### Requirement: 合成可复现且时间戳来自合成结果

edge-tts 与 Kokoro 的词边界 MUST 来自合成服务或模型自身的时间信息；Qwen3-TTS 的词边界 MUST 来自对生成音频与 narration 原文的按原文强制对齐。任何后端 MUST NOT 按字符比例估算字幕时间。词边界 MUST 单调、非负、落在音频时长内，并覆盖完整口播；不满足时 MUST 失败，不生成字幕或时间轴。时间戳 MUST 进入现有字幕断句与停顿整形，不建立第二套字幕路径。

Qwen3-TTS MUST 在每次合成前按文本、音色、参考音频摘要与语速派生固定种子；同版本环境下重复合成的 PCM 音频 MUST 逐位一致。强制对齐 MUST 在变速后的最终音频上执行；零时长词边界只允许做文本保序合并，不得改动或估算时间值。

#### Scenario: 重复合成
- **WHEN** 同一文本、音色、参考音频与语速在同一环境重新合成
- **THEN** PCM 音频摘要一致，缓存未命中也不会得到不同波形

#### Scenario: 时间戳非法
- **WHEN** 时间戳倒退、超出音频或未覆盖原文
- **THEN** 准备在写入时间轴前失败

### Requirement: 后端参与缓存与溯源

语音缓存键 MUST 包含后端标识、模型 revision、后端依赖版本与生成器版本；Qwen3-TTS 还必须包含对齐模型 revision 与参考音色档案摘要。切换后端、模型、对齐模型、参考音频或参考文本 MUST NOT 命中另一后端的缓存。准备记录、`inputs.tts` 与成片溯源 MUST 保存实际后端、音色、语速、来源及有效选择记录。后端或音色变化 MUST 使旧准备与预演失效，要求重新准备。

#### Scenario: 切换后端
- **WHEN** 同一作品从 Kokoro 改为 Qwen3-TTS 后重新准备
- **THEN** 生成新的语音缓存与准备指纹，旧预演不能授权新导出

#### Scenario: 更换参考音频
- **WHEN** 同一 `clone_<slug>` 音色档案的参考音频摘要改变
- **THEN** 缓存键与准备指纹改变，必须重新合成

### Requirement: 无法映射的口播在合成前失败

Kokoro 当前时间戳路径 MUST NOT 接受数字或拉丁字母。Qwen3-TTS 当前实现同样 MUST NOT 接受数字或拉丁字母：中文对齐可能改写数字或无法稳定映射回原文。此类旁白 MUST 在合成前失败并提示改写为口语中文或改用 `edge-tts`，不得跳过时间戳或估算字幕。纯中文标点与空白 MUST 正常处理。

#### Scenario: 旁白含数字
- **WHEN** Qwen3-TTS 作品的旁白含阿拉伯数字或拉丁字母
- **THEN** 准备失败并指出具体段落与替代办法

### Requirement: Qwen3-TTS 声音克隆绑定参考音频与固定模型

Qwen3-TTS 后端 MUST 使用作品内 `models/qwen3-tts/registry.json` 登记的声音档案、主模型、speech tokenizer 与对齐模型。声音档案 MUST 包含 `voice`、`refAudio`、`refText`、`language`、`sha256`、`bytes`，并记录来源与用户明确要求的授权说明。主模型与对齐模型 MUST 固定仓库、revision 与每个文件的大小和 SHA256；缺失、摘要不符或路径越界 MUST 在合成前失败，不自动联网下载，不覆盖已有文件。模型二进制 MUST NOT 进入 Git。恢复 MUST 由作品内 `models/qwen3-tts/fetch.py` 完成，支持离线缓存、ModelScope 与 `HF_ENDPOINT` 镜像，并能在断网下重复合成。

#### Scenario: 模型缺失
- **WHEN** `models/files/` 中没有 Qwen3-TTS 主模型、speech tokenizer 或对齐模型
- **THEN** validate 与 prepare 失败，并给出运行 `python models/qwen3-tts/fetch.py --download --voice clone_<slug>` 的提示

#### Scenario: 参考音频缺失或摘要不符
- **WHEN** 声音档案声明的参考音频不存在，或实际 SHA256 与登记不符
- **THEN** 准备在发起合成前失败，不生成音频

### Requirement: 参考音色使用必须留证

使用参考视频音色时，声音档案 MUST 记录来源平台、作品 ID、作者、参考音频摘要，以及用户明确要求复用该音色的原文。用户授权 MUST 只作为使用依据，MUST NOT 表述为原作者许可。参考音频 MUST NOT 进入成片画面或音床，MUST 只用于本作品的语音合成音色参考。

#### Scenario: 缺少用户授权说明
- **WHEN** 声音档案没有用户明确要求使用该参考音色的原文
- **THEN** 后端校验失败，不进行声音克隆

### Requirement: Qwen3-TTS 时间戳来自按原文强制对齐

Qwen3-TTS 合成 MUST 在变速后的最终音频上，使用固定版本的对齐模型与 narration 原文执行按原文强制对齐。对齐结果 MUST 按原文顺序覆盖完整口播，每个 token MUST 是原文的连续子串。零时长 token MAY 做文本保序合并：无标点 token 并入下一个有时长 token，带标点 token 并入前一个 token，末词并入前一个 token；合并 MUST NOT 改变任何时间值，也不得新增按字符比例推导的时间。最终词边界 MUST 通过现有 `cues_from_words` 的单调性、覆盖与标点校验。

#### Scenario: 对齐结果含零时长 token
- **WHEN** 强制对齐对个别字符返回相同起止时间
- **THEN** 按文本保序合并后再进入字幕断句，字幕文本与原文一致且时间单调

#### Scenario: 对齐失败
- **WHEN** 对齐模型未返回结果，或 token 与原文顺序不匹配
- **THEN** 准备失败，不写入部分时间轴
