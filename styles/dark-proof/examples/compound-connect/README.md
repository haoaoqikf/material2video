# 让积累，参与下一次

dark-proof规范示例，采用最近完成的40秒R5版：数字提出问题，大字与小球明确命题，一个雪球建立直觉，随后用表格、折线、柱形和公式逐步解释。1920×1080、30fps、1200帧；无旁白、无配乐，仅原创事件音。

- [观看当前示例](outputs/video.mp4)
- [近期创作复盘与可迁移经验](CASE_STUDY.md)
- [设计与制作合同](DESIGN.md)、[修改练习](HOWTO.md)
- [验证和覆盖限制](VERIFICATION.md)、[代码审查](CODE_REVIEW.md)
- [来源与数学边界](SOURCES.md)、[声音](SOUND.md)、[参考采用范围](style-reference.md)

## 从源码重建

在仓库根执行，先安装仓库声明的Python和web依赖：

```powershell
uv run python fonts/fetch.py
uv run python styles/dark-proof/examples/compound-connect/assets/fetch.py
uv run python styles/dark-proof/examples/compound-connect/assets/compose.py
uv run m2v validate --project styles/dark-proof/examples/compound-connect
uv run m2v prepare --project styles/dark-proof/examples/compound-connect
uv run m2v render --project styles/dark-proof/examples/compound-connect --jobs 2
uv run m2v qa --project styles/dark-proof/examples/compound-connect
```

`assets/compose.py`统一生成分镜、事件、字幕窗口与制作合同；声音参数在`assets/sound-recipe.json`，固定摘要在`assets/sound-checks.json`。恢复器复用现有合成导入器，摘要不符会失败；无需原作品、参考下载或本机缓存。`assets/recipe.json`为空，因为没有外部图像/视频素材。字体按仓库登记恢复，禁止系统回退。

数学限定为初始100、每轮按现有总量增加1%，对照固定加1，无新增外部投入。雪球只作类比，不模拟这个精确增速，也不预测现实学习、自然或投资回报。

旧68秒示例已在本地根`outputs/historical/`保护，不再作为当前规范实现。源码与配方入库；outputs、音效二进制和历史记录不入库。GUIDE同步修订会改变共享风格指纹，既有dark-proof作品再次导出前须重新准备；组件与风格版本未变。制作完成状态只以当前VERIFICATION为准，重建命令本身不等于独立审核通过。
