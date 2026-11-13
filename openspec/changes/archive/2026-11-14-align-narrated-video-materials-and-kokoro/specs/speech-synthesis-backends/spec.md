## MODIFIED Requirements

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
