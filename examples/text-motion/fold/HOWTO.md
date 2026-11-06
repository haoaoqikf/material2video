# 修改练习：相机与几何布局

在临时副本操作，从仓库根目录运行：

```powershell
@'
from pathlib import Path
import shutil, tempfile
src = Path('examples/text-motion/fold')
dst = Path(tempfile.mkdtemp(prefix='m2v-fold-')) / 'fold'
shutil.copytree(src, dst, ignore=shutil.ignore_patterns('outputs', '__pycache__'))
print(dst)
'@ | uv run python -
```

将输出路径记作 `$fold`。每次修改后从仓库根目录执行：

```powershell
uv run m2v validate --project $fold
uv run m2v prepare --project $fold
uv run m2v lookdev --project $fold --motion 8.0 10.0
uv run m2v render --project $fold
```

## 相机

在副本 `scenes/fold.tsx` 的 `CAM` 中，将 `at: 9.15` 的关键帧改成 `at: 9.3`。其他关键帧及世界对象保持原样；拉远稍晚，检查突变珠子到细胞全貌的过渡、字幕时点和前后场景能否认回同一对象。字幕和音效不会自动随相机关键帧移动，需单独核对。

## 布局

在副本中运行 `uv run python "$fold/tools/gen_layout.py" --seed 2`，重建 `scenes/layout.json`。种子只改变满足约束的路径，146 颗、第 6 颗的身份、邻接和接合不变；若找不到符合条件的路径或种子超出 1–100000，程序在写盘前失败。重跑准备和成片，检查折叠、黏点与接合的完整窗口；几何断言不能代替观感判断。

恢复方法：删除临时副本，或从原仓库重新复制；不要用副本覆盖原作品。完整验收仍需按适用审核计划独立观察。两项练习已在 2026-10-29 的临时副本执行验证：相机关键帧后移仍能认回同一对象；种子 2 仍为 146 颗、索引 5 为 knob、接合通过，种子 0 明确失败且不覆盖有效布局。
