## MODIFIED Requirements

### Requirement: 成片带可机检的溯源

渲染成功后 SHALL 落一份与成片同目录的溯源伴随文件，记录：画面入口与分镜路径、
画面实际依赖的本地资源的指纹、帧数、时长、分辨率与帧率、采集格式与渲染时刻。
有声导出 SHALL 一并记录媒体清单的指纹。

源文件位于仓库外（内容根）时，画面入口 SHALL 以工作区相对路径记录，
SHALL NOT 写入绝对路径。

指纹口径 SHALL 与媒体清单的 `sourceFingerprint` 一致（同一套哈希与字段命名），
SHALL NOT 另造一套。指纹范围 SHALL 限于画面真正依赖的资源，
SHALL NOT 因为未引用资源的变化就判为落后。

画面实现由前端工程构建得到，因此指纹范围 SHALL 覆盖**构建输入**而不是构建产物：
组件源码、共享样式与令牌、字体资产、包清单与锁文件。这样「改了组件源码但没重渲」
会被判为落后——它正是最容易发生、又最不容易被发现的一类落后。

cinematic 导出的溯源 SHALL 额外记录 `profile`、`look`、`shots`、`postFx`、`audio`
与交付文件摘要；profile MUST 为 standard 或 cinematic。look、shots、后期与声音参数
SHALL 与准备指纹使用同一口径；任一参数变化 MUST 让成片被判为落后。standard 溯源 SHOULD
省略 cinematic 专用键，保持与现有格式兼容。

#### Scenario: 渲染成功
- **WHEN** 渲染脚本成功产出成片
- **THEN** 同目录出现溯源伴随文件，字段齐全且指纹可复现

#### Scenario: 未引用资源变化
- **WHEN** 工作区里某个未被该画面引用的资源发生变化
- **THEN** 该成片 SHALL NOT 被判为落后

#### Scenario: 组件源码改了而没重渲
- **WHEN** 共享组件源码、共享样式或锁文件在成片渲染之后发生变化
- **THEN** 判定报出该成片落后，并指名变化的具体文件

#### Scenario: 文章位于仓库外
- **WHEN** 文章与产物位于 `<内容根>/videos|outputs/<slug>/`
- **THEN** 溯源记录工作区相对路径，判定能给出「对得上」而不是「无法判断」

#### Scenario: 电影级溯源
- **WHEN** 以 cinematic 导出成片
- **THEN** 溯源记录 profile、look、shots、postFx、audio 与交付摘要；只改 look 或后期后，旧成片被判为落后

#### Scenario: 标准档溯源兼容
- **WHEN** 以 standard 导出
- **THEN** 溯源保持现有必需字段；缺少 cinematic 专用键不被判为损坏
