# 《接：让积累生长》

dark-proof规范示例，解释非金融复利效应：过去的成果参与后续创造，新增部分也成为新的增长来源。原创种子机制寓言与凑十法复用；1920×1080、30fps，无旁白无配乐，仅事件音。当前68秒成片已通过完整试制独立盲审、同轮目标对照、全片内部检查、新代理终审与设计返工复查；当前账本G0–G6均完成。

## 重建

```powershell
uv run python fonts/fetch.py
uv run python styles/dark-proof/examples/compound-connect/assets/fetch.py
uv run python styles/dark-proof/examples/compound-connect/assets/compose.py
uv run m2v prepare --project styles/dark-proof/examples/compound-connect
uv run m2v render --project styles/dark-proof/examples/compound-connect --jobs 4
```

assets/compose.py是事件、字幕与合同的唯一制作源；scenes/model.ts是帧状态，visual.tsx是原创主体和画面基础。scenes/opening、core、grove、learning、closing分别对应连续段落。DESIGN记录目标、风险及逐场用途；SOURCES与SOUND记录口径和来源；VERIFICATION记录真实完成情况。outputs、基线、概念图及assets/media均不入库。
