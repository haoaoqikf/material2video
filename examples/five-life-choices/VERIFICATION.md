# 交付验证

本文件随30秒剪纸版实际制作更新。最终候选、恢复的音频、时间标注帧与独立评审包均位于忽略的 `videos/examples/five-life-choices/outputs/`，不进入版本控制。

## 自动检查

| 检查 | 命令 | 结果 |
|---|---|---|
| 材料校验 | `uv run m2v validate --project examples/five-life-choices` | 通过；900帧画面、全片音轨和本地素材引用符合配置 |
| 时间轴准备 | `uv run m2v prepare --project examples/five-life-choices` | 通过；900帧 / 1920×1080 / 30fps；preparedFingerprint `24644aee94078edde8bae425d05f46de42e630d5e1c2b45b5b752c6586046c43` |
| Web 类型检查 | `pnpm -C web typecheck` | 通过 |
| Web 测试 | `pnpm -C web test` | 通过；6个文件、85项测试 |
| Web 构建 | `pnpm -C web build` | 通过；Vite生产构建完成；contract chunk 542.75 kB，出现500 kB体积提示 |
| 示例与文档测试 | `uv run pytest tests/test_five_life_choices_example.py tests/test_examples_strict.py tests/test_doc_examples.py -q` | 通过；41项测试；pytest缓存目录因WinError 5未写入，不影响测试 |
| 完整候选与技术QA | `uv run m2v render --project examples/five-life-choices` / `uv run m2v qa --project examples/five-life-choices` | 通过；1920×1080、30fps、900帧、30秒；冻结帧、字幕对比度、响度、音画同步、主张检查通过；画面实测。SHA-256 `81657fab9515c49fcc1bb8cc6119ee18faf7a0dc151f5e15d3846b87a7641b44`；preparedFingerprint `24644aee94078edde8bae425d05f46de42e630d5e1c2b45b5b752c6586046c43` |

## 动态门禁

23–27秒学习窗口先以4秒完整帧序列预演，并逐轮由隔离评审只检查匿名评审包。通过后再扩展全片；最终全片另由两名隔离评审检查节奏、文案、接触动作、393px可读性及相对旧版基线的表达差异。意见与对应视频摘要绑定；未完成的复核不得记为通过。

## 画面限制

本片只有程序化矢量剪纸形状，手机复核重点是主体、路径、门洞、桥板与阶梯关系。抽样帧只能支持可见动作和视觉关系判断，不能代替真实观众测试，也不支持“惊艳”、记忆或留存等效果承诺。

## 最终候选独立复核

视频 SHA-256：81657fab9515c49fcc1bb8cc6119ee18faf7a0dc151f5e15d3846b87a7641b44。K07全片结构与视觉评审、K21学习段评审均由隔离评审完成，未发现阻断项。结构建议城市段稍短、结尾停留略长；视觉建议手机尺寸窗口细节可简化；学习段建议末帧驻留略短，并指出台阶寓意较抽象。以上作为偏好记录，不影响现有主题识别。评审只基于抽样帧，不能证明真实观众记忆、留存或声音体验。

## 新旧对应事件对照

隔离盲评同尺寸匿名图组：B（新版）更容易看清主体动作和事件关系，统一配色与较大标题在手机上更醒目；A（旧版）保留了更多年龄、时间、路径与阶段标签信息，但细节较密且字号较小。新版明确牺牲了这些具体节点信息，集中讲五种因素怎样影响道路。该对照基于7组静态代表帧，不能评价动态节奏、音画质量或观众反应；评审包本身未携带视频摘要，最终视频绑定摘要仍以K07/K21评审包中的SHA为准。
