## Why

用户明确要求把某一条抖音参考作品的**整条音频**用作新作品的唯一音源。当前主规格只允许参考素材用于分析、比对与制作参考，禁止其进入渲染链路；现有工具也没有从参考视频提取音轨的入口。手工用 ffmpeg 抽音频既无法复核来源，也无法证明这条音频来自哪条参考作品、是否经过替换。

这不是要放开「参考素材可随意进入成片」，而是需要一个**可追溯的窄例外**：默认禁令不变，只有用户明确指定、且把音频提取为作品目录内的独立资产并写入来源与摘要后才能使用。

## What Changes

- 新增 `m2v ref audio <参考目录> --project <作品目录> --user-authorized "<授权说明>" [--name <名称>] [--force] [--json]`：
  - 先按 `recipe.json` 复核参考目录，只接受视频作品；
  - 从视频第一条音频流提取 PCM 16-bit、48 kHz、保留源声道的 WAV 到作品 `assets/audio/`；
  - 写同名 `.provenance.json`，记录参考作品 ID、作者、来源链接、参考视频与提取音频的 SHA-256、字节数、采样数、时长、采样率、声道、提取时间、用户授权原文、许可状态与第三方音乐风险；
  - 输出 60 fps 总帧数（`ceil(samples × 60 / sampleRate)`）与可直接粘贴的 `soundtrack.music` 片段；
  - 目标已存在时默认拒绝，来源与摘要一致才复用，`--force` 才替换。
- 修改 `reference-media-acquisition` 的「使用边界」：保留默认禁令，新增「用户明确指定单条作品音频」的受控例外；渲染链路仍不直接读取 `refs/`。
- 更新 README、SKILL 与声音/分镜参考文档，补充无旁白作品只有音床时的全片音源用法、`gainDb`/淡入淡出必须显式归零、`cut` 帧数公式。
- 增加离线测试：提取、provenance、授权缺失、校验失败、覆盖保护、越界名称、非视频/非 general、无音轨与失败不留半成品。

## Capabilities

### Modified Capabilities

- `reference-media-acquisition`：参考素材默认仍不进入渲染链路；新增用户明确授权的单条参考音频提取与留证能力。

## Impact

- 新增 `src/m2v/reference/audio.py`；修改 `src/m2v/reference/cli.py`、`src/m2v/cli.py` 与文档。
- 不修改渲染引擎、混音实现或通用准备逻辑：无旁白 + `soundtrack.music` 的既有契约足够承载本能力。
- 不改 `examples/`、不新增视频类型、不引入新依赖。
- `refs/`、`videos/` 与 `work/` 仍是内容目录，保持忽略；新增代码与文档进入版本控制。
