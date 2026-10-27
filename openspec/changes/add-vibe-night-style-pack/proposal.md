## Why

已登记的参考项目 vibe-knowledge-film 的 C 夜曲外观已经过一次作品级手工复刻，但仓库里没有可安装的风格包：`styles/` 为空，制作者每次都要重新抄数值、重写光点与片名卡，风格无法复用，也无法用准备指纹和缓存失效机制保护。需要把 C 夜曲转成第一个正式风格包，并同时补上它依赖的两件事——宋体资产与"无旁白、字幕即文案"的屏幕文字约定。

本变更只做 C 夜曲；B 寓言与音效扩充按影响另行登记。

## What Changes

- 新增正式风格包 `styles/vibe-night/`：清单、tokens、指导、C 夜曲组件与宋体资产。
- 修改 `style-registry` 规格，允许并登记首个正式风格包；`m2v styles` 从空目录变为返回 `vibe-night`。
- 新增 C 夜曲风格规格：色板语义、三区版式、组件行为、字体许可与原创试制验收。
- 新增通用视频"无旁白知识片"的屏幕字幕约定：作品在 `subtitleSafeArea` 内自绘单行文字，不新增分镜字段，共享字幕层保持不变。
- 新增讲解设计参考文档：六种画法、找形象决策树、三问、可数化、无旁白字幕稿规范，并接入现有 general 制作参考。
- 制作一条 30–45 秒、不入库的原创试制片，作为风格包验收证据。
- 更新 README、风格目录说明与固定文档索引；三个固定示例不变。

## Capabilities

### New Capabilities

- `vibe-night-style`：C 夜曲风格包的注册内容、可用组件与字体、屏幕字幕约定和原创试制验收。

### Modified Capabilities

- `style-registry`：从"首期不包含正式风格"改为登记第一个正式风格包，并补充正式风格包的产品级验收要求。

## Impact

- 新增 `styles/vibe-night/` 与包内字体资产（OFL 许可随包）。
- 修改 `openspec/specs/style-registry/spec.md` 与 `styles/README.md`、[风格接入契约](../../.agents/skills/material2video/references/style-pack.md)、[外部参考项目登记](../../.agents/skills/material2video/references/external-projects.md) 的状态说明。
- 新增 `.agents/skills/material2video/references/explainer-design.md`，并在 general 制作入口引用。
- 试制片位于 `videos/general/<slug>/`，按内容不入库规则不提交；只提交方法、共享资产与文档。
- 不新增 CLI 命令，不改变视频类型、分镜 schema、制作门、审核职责或成片验收条件；三个固定示例不回归。
