# 完成审计

本记录对应任务 6.4：对照规格、命令、七例矩阵与清理台账逐项核对。

## 规格与命令

- `openspec validate make-video-projects-standalone --strict` 通过。
- `project.json` v3、`contractVersion=3`、本地执行协议、相对候选路径、作品输入绑定与旧契约拒绝由 `tests/standalone/` 与 `tests/works/examples/` 覆盖。
- `setup/validate/prepare/build/preview/render/qa/sample/inspect/lookdev/materialize` 均可在作品目录直接执行；`m2v validate/prepare/preview/render/qa` 委托本地入口，`lookdev` 与 `review timeline` 读取本地产物。
- 无字体时 `validate` 返回非零；坏摘要、缺媒体、越界路径、父目录参数与目录/文件链接均明确失败。
- 七例矩阵全部完成：资源恢复、构建、准备、完整导出与本地 QA 通过；代表帧实际查看。摘要与帧数见[示例记录](implementation-examples.md)。
- 清理台账逐项标注实际处置；公开 SDK 入口、全局依赖登记与仓库场景映射已删除，保留的 `web/` 源码与旧 Python 模块明确为参考/测试对象，不进入作品运行。
- 独立审查最终无必改项，评分 94/100；审查与修复过程见[审查记录](implementation-review.md)。

## 提交范围

- 包含主项目代码、模板、七例源码与脚手架、测试、文档与 OpenSpec 变更材料。
- 排除 `node_modules/`、`.venv/`、`outputs/`、字体与媒体二进制、依赖缓存、实验日志与生成视频。
- 新增代码与交付文档纳入 Git；`web/` 删除项已暂存；未发现凭据、令牌或真实个人配置。

## 未覆盖边界

- 未运行全仓完整回归；按影响范围运行独立工程、示例结构、前端参考、来源能力、评审/交付边界与修复相关节点。
- POSIX 进程树、跨 GPU 逐字节一致性、真实主项目越界写入与主观听感/美术评审不在本轮验证范围。
