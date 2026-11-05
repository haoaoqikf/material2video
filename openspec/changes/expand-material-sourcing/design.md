## Context

见 proposal.md。现有导入与媒体探测链路成熟，采用字段需要在导入、resolve、report、audit 间共享判据；本变更涉及这些模块，故需要设计记录。

## Goals / Non-Goals

以对象和素材缺口指导助手检索，官网与官方账号通过现有公开直链或本地文件导入。增加可追溯采用信息，不开发全网搜索 API、通用爬虫或新的音频、字体、地图授权规则。

## Decisions

- `core/media_policy.py` 提供纯数据规范化、采用判定与警告，供三条画面检查路径复用。不解析自然语言许可证为法律结论，不用未知许可代替明确禁止。
- schemaVersion 继续为 1，新增可选字段 sourceType、publisher、description、usableSegment、usage。缺省 usage 规范化为 not-checked 并提示；不建立版本兼容分支或迁移工具。已检查状态必须有 HTTP(S) evidenceUrl、ISO 日期 checkedAt 和非空 note；conditional 还需布尔 conditionsMet。prohibited 无需完善证据才能阻断。
- 明确禁止与条件未满足可以先导入留证，但 resolve/report/audit 阻断采用。not-checked/许可未知只提示；制作助手采用前继续核查，不自动推断授权。记录变化随既有来源记录摘要使准备过期。
- 来源元数据与候选采用统一字段；usableSegment 是检查窗口，当前不裁切或渲染。实际播放仍由场景代码控制。
- Pixabay 请求取消图片硬方向参数，所有候选按方向匹配稳定排序；仍只发一次每种媒体查询，缓存继续 24 小时。
- 外部方案评估：复用现有 urllib Transport、Pixabay 适配器、ffmpeg 探测和 yt-dlp 参考获取；SPDX 表达式适合描述已知许可，不能表达本次用途下的未发现限制，故采用少量纯数据政策字段，不引入许可证分析库或爬虫依赖。参考 https://github.com/spdx/spdx-spec/blob/develop/docs/annexes/spdx-license-expressions.md 与 https://github.com/yt-dlp/yt-dlp 。不改动参考作品默认不入片的边界。

## Risks / Trade-offs

- 未发现明确禁止不等于获得法律授权 → 保存原始许可、条款依据和本次用途，提示不代表授权；不伪造检查证据。
- 不再用未知许可硬拦截后，未核实项可通过技术准备 → 日志与报告明确警告，制作指南要求采用前检查，不额外增加用户确认。
- 不限制方向后候选可能更杂 → 按方向排序，实际裁切由助手判断。
- 仅首帧探测不能证明全片完整 → 保留既有候选窗口与最终媒体复核要求。

## Migration Plan

无需版本升级或迁移。导入新清单可补元数据；现有记录缺省状态显示未核实。更新共享指南与规范示例格式，不虚构对历史来源的新检查。执行针对性离线与相关真实媒体节点测试，独立评审后提交；任务完成后同步主规格并归档。
