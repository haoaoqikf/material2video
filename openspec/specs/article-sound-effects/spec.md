# article-sound-effects Specification

## Purpose
为统一文章与素材作品提供可重复的提示音和本地音效编排，允许助手将声音选择写进分镜并按真实时间轴与旁白音床混音，保持预演和正式导出一致。

## Requirements

### Requirement: 音效定位与混音

系统 MUST 提供 ding、ding-dong、click、transition 内置提示音、本地音效及登记音效 ID；按 sceneId、可选 segmentId、offsetMs 或相对场景 offsetFrames 定位，帧偏移与毫秒偏移 MUST 互斥。系统 MUST 支持 gainDb、素材入点、播放时长、循环、淡入淡出及左右声像。非法定位、越界起点、超出素材范围的入点、缺少时长的循环和不可解码素材 MUST 拒绝；尾部 MUST 裁切至全片，不延长成片。旁白、音床与音效 MUST 合成保留立体声的母版；无旁白作品 MUST 支持音效。

#### Scenario: 叮咚音效
- **WHEN** 分镜在有效幕或旁白段声明 ding-dong
- **THEN** 预演与成片在相同时点播放，配置及声音文件摘要绑定准备指纹

#### Scenario: 动作同步与声像
- **WHEN** 无旁白场景在指定帧声明右侧火花，指定入点、播放时长和淡化
- **THEN** 音效在相应帧播放，右声道强于左声道，声音尾部不延长成片

### Requirement: 电影级声音设计与混音

所有 general MUST 按内容规划声音，可选择旁白、配乐、音效或无声，不强制多层音乐。配乐 MUST 来自本地留证素材或确定性程序化音床，不自动选择第三方曲目。有声成片 MUST 以−14 LUFS和−1 dBTP为技术目标；无声作品 MUST 保持无声，不套用响度目标。已声明音效 MUST 实际混入并按真实时间窗定位，音轨严格裁至全片；保持AAC-LC、44.1kHz立体声128k和普通MP4，不另出母版。溯源 MUST 记录实际音轨与交付信息。

#### Scenario: 电影级混音
- **WHEN** general 作品声明配乐、环境音与音效
- **THEN** 成片中三者按闪避关系混合，旁白清晰、音乐在讲话时压低，音效按画面时点出现，最终约 −14 LUFS / −1 dBTP

#### Scenario: 音效实际发声
- **WHEN** 分镜声明 `soundtrack.effects`
- **THEN** 预演与成片在对应时点听到该音效；不能只校验配置存在

#### Scenario: 标准档音频不变
- **WHEN** general 有声作品未声明旧档位
- **THEN** 使用统一响度目标与现有AAC交付，配乐音效按需选择

#### Scenario: 程序化音床
- **WHEN** general 作品使用确定性程序化音床
- **THEN** 生成器、种子与许可证记录写入作品来源文件，成片可离线复现
