# 验证记录

## 规格与注册

- `openspec validate add-three-style-packages-and-migrate-examples --strict`：通过。
- `openspec validate --specs`：41 个主规格通过（变更归档前状态）。
- `uv run m2v styles --json`：返回 `count-ledger`、`deep-journey`、`doc-archive`、`vibe-fable`、`vibe-night` 五个包；`styles/examples/` 不出现在清单中。
- `find styles/examples -name style.json`：无结果，示例目录没有被当作风格包。
- `uv run python .agents/skills/material2video/scripts/sync_docs.py --check`：通过。

## 示例校验与准备

| 示例 | validate | prepare |
|---|---|---|
| `styles/examples/doc-archive/american-science-milestones` | 通过 | 通过 |
| `styles/examples/count-ledger/compound-interest` | 通过 | 通过 |
| `styles/examples/deep-journey/solar-system-journey` | 通过 | 通过 |
| `styles/examples/vibe-night/fold` | 通过 | 既有示例 |
| `styles/examples/vibe-fable/pigeon` | 通过 | 既有示例 |

代表性预览：

- `uv run m2v preview --project styles/examples/doc-archive/american-science-milestones --start-seconds 0 --end-seconds 2`：通过，输出 `outputs/previews/video.mp4`。
- `uv run m2v preview --project styles/examples/count-ledger/compound-interest --start-seconds 0 --end-seconds 2` 与 `--start-seconds 4 --end-seconds 6`：通过。
- `uv run m2v preview --project styles/examples/deep-journey/solar-system-journey --start-seconds 0 --end-seconds 2`：通过。

## 自动化测试

- `uv run pytest -m "not slow" -q -s -p no:cacheprovider`：退出码 0，非 slow 测试通过。
- 相关 slow 测试：`test_solar_system_scene.py`（3）、`test_scene_events.py`（2）、`test_styles.py`（2）、`test_vibe_fable_style.py`（2）、`test_vibe_night_style.py`（3）通过；太阳系场景测试显式传入 `deep-journey` 的 `style-build` 配置。
- `pnpm -C web test`：11 个测试文件、137 个测试通过。
- 定向测试：`test_styles.py`、`test_vibe_night_style.py`、`test_vibe_fable_style.py`、`test_style_examples_strict.py`、`test_doc_examples.py`、`test_storyboard_copy.py`、`test_derived_styles.py` 全部通过。

## 视觉抽查

抽查帧：

- `C:\tmp\m2v-frames\doc-archive.png`（迁移后档案示例开场）
- `C:\tmp\m2v-frames\count-ledger.png`（复利示例 1 秒，落片过程中）
- `C:\tmp\m2v-frames\count-ledger-5s.png`（复利示例第 5 秒，第一枚金片与算式）
- `C:\tmp\m2v-frames\deep-journey.png`（太阳系示例开场俯视）

独立子代理只读抽查结论（未读 DESIGN/指南，仅看帧）：

- 三张图共享近黑底与极简留白，但表面语言可区分：档案图为单色高噪点摄影 + 大白粗体 + 金色细线；复利图为黑底米色圆片 + 金色新生成 + 公式与边界说明；深空图为深蓝星空 + 细线 HUD + 橙/土褐天体。
- 观察到的主要风险：复利示例 1 秒帧处于落片过程，顶部圆片被上边缘裁切且画面无文字，单帧容易被误读为空白；档案开场影像主体不具名；深空示例顶部导航与圆内天体位置没有可见的一一对应。档案黑场偏多、复利单帧信息过空、深空大圆抢焦点属于偏好判断，不作为缺陷。
- 复利第 5 秒帧补充核对：第一枚金片、11 枚圆片柱、`收益再投入 / 第 1 年 / 10,000 × 10% = 1,000` 与底部方法边界均清晰可读，风格组件与作品编排衔接正常。

限制：

- 本次只抽查代表帧，未重放完整成片，不声称全片视觉验收；三个迁移作品的既有 VERIFICATION 记录保留为历史，不授权新路径下的新版本。
- 旧 `examples/` 的 `outputs/` 未迁移，约 17.4G 生成本地产物；其中 `examples/compound-interest/outputs/code-cache/code-ajld19eb` 因权限受限无法删除，作为被忽略的本地残留保留，不影响 Git 跟踪与构建。
- 深空示例迁移后 `article.md` 的字节摘要与旧输入审查记录不一致；已确认迁移前后内容逐字节相同（仅路径/行尾迁移），刷新输入审查的 `source.sha256` 与 `charCount` 后重新 prepare 通过。该刷新是元数据迁移，不是新的语义审查结论。

## 归档

- 实施提交：`0b8d971`。
- `openspec archive add-three-style-packages-and-migrate-examples -y`：主规格 11 处更新（+17 / ~11 / -5），变更移入 `openspec/changes/archive/2026-10-29-add-three-style-packages-and-migrate-examples/`。
- `openspec validate --specs`：44 个主规格通过，0 失败。
- 最终五个风格：`vibe-night`、`vibe-fable`、`doc-archive`、`count-ledger`、`deep-journey`；五个规范示例位于 `styles/examples/<style-id>/<slug>/`。
