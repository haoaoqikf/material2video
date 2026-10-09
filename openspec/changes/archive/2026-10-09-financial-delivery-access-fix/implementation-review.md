# 实施审查与验收记录

本文件记录 `financial-delivery-access-fix` 的修复、测试与重新交付结果（对应任务 2.1）。
现象：用户双击本次交付的 `videos/nvidia-since-ipo/outputs/financial-line.mp4`，Windows 11 媒体播放器报
`0x80070005 你没有访问该文件的权限`。

## 缺陷定位

交付文件的实际 ACL 只有 `SYSTEM / Administrators / OWNER RIGHTS` 三项，缺少仓库内其他文件都有的
`BUILTIN\Users: 读取` 与 `Authenticated Users: 修改`。这正是 `a2v/security.py` 文档已记录的陷阱：
`tempfile.TemporaryDirectory()` 在 Windows 上创建刻意收紧且关闭继承的目录，产物在该目录内生成后
`replace()` 到最终位置，会把这份 ACL 一并带走，于是「自己的管理员账号能读、以标准权限运行的打包播放器不能读」。

`_grant_access()`（内部 `icacls /reset`）本意就是修复它，但金融链路有两处使其失效：

1. **时机**：它在 `temp_video` 上调用，而文件当时仍在收紧的临时目录里。`icacls /reset` 的语义是继承
   **所在目录**的权限，此时只是把那份限制性 ACL 再套一遍；紧随其后的 `os.replace` 把它搬到 `outputs/`，
   就再没有第二次修复。该调用因此等同于空转，日志也不会报错。
2. **覆盖**：`if not preview:` 把修复挡在预演之外，而预演同样登记在 `preview-record.json` 里供人打开复核。

对照旁证：文章流程的 `compound-interest-leverage` 系列 mp4 权限正常，缺陷只在金融专题这条路径。

## 修复

`a2v/financial_render.py`：把 `render_engine._grant_access(destination)` 移到 `os.replace` 之后、
`with` 块收尾处，成片与预演共用一条修复路径，并加注释说明必须在搬运之后执行。

回归测试 `tests/test_financial_video.py::test_delivered_video_gets_inherited_access_after_being_moved`
（参数化成片/预演两条）：桩掉 `security.grant_inherited_access`，断言**只对最终落地的文件**授予一次，
且其父目录为 `outputs/` 或 `outputs/previews/`，从而锁住「搬运之后」与「预演也修复」两个行为。

## 验收结论

| 项目 | 命令 | 结果 |
| --- | --- | --- |
| 新增回归测试 | `uv run pytest tests/test_financial_video.py -k inherited_access` | 2 项通过 |
| Python 测试 | `uv run pytest -q` | 退出码 0，全部通过 |
| 前端类型检查 | `pnpm -C web typecheck` | 通过，无输出 |
| 前端测试 | `pnpm -C web test` | 23 个文件、160 个测试全部通过 |
| 材料校验 | `financial_video.py validate` | 通过，6971 个交易日、60 秒 |
| 重新完整预演 | `financial_video.py preview --project-dir videos/nvidia-since-ipo` | 1800 帧、无音轨、退出码 0，218.8 秒 |
| 重新正式导出 | `financial_video.py render --out outputs/financial-line.mp4` | 1800 帧、60.00 秒、无音轨、退出码 0，235.1 秒 |
| 自动权限修复 | 新导出后直接读取 ACL | 含 `Users`/`Authenticated Users`，**未经人工修复** |
| 可访问性自检 | `security.has_usable_access()` | 成片与预演均为 True |
| 全量审计 | 遍历 `videos/**/*.mp4` | 8 个文件全部可播放，0 个需修复 |

## 门禁联动（按设计工作）

`legibility_review_digest` 把 `a2v/financial_render.py` 等渲染脚本纳入绑定，因此修复该脚本后旧评审立即被判过期
（`材料或渲染资产已变化；评审记录已过期`），首次重新导出被正确阻断。已按流程重新完整预演并重新评审：
`materialsAndAssetsSha256` 由 `d8df4a9c…` 变为 `217c0e89…`。

重新生成的预演 `sha256 = 09f863873ae57eb414cc94b9ea8f9699574e4cbaba2b85f047f2ee4a0efff0f5`，与修改前已逐帧查看过的
预演**逐字节一致**（成片与预演也逐字节一致），证明本次改动不影响画面，因此沿用了既有的 11 个抽检时间码与五项证据，
并在证据中注明该判定依据。

## 剩余风险与已知局限

- 交付访问修复依赖 Windows 自带的 `icacls`；非 Windows 平台 `grant_inherited_access` 直接返回 True，无行为差异。
- 修复失败只记警告、不作废已渲染产物（沿用既有约定）。本机本次未出现失败。
- 既有作品需重新正式导出一次才会获得正确权限；本次已重新导出英伟达成片与预演。
- QA 作品 `videos/full-range-qa-20261009/` 的成片与预演由人工 `icacls /reset` 修复，未重新走渲染链路（属忽略的验证产物）。
