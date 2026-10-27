# 字体清单与许可

字体二进制**不在这个目录、也不在 Git**。来源、版本、摘要与恢复目标见仓库根
[`fonts/registry.json`](../../../fonts/registry.json)，恢复命令：

```powershell
uv run python fonts/fetch.py
```

本目录只保留 `fonts.json`（画面实际注册的字体系列）与许可证原文。

## 文件清单

| 文件 | 作用 |
| --- | --- |
| `fonts.json` | 注册语义清单：家族、文件、字重、用途、许可；源目录指向 `../fonts/files` |
| `OFL-Inter.txt` | Inter 的许可证原文 |
| `OFL-NotoSansSC.txt` | Noto Sans SC 的许可证原文 |

恢复后 `Inter-Variable.ttf` 与 `NotoSansSC-Variable.ttf` 会出现在本目录（已 gitignore），
并与字体仓中的副本摘要一致。

## 使用方式

- 渲染层（`src/fonts.ts`）在运行时用 CSS Font Loading API 注册字体，URL 由 `staticFile()` 解析；
- 构建前 `web/scripts/sync-fonts.mjs` 从 `../fonts/files` 同步到 `public/fonts/`（生成物），
  并核对 `fonts/registry.json` 的字节数与 SHA-256；
- 缺字机检按 `fonts.json` 取字形；字体缺失时构建与检查失败，不会落到系统字体。

## 许可

两套字体均为 **SIL Open Font License 1.1**，许可证原文随字体分发。
OFL 允许随产品分发与再分发字体文件，要求许可证随附、不得单独售卖字体本身、
不得使用保留字体名称（Reserved Font Name）发布修改版。
本项目不对字体文件做修改，只做分发与引用。

## 字体缺失时

运行 `uv run python fonts/fetch.py`。若本机没有网络，先把字体文件放入
`M2V_FONT_CACHE` 指向的目录或 `fonts/.cache/`，脚本会校验摘要后恢复。

字体二进制不入库的完整说明见 [`fonts/README.md`](../../../fonts/README.md)。
