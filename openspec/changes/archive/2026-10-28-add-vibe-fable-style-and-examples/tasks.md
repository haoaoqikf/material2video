## 1. 风格包

- [x] 1.1 新建 `styles/vibe-fable/`：清单声明 `types: ["general"]`、`frames: [{"width":1920,"height":1080}]`、`requires.narration = "none"`，不带 `assets`；`tokens.json` 写入暖白/金/红语义、五个场景配色、仪表与版式；`GUIDE.md` 写明适用场景、组件表、角色画法与屏幕字幕约定。验证 `uv run m2v styles --json` 同时返回两个包。
- [x] 1.2 实现十个组件：`fable-stage`、`parallax-band`、`instinct-gauge`、`scene-note`、`top-line`、`counter-row`、`callout`、`rule-card`、`title-fable`、`screen-subtitle` 与共享 `kit`；全部由帧号与固定种子驱动，不用挂钟、随机数或 CSS 动画。
- [x] 1.3 风格发现跳过保留目录 `styles/examples/`；其余子目录仍须为有效包。验证 `m2v styles` 只列两个包、按 `examples` 加载明确失败。
- [x] 1.4 同步文档：`styles/README.md`、风格接入契约与 README 当前能力。

## 3. 测试与验证

- [x] 3.1 新增 `tests/test_vibe_fable_style.py`：注册、保留目录、清单与 tokens、类型画幅拒绝、组件确定性与导入边界、指纹覆盖、旁白约束、示例可校验、示例不被当包。
- [x] 3.2 慢速用例：寓言组件在包内构建成功、同一帧两次录制字节一致。
- [x] 3.3 运行 `uv run pytest`（含 slow）与 `sync_docs.py --check`，确认 `examples/` 三个固定示例与金融、住宅类型不回归。

## 4. 交付

- [x] 4.1 独立子代理只读审查：核对包边界、无旁白约束、示例与包分离、`examples/` 上限规则未被触碰；2 项阻塞（逐幕时钟、实现与字幕的独立性）与 8 项一般问题已修正并复查。
- [x] 4.2 检查暂存范围并提交实施；排除示例 `outputs/`、生成媒体与字体二进制。（对应提交 `0ec7d18`）
- [x] 4.3 同步主规格并归档变更，提交归档结果。（对应提交 `29d27e1`）

> 2026-11-12 内容清理：已删除用户指定作品的专属内容；本档案仅保留其余历史范围，不代表本轮重新验证。
