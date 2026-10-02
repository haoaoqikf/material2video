# 少一个选项：keynote 设计语言标杆

本示例将观点型文章改编为单场景动态叙事：整条视频持续呈现同一张分叉路线地图，固定路线锚点逐步淡出，最后留下单一路径。数字仅用于示意，不代表实证。

- [文章](article.md)：167 字，正文符合 130～170 字标准。
- [v4 分镜](storyboard.json)：全片代码 renderer、4 个叙事阶段、1080 帧声明时长。
- [动作脚本](motion-design.md)：说明对象连续性、状态演进与阶段表达。
- [评审摘要](review.md)：记录主题、实际时长、画面评审和限制。

画面启用 `keynote` 设计预设。明暗主题令牌验证见 `tests/test_react_design_tokens.py`，通过浏览器实测 V4 主题令牌。正式评审/渲染产物写入被 Git 忽略的 `videos/examples/keynote-baseline/` 工作区。
