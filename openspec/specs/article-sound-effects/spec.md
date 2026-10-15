# article-sound-effects Specification

## Purpose
为统一文章与素材作品提供可重复的提示音和本地音效编排，允许助手将声音选择写进分镜并按真实时间轴与旁白音床混音，保持预演和正式导出一致。

## Requirements

### Requirement: 音效定位与混音

系统 MUST 提供 ding、ding-dong、click、transition 内置提示音以及本地音效；按 sceneId、可选 segmentId、offsetMs 定位并支持 gainDb 及叠加。非法定位、越界起点和不可解码素材 MUST 拒绝；尾部 MUST 裁切至全片，不延长成片。旁白、音床与音效 MUST 合成母版；无旁白作品 MUST 支持音效。

#### Scenario: 叮咚音效
- **WHEN** 分镜在有效幕或旁白段声明 ding-dong
- **THEN** 预演与成片在相同时点播放，配置及声音文件摘要绑定准备指纹
