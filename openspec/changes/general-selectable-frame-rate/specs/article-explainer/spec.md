## MODIFIED Requirements

### Requirement: v8 横竖屏代码分镜
系统 MUST 只接受 version/schemaVersion 均为 8 的 general 分镜，默认30 fps、支持显式60 fps，支持 1920×1080 横屏与 1080×1920 竖屏；width/height 均省略 MUST 默认横屏，半指定、非整数及其他尺寸 MUST 拒绝。全片 MUST 使用同一画幅，不自动裁切或重新排版。每幕 MUST 声明唯一 ID、template: code、本地 content.entry、可选 title/JSON 对象 props 及旁白数组；title 只作元数据。场景及旁白 ID MUST 全片唯一。原文输入 MUST 绑定非空源文并审查，主题输入 MUST 声明非空主题与逐幕关键词且不要求原文审查。代码幕 MUST 允许无旁白，未知字段及旧准备 MUST 拒绝。

每幕 MAY 声明 `leadInFrames`、`tailFrames`（0–30秒，按作品fps换算帧数）与 `readingHoldFrames`（0–6秒，按作品fps换算帧数）；旁白段 MAY 声明 `claims` 字符串数组与 `holdFrames`（0–30秒，按作品fps换算帧数，本段结束后、下一段前的静默，最后一段不得非零）；`content.props` MAY 声明 `shots` 与 `look` 对象。未声明时 MUST 保持当前时间轴、阅读停留与画面行为。字段类型、范围或时间窗非法时 MUST 拒绝并定位到具体幕、镜头或旁白段。镜头时间窗 MUST 落在所属幕内且不得重叠；`tier` 只能是 hero、major 或 minor；hero 镜头数量和时长 MUST 按内容决定，不设固定配额。

真正的一镜到底 MUST 写成单幕内多个首尾相接的镜头：所有镜头窗口 MUST 从 0 起严格相接并覆盖整幕，相邻镜头路径的末点与首点 MUST 完全相同，MUST NOT 声明 `cut: true`，全部镜头 MUST 使用 linear 缓动。`post` 参数 SHOULD 在全部镜头间保持一致，因为后期不在镜头边界混合。

#### Scenario: 默认或显式帧率
- **WHEN** 通用分镜省略帧率或声明整数30/60 fps
- **THEN** 缺省按30 fps准备；旁白、字幕、停留、转场和600秒上限按所选帧率保持原秒数

#### Scenario: 帧数字段不随帧率自动缩放
- **WHEN** 作者在不同fps下复用durationFrames、留白、停留或镜头帧数字段
- **THEN** 系统按声明帧数原值解释，超出新帧率范围则拒绝，不自动改写

#### Scenario: 默认与显式尺寸
- **WHEN** 尺寸均省略、显式横屏或显式竖屏
- **THEN** 分别按 1920×1080、1920×1080、1080×1920 规范化并贯穿制作

#### Scenario: 非法尺寸
- **WHEN** 只提供一边尺寸，或尺寸为布尔值、字符串、方屏或其他组合
- **THEN** 校验拒绝并定位字段

#### Scenario: 旧分镜
- **WHEN** 输入 v7 或更早分镜
- **THEN** 要求重新编排 v8，不自动迁移

#### Scenario: 主题输入
- **WHEN** topic 作品的代码幕旁白为空且声明有效关键词与 durationFrames
- **THEN** 按声明长度准备镜头，不要求原文审查；缺少关键词则拒绝

#### Scenario: 非法绑定
- **WHEN** 旧展示元素尝试用 segmentId 绑定旁白
- **THEN** 按未知字段拒绝；v8 代码改用实际 segmentWindows

#### Scenario: 代码模板
- **WHEN** 输入有效 code 场景
- **THEN** 本地录制片段参与统一音轨、字幕和转场合成

#### Scenario: 静音前后段
- **WHEN** 某幕声明有效的 leadInFrames 或 tailFrames
- **THEN** 旁白前后出现对应静音，时间轴与字幕整体后移，不截断或重叠旁白；未声明时行为与当前一致

#### Scenario: 非法电影字段
- **WHEN** shots 的时间窗越界或重叠、tier 非法，或 look/claims 字段类型错误
- **THEN** 校验拒绝并指出具体幕、镜头或旁白段
