# 验证记录

## 当前状态

| 项目 | 命令或材料 | 结果 |
|---|---|---|
| 材料校验 | `uv run m2v validate --project styles/dark-proof/examples/sample` | 通过 |
| 准备 | `uv run m2v prepare --project styles/dark-proof/examples/sample` | 通过 |
| 风格注册 | `uv run m2v styles --json` | 返回 6 个包，含 `dark-proof` |
| 代表帧 | `lookdev --sheet 6 13 20 24 28 35 43 51 57.9` | 已核对八拍起点；58 秒被拒，末年帧用 57.9 秒 |
| 唯一硬切 | `lookdev --motion 19.5 20.5` | 通过：19.97 秒仍是四列，20.03 秒为三点空场 |
| 同帧确定性 | `lookdev --det` | 通过：8 个采样帧两次采集均一致（psnr 为 null） |
| 声音生成 | 两次 `generate_all` 与 `recipe.json` 摘要 | 通过：两次生成字节一致，9 项摘要全部匹配 |
| 分镜机械规则 | `uv run pytest tests/types/general/test_storyboard_copy.py` | 通过：中英双语字幕已按规则去掉英文半角逗号/问号 |
| 完整渲染 | `uv run m2v render --project ...` | 通过：58 秒 / 1740 帧 / 1920×1080 / 30 fps |
| 技术 QA | `uv run m2v qa --project ...` | 通过：frozenFrames、picture、subtitleContrast、loudness、audioSync、claims |
| 响度 | `m2v qa` 输出 | −13.6 LUFS / 真峰值 −3.1 dBFS（目标 −14 ±2 LU，真峰值 ≤ −1） |
| 音画时长 | `m2v qa` 输出 | 视频 58.000 秒，音频 58.003 秒，差 3.45 ms |
| 字幕安全区 | 屏幕字幕组件只使用 `subtitleSafeArea` | 通过（代码检查与合同量测规则） |
| 参考风格材料 | `outputs/style-reference.md`、三张并排图、2 秒样片、冷审记录 | 材料齐全；冷审结论见 `outputs/visual-notes.md` |

## 已知限制

- `lookdev --sheet 58` 会被拒（成片时长 0–57.967 秒）；末尾代表帧使用 57.9 秒。
- 代表帧按八拍起点取；拍内中段的并排基准另见 `outputs/style-reference/`。
- 方法说明是右下角小字（22/20 px）；393 宽下作为次级信息，主体数字与中文结论仍可辨。
- 收尾静止约 1 秒，`frozenFrames` 报 3 对重复采样；这是片名停留，不是冻结缺陷。
- 本记录只证明技术链路和画面核对，不替代独立评审与观众理解观察。
