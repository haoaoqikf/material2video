## MODIFIED Requirements

### Requirement: 音效定位与混音

系统 MUST 提供 ding、ding-dong、click、transition 内置提示音、本地音效及登记音效 ID；按 sceneId、可选 segmentId、offsetMs 或相对场景 offsetFrames 定位，帧偏移与毫秒偏移 MUST 互斥。系统 MUST 支持 gainDb、素材入点、播放时长、循环、淡入淡出及左右声像。非法定位、越界起点、超出素材范围的入点、缺少时长的循环和不可解码素材 MUST 拒绝；尾部 MUST 裁切至全片，不延长成片。旁白、音床与音效 MUST 合成保留立体声的母版；无旁白作品 MUST 支持音效。

#### Scenario: 叮咚音效
- **WHEN** 分镜在有效幕或旁白段声明 ding-dong
- **THEN** 预演与成片在相同时点播放，配置及声音文件摘要绑定准备指纹

#### Scenario: 动作同步与声像
- **WHEN** 无旁白场景在指定帧声明右侧火花，指定入点、播放时长和淡化
- **THEN** 音效在相应帧播放，右声道强于左声道，声音尾部不延长成片
