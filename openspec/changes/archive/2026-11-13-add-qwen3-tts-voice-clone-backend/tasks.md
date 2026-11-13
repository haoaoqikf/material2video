## 1. 规格与文档

- [x] 1.1 完成提案、设计与三份规格增量，明确后端、参考音色、模型恢复、确定性、强制对齐与失败行为。
- [x] 1.2 更新 `prepared-and-subtitles.md`、`voice-and-rhythm.md`、模板 README 与主 README 的当前能力说明。

## 2. 共享后端实现

- [x] 2.1 `tts.py` 支持 `qwen3-tts` 后端解析、`clone_<slug>` 音色校验、`--backend` 覆盖、缓存键与准备记录。
- [x] 2.2 新增 `qwen3_tts.py`：模型/参考音色/对齐模型校验、固定种子、变速、按原文强制对齐、零时长修复、PCM16 输出。
- [x] 2.3 `explainer_prepare` 传递后端与模型目录；实现摘要纳入新模块；准备记录与溯源保存实际后端、参考音频摘要与对齐模型 revision。
- [x] 2.4 `m2v voices` 与作品运行时 CLI 支持按后端查询/校验；`--backend` 选项加入 `qwen3-tts`。

## 3. 模板与恢复

- [x] 3.1 模板与 `src/m2v` 镜像同步，新作品运行时复制同一实现。
- [x] 3.2 模板与作品声明 Qwen3-TTS/stable-ts 可选依赖并更新锁文件。
- [x] 3.3 新增 `models/qwen3-tts/registry.json`、`models/qwen3-tts/fetch.py` 与许可；setup/validate 接入恢复与检查。
- [x] 3.4 确认 `models/files/` 被忽略，模型二进制不入库。

## 4. 新作品重制

- [x] 4.1 复制 `stop-living-for-others` 到 `stop-living-for-others-clone`，保留原目录；更新作品 id 与 `tts.backend/voice/rate/selection`。
- [x] 4.2 登记参考音频（60–68 秒）、参考文本、来源与用户授权；恢复模型与对齐模型并安装依赖。
- [x] 4.3 重新 prepare 与 validate；核对旁白时长、字幕、音床与素材覆盖。
- [x] 4.4 技术 QA 与全片导出完成；带参考媒体的独立终审因用户叫停未完成（未报告制作完成）；未覆盖项记录在作品 DESIGN.md 与 outputs/visual-notes.md。

## 5. 验证与归档

- [x] 5.1 运行后端校验、缓存隔离、参考音色摘要、零时长修复、确定性相关测试。
- [x] 5.2 检查暂存内容，提交实现与文档。
- [x] 5.3 同步主规格并归档变更。

> 归档说明（2026-11-13）：新作品已渲染并通过技术 QA；带参考媒体的独立终审在用户叫停时未完成，未报告制作完成。原作品目录、成片与未完成评审记录保留。
