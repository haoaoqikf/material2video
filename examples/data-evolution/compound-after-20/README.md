# 复利 40 年

如果一万元每年赚 10%，赚到的钱也继续投资，为什么同一笔钱后 20 年赚的利息，是前 20 年的 6.73 倍？影片用薄片演示利息怎样再生利息，再让年柱从同一条零线生长，最后按年份分组归入两座塔。

独立工程导出四幕、原 Qwen3-TTS 克隆旁白、双语字幕，成片 1920 × 1080、30 帧/秒、1,161 帧、38.7 秒。编排见[总设计](DESIGN.md)和[分镜](storyboard.json)。

## 恢复并运行

复制整个目录，在副本中运行。使用 Node.js 22.12 或更新版本、锁文件指定的 pnpm、uv 和 Python 3.12。实际采集使用 Playwright Chromium 和支持 WebGPU 的 GPU，路径追踪在 Windows 的 ANGLE/D3D11 环境实测。场景页冷启动最多等待 90 秒，页面就绪和逐帧检查仍使用各自的等待限制。

```powershell
pnpm install --frozen-lockfile --ignore-workspace
uv sync --frozen --python 3.12 --extra qwen3-tts
uv run --frozen python models/qwen3-tts/restore-voice.py --source-project '<原作品目录>'
pnpm run setup --download --install-browser
pnpm run validate
pnpm run build
pnpm run video:prepare
pnpm run preview --limit-frames 30 --jobs 1
pnpm run render --jobs 1
pnpm run qa
```

原作品的参考 WAV 和音色档案须在本地可用。若两份文件单独保存，音色恢复命令可改用 `--registry '<本地 Qwen3-TTS 音色登记.json>' --audio '<同一份参考.wav>'`。恢复入口校验 WAV 摘要以及含参考文本的完整音色档案摘要，成功后生成本地运行登记并恢复 WAV。资料缺失、摘要不匹配或目标已有其他内容时会失败。参考 WAV、私人登记与参考文本留在本地。公开模型版本、权重摘要与许可证见[模型模板](models/qwen3-tts/registry.template.json)。

已有匹配的公开缓存时，可设置 `M2V_TTS_CACHE`、`M2V_FONT_CACHE` 并去掉 `setup` 的 `--download`。字体版本与许可证见[字体登记](fonts/registry.json)。预演可用 `--limit-frames` 控制采集上限，正式渲染输出 `outputs/video.mp4`，技术报告在 `outputs/qa.json`。

场景与声点修改后，用 `pnpm test` 验证同一零线、两组归塔的对象连续性与金额，再按[必审窗口](design/formal-review-windows.json)抽取有序帧和适用音频信号复核。
