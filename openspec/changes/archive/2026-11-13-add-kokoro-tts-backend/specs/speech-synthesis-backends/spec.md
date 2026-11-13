## ADDED Requirements

### Requirement: 作品可声明合成后端

作品 MAY 在 `project.json` 的 `tts.backend` 声明 `edge-tts` 或 `kokoro`；省略 MUST 使用 `edge-tts`。音色 MUST 符合所选后端的格式：edge-tts 为 `zh-CN-XxxNeural`，Kokoro 为 `z[fm]_NNN`。命令行 `--backend` MUST 覆盖作品声明，优先级为「命令行 > 作品配置 > 默认」。后端与音色不匹配、未知后端 MUST 在合成前失败并列出可用后端；无自身旁白的作品 MUST 不因后端或音色缺失失败。

#### Scenario: 后端与音色匹配
- **WHEN** 作品声明 `backend=kokoro`、`voice=zf_027` 并执行准备
- **THEN** 使用 Kokoro 合成并在准备记录中保存实际后端与音色

#### Scenario: 后端与音色不匹配
- **WHEN** 作品声明 `backend=kokoro` 却写 edge-tts 风格音色，或反向组合
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

Kokoro 合成 MUST 在每次请求前按文本、音色、语速派生固定种子，使同版本环境下重复合成的音频逐位一致。字幕词边界 MUST 来自模型时长预测与文本 token，不得按字符比例估算。词边界 MUST 单调、非负、落在音频时长内，并覆盖完整口播；不满足时 MUST 失败，不生成字幕或时间轴。时间戳 MUST 进入现有字幕断句与停顿整形，不建立第二套字幕路径。

#### Scenario: 重复合成
- **WHEN** 同一文本、音色与语速在同一环境重新合成
- **THEN** PCM 音频摘要一致，缓存未命中也不会得到不同波形

#### Scenario: 时间戳非法
- **WHEN** 时间戳倒退、超出音频或未覆盖原文
- **THEN** 准备在写入时间轴前失败

### Requirement: 后端参与缓存与溯源

语音缓存键 MUST 包含后端、模型 revision、Kokoro/misaki/torch 版本与生成器版本；切换后端 MUST NOT 命中另一后端的缓存。准备记录、`inputs.tts` 与成片溯源 MUST 保存实际后端、音色、语速、来源及有效选择记录。后端或音色变化 MUST 使旧准备与预演失效，要求重新准备。

#### Scenario: 切换后端
- **WHEN** 同一作品从 edge-tts 改为 Kokoro 后重新准备
- **THEN** 生成新的语音缓存与准备指纹，旧预演不能授权新导出

### Requirement: 无法映射的口播在合成前失败

当前 Kokoro 时间戳路径 MUST NOT 接受数字或拉丁字母：数字会被改写、拉丁文本没有词 token，均无法把时间戳映射回原文。此类旁白 MUST 在合成前失败并提示改写为口语中文或改用 `edge-tts`，不得跳过时间戳或估算字幕。纯中文标点与空白 MUST 正常处理。

#### Scenario: 旁白含数字
- **WHEN** Kokoro 作品的旁白含阿拉伯数字
- **THEN** 准备失败并指出具体段落与替代办法
