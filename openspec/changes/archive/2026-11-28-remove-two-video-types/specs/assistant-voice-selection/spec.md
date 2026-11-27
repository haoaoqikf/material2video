## MODIFIED Requirements

### Requirement: 实际配音参数可追溯

准备记录与成片溯源 MUST 保存实际后端、音色、语速、来源及有效助手记录；音色格式与可用候选 MUST 按后端校验和查询。三类作品的逐幕停顿声明 MUST 随准备画面参数保存；逐幕 speech.rate 当前不渲染，实际语速取作品或命令行设置。实际参数 MUST 参与准备指纹；修改配置后 MUST 重新准备与完整预演。音色或后端变化 MUST 使用独立的合成缓存。

Qwen3-TTS 的 `tts.voice` MUST 指向作品内登记的声音档案；准备记录与成片溯源 MUST 额外保存参考音频摘要与对齐模型 revision，使音色可追溯到具体参考音频。

#### Scenario: 覆盖与缓存
- **WHEN** 用不同音色或不同后端重新准备并导出
- **THEN** 缓存键改变，准备及溯源记录实际参数，旧预演不能授权新导出

#### Scenario: 按后端查询音色
- **WHEN** 作品声明 `backend=qwen3-tts`
- **THEN** 音色查询只返回作品内 `clone_<slug>` 声音档案，不混用 edge-tts 或 Kokoro 音色名

#### Scenario: 参考音色追溯
- **WHEN** 作品使用 `clone_tuixiu` 准备并导出
- **THEN** 溯源记录可查到参考音频 SHA256、参考文本、语言、对齐模型 revision 与用户授权原文

### Requirement: 适用口播作品的固定默认音色
三类作品有自身旁白且需要选音时，制作助手 MUST 默认采用 Qwen3-TTS「真人播客女」`clone_screenrecorder-20261114-174828`。制作助手 MUST 使用同一音色的已登记档案，在作品内登记参考音频、参考文本、来源与授权等必需信息，并显式填写作品后端和音色。用户指定的配音优先，修订已有作品时沿用有效显式选择。

#### Scenario: 适用口播新作未指定音色
- **WHEN** text-motion、data-evolution 或 spatial-3d 作品有自身旁白且需要选音，用户未指定其他配音
- **THEN** 助手 MUST 核对该音色在作品内的登记，并显式配置 `qwen3-tts` 和该音色 ID。

#### Scenario: 用户指定其他配音
- **WHEN** 用户明确指定另一后端或音色
- **THEN** 助手 MUST 按用户要求及对应后端的配置规则处理。

#### Scenario: 修订已有有声作品
- **WHEN** 修订已有作品且具有有效显式选音，用户未要求换音
- **THEN** 助手 MUST 沿用该选择。

#### Scenario: 没有自身旁白
- **WHEN** 作品没有自身旁白
- **THEN** 助手 MUST 保留该作品的静音或既有音轨安排，固定默认音色无须登记。

#### Scenario: 缺少固定音色档案
- **WHEN** 适用固定默认音色但参考档案或其必要材料缺失
- **THEN** 助手 MUST 报告具体缺项，MUST NOT 自动替换音色。
