## Why

通用类型（`general`）的配音是**裸露的 TTS 干声**：`general/adapter.py` 的 `_mux_audio` 只把每个场景的旁白轨 `adelay` 后 `amix`，没有任何音乐或环境音层。对 90 秒口播片实测，这会把 TTS 本身的机械感全部暴露出来——没有底噪、没有空间感、每段之间是精确到毫秒的静音硬拼。

同一仓库的 `article-narrative` 类型早已具备 `soundtrack.music`、闪避式混音与素材摘要能力（`engine/sound.py`、`engine/audio.py`），通用类型却用不上，导致「有配乐能力但通用片拿不到」。同时发现一个既存缺陷：通用类型的成片音轨被编码成 **24kHz 单声道 AAC**，而项目交付契约要求 44.1kHz 立体声（原因见渲染契约：24kHz 单声道 AAC 会被 Windows Media Foundation 拒绝打开）。

## What Changes

- 通用计划支持可选 `soundtrack.music`：本地相对路径音床、增益、循环与淡入淡出，校验复用共享的声音契约。
- 有音床时先拼出整片旁白再闪避混音，音轨以**单条母版轨**落到起点，不再逐场景 `adelay`。
- 通用成片音轨改为 **AAC-LC / 44.1kHz / 立体声 / 128k**，与文章类型统一交付规格。
- 通用类型**不支持** `soundtrack.effects`：场景没有 beat 轴，给不出音效起点锚点，显式失败而不是猜一个位置。
- Skill 参考文档记录通用片音床的素材要求与「原创合成、无第三方采样」的既有做法。
- 本作品 `china-ancient-population` 声明音床并重新准备、预演、评审与渲染。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `general-video-composition`: 通用片新增受控音床，混音改为整片单条母版轨，成片音轨统一为 44.1kHz 立体声 AAC-LC。

## Impact

- 影响 `src/m2v/engine/sound.py`（校验函数区分场景结构）、`src/m2v/types/general/adapter.py`（计划校验、准备与混音、成片编码）、`tests/test_general_video.py`。
- 同步更新 Skill 参考文档：`references/media-contract.md`、`references/render-contract.md`。
- 本作品目录属于被忽略的内容目录，`general-plan.json`、音床素材与 MP4 不加入 Git；音床生成器随作品保留在内容目录，可复制的做法记录在 Skill 参考文档。
- 现有通用作品若无 `soundtrack`，准备记录与产物不变；成片音轨编码规格变化会使旧成片的字节不再可复现，需要重新渲染才能对齐。
