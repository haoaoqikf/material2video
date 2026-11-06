# 随附示例

七部作品按五类放在 `examples/<类型>/<作品名>/`，均使用 project v2 与分镜 v9。作品专属画面与参数在各自 `scenes/`，不作为共享风格包。生成媒体与 `outputs/` 不入库。

| 类型 | 示例 |
|---|---|
| 图文动效 `text-motion` | [fold](text-motion/fold/README.md) |
| 数据演化 `data-evolution` | [compound-interest](data-evolution/compound-interest/README.md)、[compound-connect](data-evolution/compound-connect/README.md) |
| 原理隐喻 `principle-metaphor` | [pigeon](principle-metaphor/pigeon/README.md)、[luck-on-stage](principle-metaphor/luck-on-stage/README.md) |
| 三维空间 `spatial-3d` | [solar-system-journey](spatial-3d/solar-system-journey/README.md) |
| 纪实素材剪辑 `documentary-edit` | [american-science-milestones](documentary-edit/american-science-milestones/README.md) |

先按各示例 `assets/recipe.json` 和 README 恢复素材，再运行：

```powershell
uv run m2v validate --project examples/text-motion/fold
uv run m2v prepare --project examples/text-motion/fold
uv run m2v preview --project examples/text-motion/fold --limit-frames 30
```

其他示例将路径替换成上表目录。字体统一由 `uv run python fonts/fetch.py` 恢复；已有文件摘要不一致时恢复命令会拒绝覆盖。
