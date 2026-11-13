## 背景

`tts.py` 目前把 edge-tts 写死在解析、合成、缓存键和错误处理里；作品运行时（`film_runtime`）与主项目 `src/m2v` 是镜像实现，作品准备由本地运行时执行。新增后端必须同时改镜像、模板依赖、模型恢复与文档，不能只改主项目。

## 决策

### 1. 后端作为作品属性，默认仍是 edge-tts

`tts.backend` 接受 `edge-tts` 与 `kokoro`，省略时为 `edge-tts`。音色格式由后端决定：edge 保持 `zh-CN-XxxNeural`，Kokoro 使用 `z[fm]_NNN`。命令行新增 `--backend`，优先级为「命令行 > 作品配置 > 默认」。无旁白作品仍不要求选音。

### 2. Kokoro 直接使用模型时长预测生成时间戳

`KModel.forward_with_tokens` 返回每个输入音素的 `pred_dur`；中文前端 `ZHFrontend` 返回带文本的 token。调用 `KPipeline.join_timestamps(tokens, pred_dur)` 可得到秒级词边界。实测 8/8 段单调、覆盖音频 97–99%，21 条字幕与现有 edge 结果条数一致，现有 `rhythm.plan/reshape` 可直接使用。

没有采用：
- WhisperX / MFA：引入第二套模型与转写，中文转写文本常与原文不等，现有 `_walk_words` 要求 token 是原文子串，会误判或不稳定。
- 字符比例估算：现有契约明确禁止猜测字幕时间。
- kokoro-onnx：不暴露 `pred_dur`，拿不到时间戳。

风险是依赖 `ZHFrontend` 与 `join_timestamps` 的内部接口。以精确版本锁定，并在测试中固定一句话的 token 数与时间戳范围；升级 Kokoro/misaki 时必须重新验证。

### 3. 确定性由显式种子保证

ISTFTNet 使用 `torch.rand/randn`，不设种子时两次合成峰差可达 0.087。每次合成前以 `sha256(seedVersion|voice|speed|text)` 派生 32 位种子并 `torch.manual_seed`，实测跨进程逐位一致。种子策略进入缓存键的生成器版本。

### 4. 输入限制失败前置

中文前端的数字会被 `cn2an` 改写，拉丁字母由独立英文 G2P 处理且没有 token 时间戳，两者都无法把 token 映射回原文。当前版本在合成前拒绝 `[0-9０-９]` 与 `[A-Za-z]`，报错要求改写旁白或改用 edge-tts。不支持时明确失败，不退化估算。

### 5. 模型权重走作品内恢复，不进入 Git

新增 `models/registry.json`：固定 repo、revision、模型/config/音色文件的大小与 SHA256，登记 Apache-2.0 许可。`models/fetch.py` 从 Hugging Face（支持 `HF_ENDPOINT` 镜像）恢复，校验摘要，拒绝覆盖漂移文件；`--check` 供 validate/准备前检查。模型与音色文件放入 `models/files/`，由 `.gitignore` 排除。

### 6. 依赖可选，作品自包含

Kokoro 依赖（`kokoro`、`misaki[zh]`）在同一锁文件中声明为可选依赖，Kokoro 作品显式安装；模板保留 extra 说明。主项目与模板镜像同步，作品运行时复制同一实现。非 Kokoro 作品不安装 torch。

### 7. 本片重制的约束

`zf_027` 在 speed 1.0 时旁白总长 45.65s（现有 edge 37.90s），1.2 时 39.52s；套现有停顿整形后为 34.00s。场景素材覆盖检查要求 `startSeconds + 幕长` 不超过素材时长；1.0 会让 thesis/turn/action 超出可用段，且成片超过 43.5s 音床。采用 `+20%`（speed 1.2），预计成片约 39.5s，八段素材与音床均有余量。

## 复现与验证

- 后端校验：非法音色、后端与音色不匹配、数字/英文旁白在合成前失败。
- 确定性与时间戳：同一文本两次合成的 PCM 摘要一致；时间戳单调、覆盖原文、落在音频内。
- 缓存：切换后端不命中旧缓存；准备记录与溯源包含实际后端。
- 恢复：删除 `models/files/` 后 validate 失败、`fetch.py --download` 可恢复且摘要一致。
- 本片：重新准备后跑 validate、QA、全片渲染与独立终审，核对时长、字幕、素材覆盖与音床。
