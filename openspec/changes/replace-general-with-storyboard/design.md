## 方案

删除旧通用适配器，把原 article 模块移为 general；目录登记的 general 仅含 storyboard.json 模板。统一辅助命令为 m2v general，拒绝旧类型和旧 plan 材料。讲解 composition 的内部名称保留 ArticleExplainer，避免无关视觉重写。

删除旧 GeneralVideo composition 与专属代码场景 API、清单、闸门、构建别名。共享 Remotion 构建、静态源码确定性检查、字体、缓存和媒体验收继续使用；构建指纹不再依赖作品代码清单。

同步所有活动规格的类型名称与命令，替换通用编排规格并移除代码场景规格。历史归档不改。三个固定示例仅更新身份与引用，不增删示例。

## 本地材料

核实旧 general 目录的绝对路径与子目录后删除，移动 article-narrative 目录为 general；更新非派生 JSON/文本中的类型和路径，保留原分镜版本和媒体。旧 outputs 保留为历史产物，准备指纹中的类型及构建输入变化使其失效，必须重新 prepare 与完整 preview。

## 验证

新增类型替换与旧契约拒绝回归；保留 v6 模板、媒体篡改、TTS、字幕、主题和浏览器布局测试。执行 Python 测试、前端测试/类型检查/构建、文档同步检查和 OpenSpec 严格校验。审查通过提交实现，再同步主规格、验证归档并提交。
