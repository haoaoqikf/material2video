# 本地配音模型

本目录登记 Kokoro 中文配音所需模型与音色，二进制位于 `files/`，不进入 Git。

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

`registry.json` 是文件清单、大小与 SHA256 的唯一来源；恢复拒绝覆盖摘要不符的已有文件。可通过 `M2V_TTS_CACHE` 提供离线缓存，通过 `HF_ENDPOINT` 指定 Hugging Face 镜像。

仓库卡面标注 Apache-2.0；音色的训练数据来源未在卡面逐项列出。对外发布前仍应按素材台账记录实际使用的音色与许可依据，不把模型许可自动等同于所有训练数据的再分发许可。
