## Why
交付的视频文件缺少授予普通用户的访问条目，用户双击播放时 Windows 11 媒体播放器报 `0x80070005 你没有访问该文件的权限`。

根因已被 `a2v/security.py` 记录过：`tempfile.TemporaryDirectory()` 在 Windows 上创建刻意收紧的 ACL（只有 `SYSTEM / Administrators / OWNER RIGHTS` 且关闭继承），产物在该临时目录里生成再 `replace()` 到最终位置，就会把这份 ACL 一起带走。既有修复手段 `render_engine._grant_access()` 在金融专题这条链路上没有生效。

## What Changes
- 交付文件在**搬运到最终位置之后**才重新继承所在目录权限；此前在临时目录内调用 `icacls /reset` 只会再套一遍那份收紧的 ACL。
- 预演同样修复访问权限：它是登记在 `preview-record.json` 里、供人打开复核的交付文件，此前被 `if not preview` 整体排除。
- 增加可访问性要求与回归测试，文档记录该交付契约。

## Capabilities
### New Capabilities
无。
### Modified Capabilities
- `financial-timeseries-video`：正式导出与预演的交付文件在 Windows 落盘后必须可被标准权限进程打开。

## Impact
金融渲染交付链路（`a2v/financial_render.py`）、制作手册、Python 测试。无新依赖；不改变画面、价格口径或材料形状，作品不入库。
