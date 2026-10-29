# 风格示例

本目录存放风格包的规范示例作品：`styles/examples/<style-id>/<slug>/`。示例不参与风格发现，也不会改变任何风格包指纹；它们是风格落到成片上的可校验工件。

| 示例 | 风格 | 选题 | 时长 |
|---|---|---|---:|
| [fold](vibe-night/fold/README.md) | `vibe-night` | 折叠：一颗珠子改掉一个细胞的形状（镰状细胞） | 33 秒 |
| [pigeon](vibe-fable/pigeon/README.md) | `vibe-fable` | 鸽子的迷信（斯金纳 1948）：食物按时间来，它却碰巧在转圈 | 33 秒 |
| [american-science-milestones](doc-archive/american-science-milestones/README.md) | `doc-archive` | 从电报到大模型：十项美国科学里程碑 | 30 秒 |
| [compound-interest](count-ledger/compound-interest/README.md) | `count-ledger` | 复利：同样一万、两种做法、三十年后差多少 | 29 秒 |
| [solar-system-journey](deep-journey/solar-system-journey/README.md) | `deep-journey` | 太阳系之旅：从太阳到奥尔特云的一镜到底 | 174.55 秒 |

风格包只提供表现层；题材数据、素材、数学、旁白、分镜与声音属于示例作品。示例改动只会使自身准备失效，不会改变所选风格包的指纹。

```powershell
uv run python fonts/fetch.py
uv run m2v validate --project styles/examples/doc-archive/american-science-milestones
uv run m2v validate --project styles/examples/count-ledger/compound-interest
uv run m2v validate --project styles/examples/deep-journey/solar-system-journey
uv run m2v validate --project styles/examples/vibe-night/fold
uv run m2v validate --project styles/examples/vibe-fable/pigeon
```
