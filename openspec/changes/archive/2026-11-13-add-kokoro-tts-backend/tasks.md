## 1. 规格与文档

- [x] 1.1 完成提案、设计与三份规格增量，明确后端、确定性、时间戳、模型恢复与输入限制。
- [x] 1.2 更新 `prepared-and-subtitles.md`、`voice-and-rhythm.md`、模板 README 与主 README 的当前能力说明。

## 2. 共享后端实现

- [x] 2.1 `tts.py` 支持 `backend` 解析、按后端校验音色、`--backend` 覆盖、后端参与缓存键与准备记录。
- [x] 2.2 新增 Kokoro 合成模块：固定 revision、种子派生、中文 token 时间戳、PCM16 输出、数字/英文前置失败。
- [x] 2.3 `explainer_prepare` 传递后端与模型目录；准备记录与溯源保存实际后端。
- [x] 2.4 `m2v voices` 支持按后端查询音色。

## 3. 模板与恢复

- [x] 3.1 模板与 `src/m2v` 镜像同步，作品运行时复制同一实现。
- [x] 3.2 模板、主项目与 Kokoro 作品声明可选依赖并更新锁文件。
- [x] 3.3 新增 `models/registry.json`、`models/fetch.py` 与许可，setup/validate 接入恢复与检查。
- [x] 3.4 更新 `.gitignore`，模型二进制不入库。

## 4. 本片重制

- [x] 4.1 `stop-living-for-others` 声明 `backend=kokoro`、`voice=zf_027`、`rate=+20%` 并更新选择记录。
- [x] 4.2 恢复模型并在作品内安装依赖，重新 prepare 与 validate。
- [x] 4.3 技术 QA、全片导出与独立终审；核对时长、字幕、素材覆盖与音床。

## 5. 验证与归档

- [x] 5.1 运行后端校验、确定性、时间戳、缓存隔离与恢复相关测试。
- [x] 5.2 检查暂存内容，提交实现与文档。
- [x] 5.3 同步主规格并归档变更。
