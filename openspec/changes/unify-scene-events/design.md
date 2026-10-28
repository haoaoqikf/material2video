## Context

general v8 音效支持 sceneId/segmentId 加偏移，TSX 单独维护动画时间。prepare 已深拷贝幕并计算 startFrame，scene_config 已参与录制缓存，源码实现摘要与 storyboard 文件已进入准备指纹。

## Goals / Non-Goals

目标：事件只声明一次，提供纯查询；在 prepare 确定实际幕长后统一解析并供混音、配置和清单复用。
非目标：跨幕事件依赖、回调、自动碰撞检测、字幕重排、新 CLI、新版材料或兼容层。

## Decisions

- 保持 v8，增加可选 scenes[].events。每幕最多 1024 项，同幕唯一、帧为 [0,duration) 整数；不同事件可同帧发生。
- 解析结果为 eventFrames（ID→幕内帧）和清单（sceneId/id/frame/globalFrame）；Python 事件模块拥有校验和音效定位规则。
- scene_config 将 eventFrames 传给 CodeSceneProps；SDK createSceneEvents 提供 frame(id) 和 progress(id,currentFrame,durationFrames,offsetFrames=0)，进度夹在 0–1，duration 为正有限值，零时长状态用 frame 比较。
- eventId 音效只接受帧偏移，不接受 segmentId/offsetMs；偏移后起点须仍在所属幕内。其余音效保持既有行为。混音和清单共用解析出的音效起点，避免两份算法。
- prepare 在合成之前解析所有事件和音效起点，结果保存在 props.resolvedEvents 与 props.effectStartFrames，输出 outputs/events.json 并绑定 preparedFingerprint。
- 源材料摘要、事件配置和事件模块实现均参与指纹，不单独引入缓存系统。
- 复利前十枚圆片落点改用同一事件表，对齐既有音效的整数帧（原连续时间量化误差小于半帧）。其余两固定示例验证无事件路径，不为展示能力加入无意义字段。计数与强调通过真实浏览器测试场景验证，不给复利额外添加画面信息。

## Risks / Trade-offs

- 事件帧不自动随旁白伸缩：实际幕长缩短时明确失败。
- 音效事件帧表示素材播放起点，素材内部静音或慢起音仍需制作复核。
- SDK 只能保证引用后的统一求值，不能证明作者没有另写时间常量；通过示例和独立代码审查验证接线。
- 性能：每次准备 O(事件数+音效数)，运行时查询 O(1)，不逐帧导出或扫描整片。
