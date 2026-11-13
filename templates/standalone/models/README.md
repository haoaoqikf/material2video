# 本地配音模型

本目录登记本地配音后端所需模型，二进制位于 `files/`，不进入 Git。

## Kokoro

- 模型：`hexgrad/Kokoro-82M-v1.1-zh`
- revision：`01e7505bd6a7a2ac4975463114c3a7650a9f7218`
- 许可：Apache-2.0，文本见 `licenses/Apache-2.0.txt`
- 内容：`kokoro-v1_1-zh.pth`、`config.json`，以及 `voices/` 下的中文音色
- 来源：<https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh>

恢复与校验：

```powershell
python models/fetch.py --download --voice zf_027
python models/fetch.py --check --voice zf_027
```

## Qwen3-TTS 声音克隆

- 模型：`Qwen/Qwen3-TTS-12Hz-0.6B-Base`
- revision：`7ee3cf0b7e7be29c5d8de06cd552b78263f01ece`
- 许可：Apache-2.0，文本见 `qwen3-tts/licenses/Apache-2.0.txt`
- 对齐模型：`Systran/faster-whisper-small`
- 对齐模型 revision：`536b0662742c02347bc0e980a01041f333bce120`
- 对齐模型许可：MIT，文本见 `qwen3-tts/licenses/MIT.txt`
- 内容：主权重、config、tokenizer、speech tokenizer，以及 stable-ts 对齐模型
- 来源：<https://modelscope.cn/models/Qwen/Qwen3-TTS-12Hz-0.6B-Base>

恢复与校验：

```powershell
python models/qwen3-tts/fetch.py --download --voice clone_<slug>
python models/qwen3-tts/fetch.py --check --voice clone_<slug>
```

`qwen3-tts/registry.json` 还登记参考音色档案：参考音频、参考文本、语言、大小与 SHA256，以及来源和用户授权原文。参考音色是作品资产，不能从模型仓库恢复；更换参考音频或参考文本会改变语音缓存键与准备指纹。

`registry.json` 与 `qwen3-tts/registry.json` 是文件清单、大小与 SHA256 的唯一来源；恢复拒绝覆盖摘要不符的已有文件。可通过 `M2V_TTS_CACHE` 提供离线缓存，Qwen 文件支持 `MODELSCOPE_ENDPOINT`，对齐模型支持 `HF_ENDPOINT`。

仓库卡面标注 Apache-2.0 / MIT；训练数据来源未在卡面逐项列出。对外发布前仍应按素材台账记录实际使用的音色与许可依据，不把模型许可自动等同于所有训练数据的再分发许可。参考视频音色只用于本作品，用户要求不等于原作者许可。
