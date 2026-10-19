## Context
通用素材入口当前默认 Pexels，共享图库层已有 Pixabay 适配器。
## Goals / Non-Goals
固定启用 Pixabay；不动态按环境切换，不修改公开直链导入。
## Decisions
在 general 的 gallery_config 集中拒绝 Pexels 和未知来源，默认来源在同模块定义并供函数与 CLI 共用。共享图库适配器不作为制作入口，不扩大本次修改范围。
## Risks / Trade-offs
显式 Pexels 请求将失败；提示改用 Pixabay。缺少 Pixabay 密钥仍明确报错，不回退 Pexels。
## Migration Plan
无需材料迁移；更新命令帮助与制作文档。
