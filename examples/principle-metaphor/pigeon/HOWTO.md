# 修改练习：事件与取景

在临时副本操作，保留原作品和 `outputs/`：从仓库根目录运行

```powershell
@'
from pathlib import Path
import shutil, tempfile
src = Path('examples/principle-metaphor/pigeon')
dst = Path(tempfile.mkdtemp(prefix='m2v-pigeon-')) / 'pigeon'
shutil.copytree(src, dst, ignore=shutil.ignore_patterns('outputs', '__pycache__'))
print(dst)
'@ | uv run python -
```

将输出路径记作 `$pigeon`，例如 `$pigeon = 'C:\Users\me\AppData\Local\Temp\m2v-pigeon-…\pigeon'`。每次修改后从仓库根目录执行：

```powershell
uv run m2v validate --project $pigeon
uv run m2v prepare --project $pigeon
uv run m2v lookdev --project $pigeon --event wander:turn-1 --before 15 --after 45 --hold 15
uv run m2v render --project $pigeon
```

## 转圈事件

在副本 `storyboard.json` 的 `wander.events` 中将 `turn-1.frame` 从 135 改成 132。幕从全片 9 秒开始，因此轨迹起始从 13.5 秒改为 13.4 秒；引用此事件的 `swish` 音效也提前三帧。`pigeon.tsx` 的 `act` 读取事件并影响转圈方向和轨迹出现；字幕窗口、其他动作、食槽常量不会自动联动，须检查是否仍讲得清。喂食仍发生在 15 和 30 秒，不能随练习改动。该演示仅调整一小段，避免跨幕状态发生跳变；听音并观看完整事件及前后衔接，不仅看事件帧。

## 取景

恢复副本后，在 `scenes/pigeon.tsx` 的 `SHOTS.wander.to.focus` 将 `[1200, 555]` 改为 `[1180, 555]`。镜头终点左移，房间、角色及计时器的全片状态不变。播放 wander 前后，检查主体、食槽与计时器能否认回，以及字幕是否遮挡。帧拼图只帮助定位，不代替动态观察。

恢复方法：删除临时副本，或从原仓库重新复制；不要用副本覆盖原作品。完整验收仍需按适用审核计划独立观察。两项练习已在 2026-10-29 的临时副本执行验证：事件移动后引用音效同步移动，喂食仍在 15 秒与 30 秒；取景修改后角色、食槽与计时器仍可认回，字幕未遮挡主体。
