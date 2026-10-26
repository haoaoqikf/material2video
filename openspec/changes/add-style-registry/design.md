## Context

参见 proposal.md。作品和准备契约位于 core，general 场景使用受限打包和离线受控时钟录制。

## Goals / Non-Goals

目标：风格独立注册，作品显式绑定，general 显式使用表现资源，依赖变化可检测。
非目标：内置风格、混合继承、自动换肤、旧版本适配、新视频类型及评审变化。

## Decisions

- core/styles.py 从 styles/<id>/style.json 发现风格。schemaVersion=1，ID 与目录一致，version 为语义版本，guide 必填，tokens/components/assets 可选；types 为类型名列表，frames 为宽高列表。core 不依赖类型实现。
- project.style 只允许 id，准备保存时再次验证实际画幅。所有类型支持指导和绑定，general 另有场景接口。
- m2v/style 导出只读参数和身份；m2v/style/components/<name> 与 m2v/style/assets/<name> 只解析登记入口。Python 校验后传给打包器，避免两份清单解释规则。
- 包内相对导入不得越界，继续限定既有批准依赖；路径规范化检查符号链接。资产必须有来源许可。
- 全包文件摘要绑定准备与场景缓存，O(包字节数)，不进入逐帧热路径。未选风格不新增准备字段。
- GUIDE 由助手读取并落实到 DESIGN.md，不被渲染器执行。项目强制约束、用户要求、作品显式调整优先于包默认。

## Risks / Trade-offs

- [全包哈希增加 I/O] → 仅处理选中包，包应只存放交付资源。
- [文档无法自动保证审美] → 明确显式接入，沿用现有独立评审。
- [工作区已有重叠改动] → 保留基线，按任务增量暂存，不夹带其他工作。

## Migration Plan

存量作品无需声明风格，初始注册目录为空。无新依赖或迁移工具。
