# 文档冲突核对

核对范围为当前 Skill 及参考文档、README、规划、风格包和教学示例说明、当前 OpenSpec 主规格；不将历史归档或作品专属约定转成通用要求。下表路径中的参考页位于 `.agents/skills/material2video/references/`。

| 冲突位置 | 采用依据 | 统一结论与修复位置 |
|---|---|---|
| creative-production / visual-creative-direction / production-workflow 仍固定三案、两方向或三机制；主规格多处相反 | 已归档 simplify-general-production-review；当前主规格“通用制作必须…”选案条款、风险策略 | 按未决问题比较实质不同方案；用户方案充分时直接采用；同步上述参考页、素材选择页和主规格六个相关要求 |
| G5 内部观察却被要求登记独立身份、隔离或盲看 | workflow.py 的 G5 internal；独立评审主规格 | director-review-and-edit 区分 G5 内部记录与 G6 独立凭据、观察顺序 |
| 场景观察只要作者执行就一律未完成 | checkpoint-based-visual-acceptance 的普通 G4 / G5 覆盖边界 | 主规格场景限定到适用核心独立观察和 G6；creative-production 的复述检查不逐幕派审 |
| 两问限于第二次独立审查，与 G5 可选诊断相反；答不出唯一画面即否决 | 当前流程及诊断主规格 | director-review-and-edit 允许 G5/G6 按问题使用，只有实际视觉核心缺失才按证据返工 |
| 终检表将回场、连续运动、每句单行和先停后读写成通用门槛 | explainer-visual-diagnosis 的分类诊断边界；屏幕字幕与共享字幕分别契约 | stage-final 按用途与字幕类型检查，保留核心理解和必要可读性；抽五处不能代替全片覆盖 |
| qa 等按需工具与唯一命令/强制预先检查混淆 | 主规格全片采样及现行工具非渲染前置原则 | director-review-and-edit / visual-review-rubric 保留采样密度、分页与风险加密，允许复用或同覆盖取证；完整证据仍是完成条件 |
| 禁止外部逐字字幕与现有重写组件混淆 | 有旁白共享字幕互斥；无旁白 screenSubtitles 组件契约 | 外部指南明确不覆盖共享字幕；允许现有无旁白组件，许可限制不变 |
| “未来合并”已完成；规划将已吸收镜头方法仍写为待评估；传播预估标题与正文相反 | 当前风格目录、README、主规格正文 | 更新外部指南标题和规划；主规格改名为实际传播表现评估，不新增报告或播放量承诺 |
| 固定片尾署名/版权说明与画面注释从紧相反 | AGENTS.md 画面注释、许可和发布说明约定 | creative-production / stage-final 保留必要素材署名，取消默认制作说明，不减许可义务 |
| prepared-and-subtitles 仍宣称仅口播决定时长、固定 24 帧及统一混 AAC | explainer_prepare.py 的 600 × fps、durationFrames / targetSeconds / readingHoldFrames；无声音轨契约 | 准备说明改为实际时间轴、默认 0.8 秒可配置停留，区分内部静音母版与无声交付 |
| 文档链接测试仍读取已删除 article-to-storyboard | 当前 stage-plan 入口与阅读路由 | test_doc_examples.py 更新到实际入口，保留结构可达性检查，不添加措辞黑名单 |

## 保持不变的边界

- repeated-failure 仍要求至少两个实质不同的匿名候选，实质争议仍由新代理复核；候选数量放宽不豁免这些风险。
- 复利作品的独立粗片等专属要求，以及 traffic-jam-wave 的历史重制要求保留；不迁移或补签旧作品。
- 动态核心事件的完整过程片段、当前候选绑定、独立失败原条件复查、全部必改关闭和全片采样覆盖保持不变。
- 不修改渲染器、CLI、schema、评审人数策略或作品材料；不将本次文档核对宣称为成片审美验证。
