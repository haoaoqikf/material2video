## Context

现有字符串口播经 WordBoundary 生成字幕，画面时长可由媒体清单延长；场景树只有节点级入场配方，代码场景只能自行按整幕 progress 编排。系统缺少可被字幕、共享 composition 和评审共同读取的推理阶段。

## Goals / Non-Goals

**Goals:** 建立单一 beat 时间真源；保持随机寻帧确定性；提供五个高复用中层原语；让机检与人工共同判断动画是否解释论点。

**Non-Goals:** 不做背景音乐、逐字高亮、录音导入、在线语义评审，也不在首版提供通用 metaphor/state-machine/allocation 原语。

## Decisions

### 分段口播是新作品真源

新增 `narrationSegments: [{id,text,beatId}]` 与 `beats: [{id,action,targets,meaning}]`；它与字符串 `narration` 互斥，完整 TTS 文本由段落拼接。这样避免保存第二份完整口播，也能稳定引用重复短语。旧格式继续读取，严格规则只约束新生成的非文字幕。

### 媒体清单升级但保持旧版可读

新版清单逐幕保存 `resolvedBeats` 的本地帧区间。prepare 从已恢复原文的 WordBoundary 顺序消费每段文本，再以场景 fps 向外取整为开始包含、结束不包含区间；任何剩余或越界均失败。读取器同时支持旧清单，只有含分段口播的源分镜才要求新版解析结果。

### 一个共享 beat 求值核心

Python 负责验证与媒体解析，TypeScript 提供等价的无声比例解析和逐帧求值。composition 将 `{current, progress, completed, estimated}` 传给场景树和代码场景。中层原语消费这份状态，不读取字幕 DOM 或音频时钟。

### 注册表扩展而非引入整页组件

五个原语仍是场景树节点：flow/cycle/timeline 允许受控子节点并绘制关系，gauge 读取数值与 beat 状态，pictogram 使用本地 Lucide 白名单。注册表继续唯一声明 props、容量与动作；新增图形进入 V 系列结构证据。

### A 系列分离客观与主观判断

A1–A5、A7–A8 从分镜、解析时间轴和 DOM 探针量测；A6 读取 review.md 的评分与依据。A 系列独立于 C/K/M/V 展示，客观失败进入严格评审，主观结论缺失阻止发布但不伪造成脚本错误。

## Risks / Trade-offs

- [TTS 边界与标点恢复存在差异] → 复用现有严格覆盖校验，按段顺序消费且失败不猜测。
- [五个原语一次引入范围较大] → 共用 beat 核心、状态属性和探针协议，逐个原语独立测试。
- [旧媒体缓存不能提供 beats] → 分段口播指纹变化必然触发重新 prepare，旧字符串口播继续复用旧清单。
- [Lucide 全量打包膨胀] → 使用显式图标白名单和静态映射，只打包被登记图标。

## Migration Plan

先落地 schema、校验和 beat 核心，再升级媒体清单与 composition，随后实现五个原语、A 系列、示例和文档。仓库内示例迁移；被忽略的作品继续兼容，修改后需重新 prepare。完成验证与提交后自动归档并同步主规格。
