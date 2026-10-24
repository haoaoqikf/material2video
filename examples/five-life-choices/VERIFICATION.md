# 交付验证

本文件记录 65 秒重制实际执行的检查与结论；生成媒体、候选、基线、评审包与帧图保存在本地 `videos/examples/five-life-choices/outputs/`，不入库。

## 自动化检查

| 检查 | 命令 | 结果 |
|---|---|---|
| 材料校验 | `uv run m2v validate --project examples/five-life-choices` | 通过 |
| 时间轴准备 | `uv run m2v prepare --project examples/five-life-choices` | 通过；1950 帧 / 65 秒 / 1920×1080 / 30 fps / 无声 |
| 完整粗片 | `uv run m2v preview --project examples/five-life-choices --start-seconds 0 --end-seconds 64.9` | 通过；逐秒接触表保存于本地 `work/full2/sheet.png`，不作为交付门禁 |
| Web 数值行为测试 | `pnpm -C web test` | 87 passed |
| Web 类型与构建 | `pnpm -C web typecheck` / `pnpm -C web build` | 通过 |
| 示例与文档测试 | `uv run pytest tests/test_five_life_choices_example.py tests/test_examples_strict.py tests/test_doc_examples.py` | 通过 |
| 全片生成 | `uv run m2v render --project examples/five-life-choices` | 通过；1950 帧、1920×1080、30 fps、65.0 秒、数字静音；SHA-256 `d44ad5a675170bf5e90138c51693ea4011c964d69a566695c8bb834061e9e562` |
| 技术 QA | `uv run m2v qa --project examples/five-life-choices` | 通过；冻结帧 0、重复帧 0、近静止比 0；静音验收通过；音画差 0.016 秒；字幕对比度 19.43；claims 覆盖通过（可见性未评估） |

## 关键帧门禁

- 七张无文字关键帧：开场 5.3 / 城市 11.5 / 行业 21.0 / 伴侣 32.0 / 投资 42.5 / 学习 52.4 / 终幕 62.4 秒。
- 隔离评审只读取图像与问题，不读设计、源码、旧评审。前六幕由 K02 评审读出目标变化；终幕经 K03–K09 多轮返工，最终 K09 放射人生扇由 3/3 评审读出“同一点向右放射出许多路径”。
- 终幕五个阶段在单帧中未被稳定数出；作为已知限制披露，由成片章节标签与五道阶段弧共同承担，不写成已通过的五阶段静帧识别。
- 证据：[visual-notes.md](../../videos/examples/five-life-choices/outputs/visual-notes.md)（生成媒体与评审包不入库）。

## 视觉复核（待最终候选）

- 最终候选完成后，两名隔离代理分别检查结构节奏与视觉文案；另做与 b02 基线的对应角色匿名比较。
- 手机基准：852×479 CSS 像素；另查 393 宽与 200 宽缩略图。393 宽只保证主题与主体辨认，不承诺小字可读。
- 未实时播放全片，也未试听（成片无旁白/配乐；最终音轨状态以 QA 为准）。

## 已知限制

- 终幕五阶段静帧计数不稳定；成片用五章标签提示，不宣称观众能独立数出五个阶段。
- 终幕从连续世界切入放射人生扇时采用硬切淡入，未达到世界变形的连续转场；已作为已知限制披露，不写成已通过连续转场。
- 人物在广角镜头中很小，393 宽可能退化为白点；城市与终幕的人物定位依赖环标记。
- 内部空间是长期条件的解释隐喻，不是真实地理、行业排名、收益公式或唯一成功路径。
- 没有真实发布数据，不推算留存、跳出率或真实记忆，不宣称惊艳。
