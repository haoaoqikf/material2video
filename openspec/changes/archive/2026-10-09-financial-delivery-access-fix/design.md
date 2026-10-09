## Context
见 proposal.md。金融专题的成片与预演都要经临时目录中转；`a2v/security.py` 已确认这类产物会带走临时目录的收紧 ACL，并提供了 `_icacls /reset` 作为修复手段。缺陷不在缺少手段，而在调用时机与覆盖范围。

## Goals / Non-Goals
目标：交付的成片与预演在 Windows 上可被标准权限进程打开（解决 `0x80070005`），并让该行为有回归测试。非目标：不改动画面、坐标、价格口径、材料形状或评审五项结论；不改变临时目录的使用方式。

## Decisions
- 把 `_grant_access` 从临时文件移到 `os.replace` 之后的最终路径。`icacls /reset` 的语义是「继承所在目录权限」，在临时目录内执行只会继承那份限制性 ACL，因此必须在搬运之后。
- 预演一并修复，去掉 `if not preview` 条件。预演的用途就是人工打开复核，与成片同属交付文件。
- 单一调用点放在 `with` 块之后的收尾处，成片与预演共用一条修复路径，避免两处各自维护。
- 认证依据用既有 `security.has_usable_access()`（解析 `icacls` 授权行，要求存在 `Users` / `Authenticated Users` / `Everyone` 或当前用户的写权限），而不是自行重写判断。

## Risks / Trade-offs
- 权限修复失败不影响已渲染产物：`grant_inherited_access` 只记警告并返回 False，渲染不因此作废（沿用既有约定）。
- 修复会使已绑定的可读性评审失效：`legibility_review_digest` 绑定了 `a2v/financial_render.py` 等渲染脚本，改动脚本即视为渲染资产变化。这是门禁按设计工作；已按流程重新完整预演并重新评审。
- `icacls` 是 Windows 专有命令；非 Windows 平台 `grant_inherited_access` 直接返回 True，无行为差异。

## Migration Plan
无材料迁移。既有作品需重新正式导出一次以获得正确权限；若期间改动了绑定的渲染脚本，须重新完整预演与评审。
