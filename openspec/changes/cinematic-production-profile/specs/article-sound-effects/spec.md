## ADDED Requirements

### Requirement: 电影级声音设计与母版

cinematic 作品 MUST 提供完整声音设计：配乐或环境底、与画面事件对应的音效、旁白与音乐的闪避关系，以及母版响度目标。配乐 MUST 来自本地已留证素材或确定性程序化音床；系统 MUST NOT 自动选择第三方曲目，也不依赖联网音乐服务。

cinematic 母版 MUST 使用 48kHz/24bit；对白 MUST 约 −16 LUFS，音乐 MUST 在旁白下压低约 18–24dB，音效 MUST 约 −24dB；母版 MUST 约 −14 LUFS 且真峰值不超过 −1 dBTP。旁白、音床与音效 MUST 合成一条母版轨，并严格裁到全片时长；`soundtrack.effects` MUST 实际渲染并进入母版，MUST NOT 只在配置里存在而不发声。

standard 作品 MUST 保持现有 44.1kHz/立体声/128k AAC 交付与可选音床/音效行为，不因 cinematic 母版参数改变。cinematic 交付 MUST 另提供 48kHz/320kbps AAC 或等价兼容音频；母版与交付的响度、真峰值与时长 MUST 写入溯源。

#### Scenario: 电影级混音
- **WHEN** cinematic 作品声明配乐、环境音与音效
- **THEN** 母版中三者按闪避关系混合，旁白清晰、音乐在讲话时压低，音效按画面时点出现，最终约 −14 LUFS / −1 dBTP

#### Scenario: 音效实际发声
- **WHEN** 分镜声明 `soundtrack.effects`
- **THEN** 预演与成片在对应时点听到该音效；不能只校验配置存在

#### Scenario: 标准档音频不变
- **WHEN** standard 作品未选择 cinematic
- **THEN** 音频仍按现有 44.1kHz/128k 交付，音效与音床行为不变

#### Scenario: 程序化音床
- **WHEN** cinematic 作品使用确定性程序化音床
- **THEN** 生成器、种子与许可证记录写入作品来源文件，母版可离线复现
