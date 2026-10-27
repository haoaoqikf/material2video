## 1. 规范与文档

- [x] 1.1 更新 `AGENTS.md` 的注释条目：示意/实拍边界标注改为大屏可辨、手机横屏不可辨；必要口径、署名与其他注释仍须可读
- [x] 1.2 同步 `.agents/skills/material2video/SKILL.md` 与 `references/production-workflow.md`、`video-revision.md`、`visual-review-rubric.md`、`visual-material-selection.md`、`subagent-review.md`
- [x] 1.3 全量搜索「手机可读 / 仍须可读 / 缩到不可读 / 缩小字号」，确认无旧口径残留

## 2. 作品重制

- [x] 2.1 建候选基线保护旧片（SHA-256 `fdb017ea…`）
- [x] 2.2 `scenes/common.tsx` 注释与英伟达幕末两行署名都改 20px `#5f6970`；开场标题改为「美国市值最高的十大公司」，同步分镜、DESIGN、CREDITS 与生成脚本；市值行与开场副标题不动
- [x] 2.3 `DESIGN.md` 更新注释说明、合同 `textPlan` 标题并补「重制启动」记录
- [x] 2.4 `m2v validate`、`prepare`、局部抽查 1920/852/393 后 `render`、`qa`

## 3. 门禁与独立评审

- [x] 3.1 复核 G0/G1/G3（标题改动触及合同 textPlan），重跑全部 11 个 G4 检查点
- [x] 3.2 核心轮：重建 cp-apple/cp-nvidia 评审包，新代理评审并导入
- [x] 3.3 粗片轮：重建 G5 报告与全片包，新代理评审并导入
- [x] 3.4 终审：重建 G6 报告与全片包，未参与前期评审的新代理终审并导入
- [x] 3.5 `gates rebuild` 后 `m2v status` 全部通过，无过期证据

## 4. 问题表与记录

- [x] 4.1 用新证据重新关闭 12 项问题，复核 V-RANKING-01 的关闭理由
- [x] 4.2 `visual-notes.md` 追加本轮记录与 852/393 实测

## 5. 交付与归档

- [x] 5.1 `openspec validate --specs --strict` 通过
- [x] 5.2 提交仓库内改动（规范文档与变更材料）
- [ ] 5.3 归档变更并同步主规格，提交归档结果
