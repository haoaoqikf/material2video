## Context

动机见 proposal.md。当前 review v2 的 blind/consistency 强制成对，sample v1 以静帧加视频作为不可拆分范围；已有账本、隔离包、摘要、问题闭环和本地采集可直接复用。

## Goals / Non-Goals

目标：用明确用途拆分静态品质与过程证据；将机械字段自动派生；世界级品质判断留给真实独立观察及总代理。固定保留研究、总设计和逐场文档，缩短默认填写。

边界：不新增风格注册、自动审美打分、工作流服务器或另一套采集链路；不改变分镜和成片格式；不迁移作品内容和旧通过。

## Decisions

1. review v3 的 request 必填 purpose=keyframe/process/final；report 的用途从绑定包派生。关键帧为图片，过程为视频，终审为当前完整候选。新增 reviewType=process，直接提供实际参考和中性条件，不引用 blindId；必要过程盲审用 blindReason 说明时间机制风险，仍先盲后对照。用途进入问题范围和状态，过程通过不能替代关键帧通过。
2. sample v2 增加 kind=static/motion。static 仅采集选定原生帧及可复现网页，video=null；motion 同源采集视频，关键帧请求只包含图片，另生成完整过程请求。二者均保留输入／产物和实际配置复核。复用本地 _capture 的 selected_frames，顺序模式推进必要前序状态但不编码，不新写截图引擎。
3. 动态样品交付要求关键帧独立双通过和完整过程独立对照通过，静态只要求前者。过程可由直接 process 报告或有具体依据的过程双评证明。源、显示尺寸、目标和原失败范围严格绑定；复制现有产物，不重渲染。试制视觉等价复用继续限同用途、完整字节和相同条件。
4. 生成包时在包外生成 report-template.json 和任务说明，模板结论默认 insufficient、adoption=reject；报告必须填写明确 adoption=adopt/reject，并与 verdict 一致。每项 coverage 同样明确采用结论。机器核对一致性，不用禁词或字符数假装判定审美。真实调用记录继续严格校验。review compare 从当前盲报告自动派生目标包，复制已核验媒体并直读复核封存摘要，保持两包独立，避免重复编码及取帧，sample review 从采集及目标文件自动建包，避免手抄 JSON。
5. 状态只读展示用途与采用结论。所有作品必须有有效关键帧双通过和当前全片新代理终审；短片只免单独过程试制。过程是否覆盖全部创作风险由作者核对，不用一个任意过程报告假装机器认证代表性。
6. 评审政策集中 review-contract.md，风格开放的世界级判断集中 visual-review-rubric.md，隔离方法集中 subagent-review.md，字段与命令集中独立技术协议。阶段入口只引用；场景四问为默认，机制深度和教学演练继续按需保留。总代理的选择和真实问题进入已有文档，不增加审批。
7. 外部方案调研：核对 Python argparse 官方文档（https://docs.python.org/3/library/argparse.html）、Pydantic 模型（https://docs.pydantic.dev/latest/concepts/models/）及 Prefect flows（https://docs.prefect.io/v3/concepts/flows）。本轮是已有媒体绑定协议的自动派生，现有 argparse、JSON 校验、文件锁和账本满足需求；Prefect 的状态／数据库会重复权威记录，Pydantic 全量重写不提高本次目标效果，故不新增依赖。视频创作侧仍明确成熟外部视觉方案优先，并按实际采用登记版本与许可。

## Risks / Trade-offs

- 审美不能由 schema 证明 → 独立真实观察、具体参考、明确结论、总代理核查；工具不声称自动世界级认证。
- 静态误授权动态 → kind、purpose、交付范围及报告绑定分别校验，静态无过程资格。
- 来源／目标漂移和失败绕过 → 保留摘要、安全路径、不可变包、用途范围、同类复查、用户 retarget 及当前周期保护。
- 升级影响旧记录 → 只维护 v3 review/v2 sample，旧记录明确拒绝；新周期保留历史，不提供适配和迁移，不批量修改现有作品。
- 静态采集仍可能推进多帧 → 复用顺序宿主保证状态正确，只保存选定帧且不编码；复杂动态用 motion 验证。

## Migration Plan

先规格后实现，更新共享模板、管理工具、测试夹具和五部示例的制作记录；相关单测及有代表性的真实静态／动态采集通过后独立审查，提交实现。然后同步主规格、归档并提交归档。需要撤回时使用 Git 提交恢复，不转换旧作品材料或旧证据。

## 实施中发现并处理

Windows 初始化与采集目录发布反复出现短暂 WinError 5/32 句柄占用；在主项目、模板和五部示例的目录发布入口加有限重试，只对目标尚不存在的已知占用错误，失败仍抛出，不删除目标、不修改全局权限。以瞬时、永久拒绝和已有目标边界测试验证。
