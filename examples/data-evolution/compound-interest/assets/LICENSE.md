# 原创音效与环境床许可

`synthesize.py` 生成的环境床（bed）与事件音（drop1–3、slide、float、ding、suction、fusion、tingLow、tingHigh、thump、tick、stream、resonance、chime）由 material2video contributors 原创合成，不含第三方采样，按 CC0-1.0 发布。

- `bed.wav` 为 29 秒无旋律持续纹理：前 8 秒是数字静音，8.0 秒起 0.8 秒淡入，28–29 秒淡出；它属于环境床，不是配乐。
- 事件音为确定性的短音；`stream.wav` 是 6 秒颗粒化金属流，不逐枚发声。
- 文件摘要、采样率、声道与时长由 `recipe.json` 固定；`fetch.py` 只恢复并核验，不接受摘要漂移。


## 方案C新增声音

assets/mint_synthesize.py生成mint-bed、mint-contact、mint-grow、mint-return、mint-reveal、mint-close，均为本例原创确定性合成、无第三方采样，按CC0-1.0发布。环境床29秒、8秒起淡入、28至29秒淡出；其余是柔质接触、空气生长、回吸、揭示与归队的短触感声，不组成旋律。每个新身份的摘要见recipe.json；旧配方及旧资产摘要未覆盖。
