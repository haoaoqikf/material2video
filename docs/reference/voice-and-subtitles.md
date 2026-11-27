# 声音与字幕

本文件从 README 下沉，权威内容仍以 [`.agents/skills/material2video/references/`](../../.agents/skills/material2video/references/) 为准。具体见[配音与节奏](../../.agents/skills/material2video/references/voice-and-rhythm.md)和[准备与字幕](../../.agents/skills/material2video/references/prepared-and-subtitles.md)。

## 默认配音

五类作品有自身旁白且需要选音时，制作助手默认采用「真人播客女」，配置与覆盖规则见[配音指南](../../.agents/skills/material2video/references/voice-and-rhythm.md#口播作品的固定默认音色)。

纪实口播默认使用本地 `kokoro`，其他类型默认使用联网的 `edge-tts`。纪实口播可按文案选择合适的 Kokoro 中文音色，例如 `zf_027` 这类本地音色，并按作品内 `models/registry.json` 恢复固定 revision 的模型。需要克隆参考音色时，作品可声明 `qwen3-tts`，用 `clone_<slug>` 指作品内参考音频与参考文本，按 `models/qwen3-tts/registry.json` 恢复 Qwen3-TTS 主模型与 stable-ts 对齐模型。Qwen3-TTS 使用 FFmpeg `atempo` 做保音高变速，再对实际音频强制对齐。三种后端都输出真实词边界，进入同一字幕断句与停顿整形链路。Kokoro 与 Qwen3-TTS 目前只接受纯中文旁白，数字与拉丁字母会在合成前失败；Qwen3-TTS 参考音色的来源与用户授权必须留证，不能从模型仓库恢复参考音频。

## 模型恢复

使用 Kokoro 的作品需在自身依赖中安装 `kokoro` 与 `misaki[zh]`（模板提供 `kokoro` extra），并用 `python models/fetch.py --download --voice <音色>` 恢复模型。使用 Qwen3-TTS 的作品需安装 `qwen-tts` 与 `stable-ts`（模板提供 `qwen3-tts` extra），并用 `python models/qwen3-tts/fetch.py --download --voice <音色>` 恢复主模型与对齐模型。参考音色必须随作品保存并登记摘要。详见[独立工程说明](../../templates/standalone/README.md)。

## 字幕与柔光

字幕支持中文主行 + 英文次行上下排列；带字幕的五类作品默认从实绘背景选择浅字或深字和自适应柔光，`frames.json` 保持字体、字号和画幅参数的统一入口。既有独立工程需采用更新后的本地运行时再生成。画面标注和片尾编排见[素材采用与署名](../../.agents/skills/material2video/references/material-sourcing.md#5-采用政策与署名)。
