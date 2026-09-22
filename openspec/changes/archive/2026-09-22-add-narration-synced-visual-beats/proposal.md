## Why

当前字幕、配音和节点入场虽能稳定渲染，却没有共享“正在解释哪一步推理”的时间语义；复杂观点只能依赖作品代码或一组与口播脱节的入场动画。需要让口播分段、字幕边界、语义动画和声明式图形共用同一时间轴，使画面通过状态与关系变化解释论点。

## What Changes

- 新增语义动画时间轴：分镜可用互斥于旧字符串口播的 `narrationSegments` 绑定 `beats`，媒体准备按真实 WordBoundary 解析逐幕节拍帧区间。
- 媒体清单升级并携带 `resolvedBeats`；有声画面、字幕和配音使用同一边界，无声预览按声明时长等比例解析。
- 新增 `flow`、`cycle`、`timeline`、`gauge`、`pictogram` 五个声明式中层原语，复用现有 ECharts、Dagre、Lucide、SVG 和帧驱动运行时，不增加外部依赖。
- 扩展代码场景共享接口，使其只读当前 beat、局部进度和已完成 beat 集合，不自行解析字幕或挂钟。
- 新增 A1–A8 动画论证评审，并更新文章生成 Skill、分镜/媒体/渲染契约、示例和项目文档。
- 保持 schemaVersion 2、旧 `narration`、旧媒体清单和既有 `motions` 的预览与渲染兼容；新生成的非文字幕在严格验收中必须使用语义节拍。

## Capabilities

### New Capabilities

- `semantic-motion-timeline`: 规定分段口播、语义节拍、媒体解析结果、运行时状态和动画论证评审的端到端契约。

### Modified Capabilities

- `scene-primitive-tree`: 增加五个可组合、确定性的中层视觉原语及其受控属性和节拍状态。
- `frame-driven-motion`: 将语义动作纳入帧纯函数与量测契约，并保证布局冻结和结尾稳定。
- `article-to-storyboard`: 生成流程增加推理拆分、节拍编排、分段口播和字幕同步验收。

## Impact

- 分镜 schema、Python 校验器、TTS 准备和媒体清单版本发生兼容性扩展。
- React composition、场景树解释器、代码场景 props、组件注册表与契约页增加 beat 运行时支持。
- `review.py` 与报告新增 A 系列闸门；现有 C/K/M/V 系列保持独立。
- Skill 参考文档、README、项目计划、注册表生成目录和受版本控制示例需要同步更新。
