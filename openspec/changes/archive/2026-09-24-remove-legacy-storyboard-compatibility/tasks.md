## 1. 契约、运行时与清理
- [x] 1.1 将 Python/TS 根 schema 固定为 v3，强制 directingVersion、directingBrief、visualDirection、keynote preset。
- [x] 1.2 强制 renderer、完整视觉论证、camera.segments、非首幕 transition；有口播强制 narrationSegments + beats，拒绝 narration。
- [x] 1.3 移除 startFrame 动效输入，强制 phase/beatId；多目标必须 targets + stagger；统一消费解析 beat 时间轴并检查稳定结尾。
- [x] 1.4 统一预览、评审、渲染对 v1/v2 的明确拒绝；删除缺省 renderer、movement、旧口播与旧 motion 分支。
- [x] 1.5 删除迁移脚本、迁移模块、迁移旧规格与过期测试；保留媒体溯源只读诊断。
- [x] 1.6 补 Python 和 Web 测试：旧版本、字符串口播、缺 renderer/directing 字段、startFrame 拒绝，以及 v3 镜头/动作/稳定收束。

## 2. 内容与文档
- [x] 2.1 按 v3 重编复利作品和 7 个示例，保留教学目标并完整声明导演逻辑。
- [x] 2.2 更新 README、项目计划、Skill 与 schema、渲染、视觉规范和生成参考，清除兼容描述。
- [x] 2.3 删除 3 个忽略 outputs 目录中的旧产物并重建评审材料及成片。
- [x] 2.4 溯源指纹按作品绑定可达代码场景源文件，排除全局易变的生成索引，并确认八份作品状态均为 current。

## 3. 验收与收尾
- [x] 3.1 8 份作品严格校验零错误零警告，完成配音准备及 review，记录人工 V6/A6 裁决且所有硬闸门通过。
- [x] 3.2 运行完整 pytest、Vitest、TypeScript typecheck 和生产构建。
- [x] 3.3 完整解码所有输出并核对分辨率、帧率、视频像素格式/色彩参数、音频参数；抽查各幕、beat 边界、转场、末帧和复利动作。
- [x] 3.4 完成代码质量复审；检查暂存仅包含本次受版本控制改动，排除媒体、缓存、依赖和其他既有改动。
- [x] 3.5 同步主规格并归档 OpenSpec 变更，提交全部受版本控制改动并报告 commit、验证结果、风险和质量评分。
