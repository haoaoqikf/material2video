# 风格包目录

已登记一个正式风格包：

| ID | 版本 | 适用 | 内容 |
|---|---|---|---|
| `vibe-night` | 1.0.0 | `general` 1920×1080 | C 夜曲：色板与三区版式、九个表现组件加屏幕字幕组件、宋体资产与屏幕字幕约定 |

`uv run m2v styles` 显示已注册包，`uv run m2v styles --json` 返回同一清单。包的使用方式、
清单字段与制作边界以[风格接入契约](../.agents/skills/material2video/references/style-pack.md)为准；
C 夜曲的取色、组件与无旁白字幕约定见 [styles/vibe-night/GUIDE.md](vibe-night/GUIDE.md)。

每个直接子目录代表一个风格包，必须提供有效 `style.json`；不要在此放缓存、样片或临时目录。
风格包只提供表现层，选择风格不会自动换肤；三个固定示例不因新增包而改变。
