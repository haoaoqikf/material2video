# 风格包目录

已登记两个正式风格包，另设一个保留目录存放风格示例。

| ID | 版本 | 适用 | 内容 |
|---|---|---|---|
| `vibe-fable` | 1.0.0 | `general` 1920×1080，无旁白 | B 寓言：扁平插画舞台、三层视差、本能读数仪表、对照计数、引线标注、规则卡与逐字亮起的屏幕字幕 |
| `vibe-night` | 1.0.0 | `general` 1920×1080，无旁白 | C 夜曲：色板与三区版式、九个表现组件加屏幕字幕组件、宋体资产与屏幕字幕约定 |

`uv run m2v styles` 显示已注册包，`uv run m2v styles --json` 返回同一清单。包的使用方式、
清单字段与制作边界以[风格接入契约](../.agents/skills/material2video/references/style-pack.md)为准；
各包的取色、组件与无旁白字幕约定见包内 `GUIDE.md`。

每个直接子目录代表一个风格包，必须提供有效 `style.json`；`examples/` 是保留目录，存放
风格示例，不参与风格发现。不要在此放缓存、样片或临时目录。
风格包只提供表现层，选择风格不会自动换肤；`examples/` 下的三个固定示例不因新增包而改变。

## 风格示例

示例放在 `styles/examples/<style-id>/<slug>/`，不占用 `examples/` 的三个固定名额。
它们演示风格包实际落到成片上的样子，也是回归用的可校验工件。

| 示例 | 风格 | 选题 | 时长 |
|---|---|---|---:|
| [pigeon](examples/vibe-fable/pigeon/README.md) | `vibe-fable` | 鸽子的迷信（斯金纳 1948）：食物按时间来，它却碰巧在转圈 | 33 秒 |
| [fold](examples/vibe-night/fold/README.md) | `vibe-night` | 折叠：一颗珠子改掉一个细胞的形状（镰状细胞） | 33 秒 |

示例**不能**放进 `styles/<id>/` 包内：包指纹覆盖包内所有文件，示例一改就会让所有选了该
风格的作品准备失效。两个示例都按已登记样片的选题与分镜重写，实现与媒体自绘，不复制上游
`film.js`、GIF/JPG 或画面；产物写入各自 `outputs/`，已被版本控制忽略。

```powershell
uv run python fonts/fetch.py
uv run m2v validate --project styles/examples/vibe-night/fold
uv run m2v validate --project styles/examples/vibe-fable/pigeon
```
