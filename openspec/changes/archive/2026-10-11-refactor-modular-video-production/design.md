## Context

现有 Python 实现在 Skill scripts/a2v；金融与文章有独立入口及输出流程。前端已有两个 composition，文章 v4 使用稳定 world 和全局时间轴。三个示例固定，作品和媒体不入库。动机见 proposal.md。

## Goals / Non-Goals

目标：底座无类型业务依赖；金融和文章完整迁移；通用多场景组合；统一显式入口、准备与评审版本绑定；完成真实渲染和性能验证。
不建设在线数据/模型服务、动态插件、云任务、自动发布、复杂转场、嵌入片段裁切或变速。

## Decisions

1. 标准 src/a2v 包：core 管理作品、类型协议和记录；engine 管理打包、会话、媒体；types 管理文章、金融和 general；cli 做注册与分派。组合根可导入类型，core/engine 禁止导入 types。既有底层模块按实际依赖迁移，类型独占的代码放进类型目录。
2. project.json v1：id、type、schemaVersion、materials（命名相对路径）、output（width、height、fps、audio）。材料相对作品根解析；拒绝版本未知、缺失、越界引用。嵌入作品引用可指向内容根中另一个 project，递归加载带访问栈，拒绝循环。
3. PreparedVideo 执行契约 v1：compositionId、props、width/height/fps/durationInFrames、inputs/asset 指纹、音轨和字幕、依赖项目；保存至 outputs/prepared.json。准备产物参与记录绑定但不是可编辑源；render 只读并复核。
4. 统一记录保存 preview-record.json 和 review.json；完整预演绑定输入与准备指纹及视频摘要。评审模板保持 pending，结论需要具体证据和评审来源。类型门禁单独检查，嵌入项目必须通过自身正式门禁。
5. general-plan.json v1 使用 scenes：id、type、duration（frames 或 narration）、data/material project、narration、transition。全片帧数为场景帧数总和减交叉淡化重叠。默认硬切；淡化默认12帧，相邻淡化不能导致三场景重叠。固定时长口播溢出失败，父级口播不能覆盖嵌入片段口播。
6. Remotion General composition 使用同一编译时间轴，Sequence 提供局部帧，透明度/音量共享淡化函数；字幕映射全片帧。graphic 使用受控原语；代码沿用源码白名单、种子随机与探针。嵌入文章代码模块递归纳入静态清单，按父级场景 ID 生成隔离别名，并绑定准备和打包缓存指纹。公开 API 增加 GeneralSceneProps，保留文章上下文。
7. 所有类型经同一共享渲染器：准备清单、生成锁、完整缓存键、一次浏览器会话、元数据确认、临时输出验收、原子替换、指纹复核、性能与溯源。文章媒体复用现有 TTS/本地混音，不复制声音实现。
8. 保留仓库名和 Skill 位置，移除生产旧命令。制作流程所需文章审查、关键样片、基准等操作通过新 CLI 子命令提供，维护工具可迁入包的工具模块。

## Risks / Trade-offs

- 模块迁移使路径/源码扫描/字体定位失效 → 以仓库标记定位共享资产，测试包安装与外部内容根。
- 评审被迁移或嵌入绕过 → 旧记录归档，重新准备预演评审；递归执行嵌入类型门禁。
- 构建共享清单串扰 → 生成和打包同锁，缓存键包含所有项目代码模块。
- 重构性能回归 → 同机三轮中位耗时与峰值内存比基线增幅不超过10%，记录冷/热缓存。

## Migration Plan

先记录测试及真实关键帧基线，逐阶段迁移包/底座、金融、文章、通用编排，最后替换文档和删除旧入口。migrate 校验旧材料，创建不覆盖的完整备份，再写 project；失败保留原材料且不发布 project。v1-v3 文章拒绝；历史金融先使用已有显式迁移。三个示例就地添加 project，生成记录放 ignored outputs。验证每阶段后提交，完成后同步规格并归档。
