## Context

动机见 proposal.md。文章已有真实 TTS 时间轴及完整预演门禁，stock 已有图库适配器与本地媒体服务，共享 audio 支持音床和音效混音。

## Goals / Non-Goals

支持统一作品混排与可重复离线制作；互联网搜索由助手执行，不在 CLI 接入搜索引擎，不绕过网站访问控制。

## Decisions

- 仅接受 v6，最长 600 秒；新建使用 v6，默认目标 60 秒。输入 kind=article/topic；topic 不伪造原文审查。
- 资产清单导入后保存实测信息与内容摘要，分镜使用本地 src。远程抓取只在导入发生，prepare/render 不联网取素材。
- 新媒体模板采用作品本地回环服务，不将视频放入共享 public 或 base64。图片保留既有 image 模板并增加可选运动。
- TTS 先量测、再分配无旁白幕的剩余帧；已声明时长不足以容纳旁白时失败。兼容 cut/fade，素材迁移保留 crossfade 重叠帧。
- 音效使用 builtin 或 sourceRef 二选一，sceneId/segmentId/offsetMs 定位，沿用母版混音并裁切全片末尾。
- 删除 stock 独立类型、旧 brief/时间轴/渲染链，复用 provider 层实现 article assets search。

## Risks / Trade-offs

- 全网地址失效或并非媒体 → 限时限量下载，实测后采用，错误按资产定位。
- 未知作者许可 → 明确记为未知，绝不虚构。
- 长片渲染成本 → 资产与实现指纹复用；保留流式音频及本地服务。

## Migration Plan

按用户最新规范，本次彻底重构，不保留兼容与迁移。旧作品须按 v6 重新编排。
