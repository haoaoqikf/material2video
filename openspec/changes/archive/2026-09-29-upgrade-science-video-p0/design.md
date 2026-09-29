## Context

见 proposal.md。现有口播整幕缓存、WordBoundary 与 resolvedBeats 是时间真源，声音先编码为统一 WAV 再合入视频。代码场景已有 beats.plan、探针和确定性约束。

## Goals / Non-Goals

Goals：在既有链路上增加可选语音参数、共享对象数学工具和内容评审；完整标杆验收。
Non-Goals：新增场景树原语、外部 TTS、录音导入、自动选曲和新的时钟。

## Decisions

- 分镜保持 v3。speech 含 rate/pauseBeforeMs/pauseAfterMs；soundtrack 使用 sourceRef/gainDb/loop/fadeInMs/fadeOutMs，effects 使用 sceneId/beatId/offsetMs/gainDb。Python 与 TS 同步校验，拒绝远程与越界路径。
- 段级合成逐段缓存，不把停顿放入 TTS 缓存键；先按样本拼接段及停顿，再对词边界和字幕加偏移，独立窗口派生 beats。保留无配置整幕路径以免降低旧作品流畅度。
- 混音通过 ffmpeg 和文件处理完成，旁白二遍 loudnorm；压低包络来自实际字幕区间，应用 80ms/250ms 包络。使用固定默认混音参数，不由音频随机峰值决定画面时间。
- 媒体 v3 保留 audio 为最终混音，新加 narration、soundFingerprint、soundAssets；v1/v2 可读。素材解析相对源分镜，读取清单时验证快照和摘要。
- 动画工具独立模块由 @a2v/scene 导出。SVG 路径用预采样折线查找位置，积分预计算分段常流量并钳制容量；帧查询不回放历史。
- 内容评审作为 full.content，评分与材料来源复用现有评审字段，正式门禁显式要求，旧制作记录可读但需补评审。
- 示例六幕采用固定水箱对象，传输、拆解、积累与溢出由 data 定义。自制音乐及音效记录 CC0 许可。

## Risks / Trade-offs

- 段级 TTS 拼接可能削弱连贯性 → 仅有 speech 的幕拆段，标杆试听调整。
- TTS 联网不稳定 → 离线夹具覆盖逻辑，真实请求缓存，失败不伪造有声验收。
- 混音编码可能增峰 → 输出留余量并量测 AAC 真峰值，必要时降低音轨增益。
- 任意 SVG 曲线采样误差 → 公共 API 接受确定性预采样路径，明确误差与支持范围，不引入 DOM 时钟。

## Migration Plan

旧分镜不改；旧清单按原语义读取，有新声音参数重新 prepare。新制作模板附内容评审，旧记录补齐再发布。全部验证与提交成功后自动同步主规格并归档。

## 实施中发现的契约修正

段级停顿属于 beat，而字幕只覆盖讲话，A4 改为检查文本、顺序和讲话区间包含关系（无 speech 仍使用一帧边界相等判据）。为使标杆有声预演和导出一致，媒体派生 props 增加 subtitleCues，composition 绘制字幕并预留安全区；源分镜拒绝手填。审片帧范围改用媒体派生时长。代码场景跨幕节点映射当前不能静态确认，示例复用 tank 母题并使用既有 dissolve 转场，不伪造可验证继承映射。
