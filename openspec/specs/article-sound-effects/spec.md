# article-sound-effects Specification

## Purpose
为统一文章与素材作品提供可重复的提示音和本地音效编排，允许助手将声音选择写进分镜并按真实时间轴与旁白音床混音，保持预演和正式导出一致。

## Requirements

### Requirement: 音效定位与混音

系统 MUST 提供 ding、ding-dong、click、transition 内置提示音以及本地音效；按 sceneId、可选 segmentId、offsetMs 定位并支持 gainDb 及叠加。非法定位、越界起点和不可解码素材 MUST 拒绝；尾部 MUST 裁切至全片，不延长成片。旁白、音床与音效 MUST 合成母版；无旁白作品 MUST 支持音效。

#### Scenario: 叮咚音效
- **WHEN** 分镜在有效幕或旁白段声明 ding-dong
- **THEN** 预演与成片在相同时点播放，配置及声音文件摘要绑定准备指纹

### Requirement: 电影级声音设计与混音

cinematic 作品 MUST 提供完整声音设计：配乐或环境底、与画面事件对应的音效、旁白与音乐的闪避关系，以及成片响度目标。配乐 MUST 来自本地已留证素材或确定性程序化音床；系统 MUST NOT 自动选择第三方曲目，也不依赖联网音乐服务。

cinematic 成片 MUST 沿用现有普通 MP4 音频链路（44.1kHz 立体声 AAC）；对白 MUST 约 −16 LUFS，音乐 MUST 在旁白下压低约 18–24dB，音效 MUST 约 −24dB；成片 MUST 约 −14 LUFS 且真峰值不超过 −1 dBTP。旁白、音床与音效 MUST 合成一条整片音轨，并严格裁到全片时长；`soundtrack.effects` MUST 实际渲染并进入成片音轨，MUST NOT 只在配置里存在而不发声。

standard 作品 MUST 保持现有 44.1kHz/立体声/128k AAC 交付与可选音床/音效行为，不因 cinematic 参数改变。cinematic MUST NOT 另出 48kHz/24bit 母版或 320kbps 专用音轨；成片的响度、真峰值与时长 MUST 写入溯源。

#### Scenario: 电影级混音
- **WHEN** cinematic 作品声明配乐、环境音与音效
- **THEN** 成片中三者按闪避关系混合，旁白清晰、音乐在讲话时压低，音效按画面时点出现，最终约 −14 LUFS / −1 dBTP

#### Scenario: 音效实际发声
- **WHEN** 分镜声明 `soundtrack.effects`
- **THEN** 预演与成片在对应时点听到该音效；不能只校验配置存在

#### Scenario: 标准档音频不变
- **WHEN** standard 作品未选择 cinematic
- **THEN** 音频仍按现有 44.1kHz/128k 交付，音效与音床行为不变

#### Scenario: 程序化音床
- **WHEN** cinematic 作品使用确定性程序化音床
- **THEN** 生成器、种子与许可证记录写入作品来源文件，成片可离线复现
