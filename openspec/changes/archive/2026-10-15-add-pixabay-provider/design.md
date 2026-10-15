## Context

现有图库使用可注入 Transport 和统一 Candidate，检索与渲染已解耦。Pixabay 的 Key 放在查询参数中，不能沿用会输出完整 URL 的异常信息。

## Goals / Non-Goals

目标：接入图片、视频并复用现有排序、下载留证和剪辑流程。保留现有 Pexels 默认值，不增加多源混搜或自动回退。

## Decisions

- 按 provider.name 补全 apiBase、apiKeyEnv；明确配置始终优先，旧作品不变。
- 独立 Pixabay 适配器复用传输接口；下载 CDN 文件不携带 API Key。异常仅报告脱敏地址及错误类别，不回显远端响应或异常正文。
- 将 Pixabay 成功检索响应缓存到作品 outputs/stock-cache，按不含凭据的请求参数与凭据摘要生成文件名；缓存不保存请求 URL 或明文 Key，24 小时内命中，损坏及过期重取。缓存写入采用临时文件替换。
- 使用 API 实际返回的图片版本尺寸（largeImageURL 最大边 1280）及视频变体尺寸留证，避免原图尺寸冒充下载尺寸；方向在候选层过滤。

## Risks / Trade-offs

- 外部真实接口未测试 → 注入响应及本地 HTTP 回归；不声称已用真实 Key 验证。
- API 不允许系统性批量下载 → 仅按人工指定作品逐幕检索入选素材，复用缓存；文档说明用途限制。
- 普通图片接口最大边 1280 → 如实记录尺寸，不承诺原图权限。
