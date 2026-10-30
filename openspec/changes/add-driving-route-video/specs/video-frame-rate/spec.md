## MODIFIED Requirements

### Requirement: 统一视频帧率

系统 MUST 对金融与自驾路线使用固定 60 fps；general MUST 默认30 fps并允许显式整数30或60，贯穿初始化、准备、场景录制、完整预演与正式导出。对于 general，`project.json` 的 `output.fps` 与分镜的 `fps` 均显式时 MUST 一致，仅一处声明时 MUST 使用该值，均缺省时 MUST 使用30。系统 MUST 拒绝类型契约以外的值（包括布尔和小数）、冲突声明及帧率不匹配的准备产物。时间轴 MUST 保持以秒计的旁白、字幕、阅读停留及动画节奏；显式帧数字段按原值解释，不自动缩放。

#### Scenario: 新建通用作品
- **WHEN** 初始化通用作品且未设置帧率
- **THEN** 项目配置和分镜模板写入30 fps，金融与自驾路线仍为60 fps

#### Scenario: 单处帧率声明
- **WHEN** 通用项目或分镜中仅一处声明整数30或60 fps
- **THEN** 准备、录制、预演及导出均采用该帧率

#### Scenario: 冲突或非法帧率
- **WHEN** 两处声明不一致，或帧率是布尔、小数或非30/60整数
- **THEN** 校验失败并指出字段

#### Scenario: 帧率变化
- **WHEN** 已准备作品改变帧率
- **THEN** 原准备及录制缓存失效，需按新帧率重新准备；以秒计的时长和运动速度保持一致

#### Scenario: 固定示例
- **WHEN** 五个随附风格示例完成准备、完整预演及正式导出
- **THEN** `doc-archive` 与 `deep-journey` 示例按其显式声明的60 fps交付，`count-ledger`、`vibe-night/fold` 与 `vibe-fable/pigeon` 按30 fps交付；各示例帧数与准备记录一致，旁白与字幕同步
