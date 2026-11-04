# 《接》示例

`dark-proof` 的规范示例：64秒、1920×1080、30fps，无旁白、无配乐，仅原创事件音效。一个连续实验说明：让产出参与下一轮，才会改变下一轮的起点。

两组都从100单位出发，每轮产出为当轮投入的10%。一组取走保存，30轮后投入100、已取300，总量400；另一组把产出接回，30轮后总量约1,745，是前者的4.36倍。这是忽略损耗的数学示意。

画面从30次重复进入100单位资源，跟随同一产出包返回，依次看见100→110→121→133.1，再进入共同线性坐标下的30轮曲线、总量对比与片名回接。参考片只作风格分析，画面和音轨没有进入示例。

## 重建

```powershell
uv run python fonts/fetch.py
uv run python styles/dark-proof/examples/compound-connect/assets/fetch.py
uv run python styles/dark-proof/examples/compound-connect/assets/compose.py
uv run m2v validate --project styles/dark-proof/examples/compound-connect
uv run m2v prepare --project styles/dark-proof/examples/compound-connect
uv run m2v lookdev --project styles/dark-proof/examples/compound-connect --sheet 2 8 15 21.5 23.3 29.6 39.5 46 54 61
uv run m2v render --project styles/dark-proof/examples/compound-connect --jobs 4
uv run m2v qa --project styles/dark-proof/examples/compound-connect
```

声音由 `assets/synthesize.py` 生成，按 `assets/recipe.json` 校验摘要、采样率、声道与时长。`assets/media/` 与 `outputs/` 都不入库。

## 材料

- `assets/compose.py`：模型参数、阶段、事件、15条屏幕短句与声音绑定的唯一制作源；生成分镜、项目配置并同步DESIGN机器合同。
- `scenes/model.ts`：数学账本、资源坐标与返回路径；不读取外部参考。
- `scenes/compound-connect.tsx`：逐帧画面入口，复用共享光轨、粒子、图表与公式组件。
- `DESIGN.md`：采用方案、表达条件与检查点合同。
- `SOURCES.md`、`SOUND.md`：素材边界、许可与事件音定位。
- `VERIFICATION.md`：实际验证、评审与未覆盖范围。
- `HOWTO.md`：修改返回动作时序的练习。

公式就绪后才通知采集器开始。字体必须从登记表恢复，不静默回退系统字体。共享接口见[表达组件](../../../../.agents/skills/material2video/references/visual-components.md)。
