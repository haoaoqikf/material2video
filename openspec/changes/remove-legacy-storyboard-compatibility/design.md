## 背景与现状
现有 schema v2 已具备导演简报、逐幕视觉论证和 narrationSegments，但这些字段仍有可选路径。motion 支持绝对 startFrame，camera 同时允许 movement 与可选 segments；renderer 可省略并默认 tree；根视觉策略和导演信息可缺省。Python 与 TS 还有字符串 narration、缺 beat、迁移代码等历史分支。跨层运行时可能接受不同输入集合。

## 设计

### 唯一契约
根版本号与 schemaVersion 固定为 3。directingVersion 固定为 1，directingBrief、完整 visualDirection 与 visual.preset=keynote 必填。每幕必须有 renderer、完整 visualIntent 和 camera.segments。第二幕起必须显式声明 transition。静音幕可以不带 narrationSegments；有口播则只允许非空 narrationSegments，并要求 beats 按语义段绑定。字符串 narration 一律拒绝。

每条 motion 必须绑定 phase 或 beatId，禁止 startFrame；单目标使用 target，多目标使用 targets 并配套 stagger。解析后的 beat 时间轴作为共同时间真源供口播、字幕、镜头、动作、审阅复用，且场景尾部保留稳定阅读区。

### 一致拒绝与错误
Python 校验器、TypeScript schema、契约页入口、composition、review 和渲染编排都调用同一语义规则：缺版本或版本小于 3 时停止处理并给出具体“不支持 v3 之前分镜”信息。未知旧字段不得被 strip 后继续渲染。移除旧 renderer 默认、旧 movement 镜头规划、绝对帧动效和字符串口播支持。历史成片 manifest 只读识别不属于分镜执行兼容。

### 内容重编与媒体重建
逐一重写目标作品与七例的导演简报、visualDirection、逐幕视觉意图、镜头段、transition、narrationSegments/beats、renderer 和阶段动作。保留示例的教学目标。复利作品需让投入、复利增长、反馈闭环及跨幕对象根据口播推进，而非静态镜头下微调曲线。删除 3 个仓库 outputs 目录后逐个严格校验、配音准备、视觉评审、人工填写 V6/A6，再完整渲染；产物仍遵守 ignore 规则。

### 文档与归档
更新 README、项目计划（如现状/路线受影响）、Skill 及 schema/render/visual/生成参考。删除 migrate_storyboard.py、a2v.migration 与迁移专用文档/规格。完成后将 delta spec 同步为主规格并归档变更。

### 作品溯源稳定性
媒体指纹须按具体分镜遍历可达代码场景源文件，不将全局 `.gen/active-scenes.ts`、`.gen/scene-manifest.json` 或 `.gen/active-tailwind.css` 等由其他作品重写的派生索引当作输入。这样逐一生成八份作品后，之前完成的产物仍能对照其自身有效输入判定为 current。

## 风险和缓解
- 一次性拒绝 v1/v2 会中断旧内容：仓库目标作品全部重编，新错误明确要求按 v3 重写。
- 完整重渲染耗时且依赖 TTS、浏览器、ffmpeg：按内容顺序分批运行，保存日志和审阅结果，单项失败先修复再继续。
- v3 跨 Python/TS 的规则漂移：加入镜像拒绝测试与时间轴测试，完整运行 Python 与 Web 验证。
- 忽略文件删除后不可从仓库恢复：用户已明确要求彻底删除旧 outputs 并重建；重建产物不提交。
