## Why

现有内置搜索依赖逐幕 Pixabay 查询，公开页面获取、长视频选段、多模态检索和跨作品复用之间存在断点，难以持续支撑纪录片式口播视频。用户已批准先交付口播指南，再完整实现素材发现、获取、索引、检索、预览、精裁导入和复用；本变更承担第二部分，不将模型能力留为空接口或自动推迟。

## What Changes

- 新增不依赖完整分镜的需求与多来源发现入口，覆盖 Pixabay、Commons、Internet Archive、NASA、yt-dlp 支持的 B站/YouTube 搜索、平台已知链接、网页媒体和显式本地目录。
- 统一受控获取、元数据与字幕、源文件身份、大小/流量/磁盘预算、有限重试、取消及恢复，保留 Pexels API 停用和既有抖音参考用途。
- 实现章节/字幕、faster-whisper 转录、RapidOCR、镜头/关键帧、multilingual E5 文本语义、SigLIP 2 多语言视觉索引，以及词面/语义/视觉混合检索；模型按需安装、显式准备并真实验证。
- 提供带源时间关系的候选接触表、短预览、静态 HTML、选择清单、精裁、现有 import 清单和作品内获取凭据；未知源映射如实保留，不把请求起点冒充实测起点。
- 增加本地 SQLite 工作库、不可变内容对象、增量索引、按摘要复用及引用保护清理；不增加云平台、常驻向量服务或自动发布。
- 扩展 `m2v author assets` 的 discover/fetch/index/find/preview/select/library/models/doctor 工作流；保留现有 search/import 职责，不改变 project v3、分镜 v9、正式媒体登记 schema、离线运行和既有成片评审门禁。

## Capabilities

### New Capabilities

- `material-acquisition`：需求、来源发现、受控网络/平台/本地获取、身份与时间映射、资源预算及失败诊断。
- `material-index-retrieval`：字幕/转录/OCR/镜头/多模态索引、模型恢复、中文检索、混合召回、版本化缓存及可观察依据。
- `material-selection-library`：候选预览、选择与精裁、作品内暂存和现有导入衔接、来源凭据、本地库复用与安全清理。

### Modified Capabilities

- `material-sourcing`：增加完整素材工作层的操作指导和能力边界，保持既有来源政策、记录分工、阶段和审核职责。

## Impact

主要新增 `src/m2v/materials/`，接入现有 author/assets 薄路由，并复用图库、参考获取、FFmpeg 检查、媒体导入和作品锁。依赖通过可选 extras 引入转录、OCR、文本与视觉模型工具，登记精确版本、模型 revision、摘要和许可证；权重、候选与真实媒体不入库。同步 README、架构、项目规划、Skill 素材指南与直接受影响测试。

第一部分口播指南已独立提交为 `2eb76e67`。本变更不挪用 `skip-trial-samples-for-short-videos`，不新增第六部视频示例，不实现绕过验证码/DRM/付费权限、去水印或全网镜像；平台支持仅按实际测试范围披露。实现与归档须完成针对性测试、真实检索及模型推理、独立代码审查，不以接口空壳或 mock 测试代替交付。
