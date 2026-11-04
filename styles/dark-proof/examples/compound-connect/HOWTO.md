# 《接》练习：让第一轮返回更从容

本练习修改唯一制作源，不直接修改生成的分镜。先保留工作区改动，避免覆盖自己的其他修改。

在 `assets/compose.py` 中，把第一轮 `return-travel` 从 `a+135` 改为 `a+120`。合并仍在 `b-24`，路径总长和起终点不变，移动窗口因此增加15帧；`travel` 音效也随事件前移。

```powershell
uv run python styles/dark-proof/examples/compound-connect/assets/compose.py
uv run m2v validate --project styles/dark-proof/examples/compound-connect
uv run m2v prepare --project styles/dark-proof/examples/compound-connect
uv run m2v preview --project styles/dark-proof/examples/compound-connect --start-seconds 20 --end-seconds 24 --jobs 2
```

检查产出包是否从出口沿完整路径返回，是否在合并前一直保留100，合并后才成为110；注意移动音与实体起步是否一致。不要只检查两个端点。

练习完成后把 `a+120` 恢复为 `a+135`，再次运行compose和prepare。若正式采用新节奏，还须更新声音说明并重新执行受影响窗口的检查与独立评审；历史证据不能替代当前版本。

检查手机小字时，先看真实393宽单帧，再看原生图；不能靠放大或记忆补字。`lookdev --sheet 8` 表示全片均匀取8帧；要检查8秒附近，应使用 `--sheet 8 8.1`，对应本片第240／243帧。
