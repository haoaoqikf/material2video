## MODIFIED Requirements

### Requirement: 适用口播作品的固定默认音色
五类作品有自身旁白且需要选音时，制作助手 MUST 默认采用 Qwen3-TTS「真人播客女」`clone_screenrecorder-20261114-174828`。制作助手 MUST 使用同一音色的已登记档案，在作品内登记参考音频、参考文本、来源与授权等必需信息，并显式填写作品后端和音色。用户指定的配音优先，修订已有作品时沿用有效显式选择。

#### Scenario: 适用口播新作未指定音色
- **WHEN** text-motion、data-evolution、principle-metaphor、spatial-3d 或 documentary-edit 作品有自身旁白且需要选音，用户未指定其他配音
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
