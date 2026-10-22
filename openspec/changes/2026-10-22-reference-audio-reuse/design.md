## 背景

一条参考作品的音频要作为新作品的唯一音源。现有母版链路已经支持「无旁白作品 + `soundtrack.music`」：音床以 0 dB 进入母版，不循环、不做淡入淡出，母版按全片帧数裁剪与补齐。缺的不是混音能力，而是**来源可复核的提取入口**与**规格上的受控例外**。

## 数据链路

1. **参考校验**：`verify_directory` 按 `recipe.json` 复核参考目录；只接受 `metadata.json` 中 `kind: video` 的作品。
2. **授权显式化**：命令要求 `--user-authorized "<说明>"`，把用户原话写入 provenance；没有说明就失败，不产生音频。
3. **提取**：ffmpeg 读取第一条音频流，输出 PCM 16-bit、48 kHz、保留源声道的 WAV。每帧 60 fps 对应 800 个采样，帧数没有浮点歧义。
4. **帧数与时间轴**：`totalFrames = ceil(samples × 60 / sampleRate) = (samples × 60 + sampleRate - 1) // sampleRate`。这与使用 `cut` 转场时的 `sum(durationFrames) = totalFrames` 同源；尾部最多补 1 帧静音，不截断。
5. **留证**：作品 `assets/audio/<name>.provenance.json` 记录参考作品、视频摘要、音频摘要、采样参数、授权原文、许可状态与第三方音乐风险。
6. **复用判定**：目标已存在时，只有参考视频摘要、音频摘要与字节数都一致才复用；否则要求 `--force`。
7. **使用**：作品不写旁白，显式声明 `soundtrack.music`：`gainDb: 0`、`loop: false`、`fadeInMs: 0`、`fadeOutMs: 0`；每幕用 `durationFrames` 对齐音频。
8. **渲染链路**：仍不读取 `refs/`；只读取作品目录内已提取的 WAV。

## 目录与文件

```text
refs/douyin/<awemeId>/video.mp4          # 参考素材，内容目录，不入库
videos/general/<slug>/assets/audio/
  <name>.wav                             # PCM16 / 48 kHz / 源声道
  <name>.provenance.json                 # 来源、摘要、授权与许可状态
```

`--name` 默认 `ref-<awemeId>`。名称只允许字母数字与 `._-`，拒绝路径分隔符、`..`、Windows 保留名与已带 `.wav` / `.provenance.json` 后缀的输入；目标固定落在 `assets/audio/`。

## 规格边界

主规格的默认禁令保留：参考素材只用于分析、比对与制作参考，渲染链路不得直接使用 `refs/`。新增例外只覆盖「用户明确指定复用单条参考作品音频」：必须先提取到作品目录、写入 provenance，并只在作品内使用；参考画面仍不得进入成片。例外不扩展为默认能力。

## 取舍

- **不做外部音频母版直通**：现有母版会重采样为 24 kHz 单声道、经 `alimiter`/`acompressor`/`loudnorm` 到 −14 LUFS / −1 dBTP，再编码为 AAC 44.1 kHz。要比特级原样需要另立契约，影响所有作品的准备指纹；本变更不做。
- **不复制 AAC 原样**：AAC 原样复制虽然文件小，但时长依赖容器与 edit list，`wave` 读不了，分析还要再解码；PCM WAV 让时长、帧数与摘要都可直接复核。
- **不把音频提取塞进渲染引擎**：`reference/audio.py` 独立实现，避免修改进入 `implementation_digest()` 的模块，导致全部已有作品准备失效。
- **不自动加载或播放音轨**：场景代码不读取 `assets/audio/`，声音只经统一母版轨进入成片。

## 失败与边界

- 参考目录缺失、被替换、摘要不符：提取前失败，不写任何音频。
- 参考为图文作品、视频没有音频流、作品不是 `general`：失败并说明原因。
- 目标存在且来源/摘要不一致：失败并提示 `--force`；`--force` 同时替换 WAV 与 provenance。
- 提取过程中失败：删除临时文件，不留下 `.partial-*`。
- 版权：provenance 只记录「用户明确指定复用、未取得书面许可」，不把授权表述为许可；成片只保留一处署名。第三方音乐/声音权利状态如实写未知。
