## 1. 研究与设计模板

- [x] 1.1 在 `stage-research.md` 保持阅读预算内的入口表述，并把五维决策与静态推导写入 `reference-video-analysis.md` 的研究记录要求。
- [x] 1.2 在 `reference-video-analysis.md` 增加“只有静帧时的推导”方法、映射表与可量测验证指标。
- [x] 1.3 在 `stage-design.md` 增加逐场“时间节拍、镜头/运动、入出转场、声音、可量测预期”表，以及转场语法、变化密度、静止理由和技术代价说明。
- [x] 1.4 在 `visual-expression-inspiration.md` 的使用原则中补充静态推导与五维决策。

## 2. 评审证据与文档清理

- [x] 2.1 改写 `visual-review-rubric.md`、`subagent-review.md`、`review-contract.md`：评审以有序帧、解码、帧差/切分、主体量测和音频信号为证据；删除播放/试听前提。
- [x] 2.2 改写 `stage-production.md`、`material-sourcing.md`、`visual-material-selection.md`、`article-media-and-sound.md`、`voice-and-rhythm.md`、`SKILL.md`、`README.md` 中把播放/试听作为验收前提的表述。
- [x] 2.3 同步修改 `openspec/specs/` 下受影响能力：灵感五维、静态推导、评审证据、代理证据边界、全片内部检查。

## 3. 验证与提交

- [x] 3.1 运行文档投影、相对链接、JSON/表格结构与相关测试节点；检查五维、可量测预期与“无播放/试听前提”表述一致。
- [x] 3.2 检查暂存内容，提交实施；完成后同步主规格、归档变更并提交归档结果。

## 验证记录

- `sync_docs.py --check`：通过；阅读预算 entry=1657、research=2997、design=1889、production=942。
- `pytest tests/common/test_guidance_routes.py`：通过。
- `pytest tests/common/test_production_sources.py`：通过。
- `openspec validate land-audiovisual-dimensions --strict`：通过。
- 作品内容未修改；未重建视频、未重制试制片。
