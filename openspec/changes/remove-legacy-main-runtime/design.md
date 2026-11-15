## Context

独立工程改造后，`m2v` 的 validate/prepare/preview/render/qa 全部通过 `standalone.executor` 委托作品本地运行时；模板 `templates/standalone/runtime/python/film_runtime/` 已包含完整的准备、采集、渲染、QA 与字体实现。主项目里的同名模块是最初抽出模板时的来源副本，从 `m2v.cli` 出发不可达（见 proposal.md 的 Why）。

现有测试通过 `tests/helpers/scene_film.py` 把 `templates/standalone/runtime/python` 加入 `sys.path`，已经直接导入 `film_runtime` 的 TTS 实现；同一模式可以扩展到其他运行时模块。约束是：不保留生产兼容层，不因删除旧实现而降低对当前契约的覆盖，也不能把作品或模板改成依赖主项目。

## Goals / Non-Goals

**Goals**

- 主项目只保留制作管理所需的 PyPI 代码；渲染与采集实现只存在于模板／作品。
- 对模板运行时行为的测试继续存在，并直接针对 `film_runtime`。
- 旧实现的模块级单元测试随实现删除，不保留“测试专用副本”。
- 文档不再声称主项目保留旧准备／渲染模块。

**Non-Goals**

- 不修改模板运行时的行为、依赖、锁文件或输出契约。
- 不修改 `m2v` 对外命令、材料 schema、评审或交付门禁。
- 不迁移示例作品内部的 `film_runtime` 副本。

## Decisions

### 决策 1：整模块删除，不建立兼容导入

删除的模块不保留转发文件、`__getattr__` 或旧路径别名。项目约定版本升级只维护当前契约；旧实现的代码可在 Git 历史追溯。

替代方案（保留转发模块 + 弃用警告）会让“主项目是否参与渲染”继续含糊，也会把删除成本推给未来。

### 决策 2：测试按“保护对象”分流

- 只验证被删模块内部算法、缓存键或私有辅助函数的测试：随实现删除。
- 验证作品运行时行为的测试（字体覆盖／子集、示例媒体恢复、代码场景采集、准备与交付）：把导入从 `m2v.*` 改为 `film_runtime.*`，保留断言；必要时把 monkeypatch 目标同步改为 `film_runtime` 模块。
- 验证仍在主项目中的校验、素材、评审、命令行为的测试：保持不变。

替换实现对象时不复制测试代码，也不在主项目保留测试夹具副本。

### 决策 3：`code_scenes` 收敛为校验入口

`code_scenes/__init__.py` 只导出 `validate_entry`、`validate_capture`；`config.py` 保留 `capture_settings`、`validate_entry`、`validate_capture` 与常量，删除构建、打包、输入指纹、媒体白名单与源码字面量收集。`explainer.py` 是唯一调用方，接口不变。

### 决策 4：`core/assets.py` 收敛为仓库定位

只保留 `REPOSITORY_ROOT` 与 `BUNDLE_DIR`（`standalone/scaffold.py`、`core/workspace.py` 使用）。`default_mounts`、`mount_key`、`asset_key` 的调用方全部在删除集合内，因此一并删除。

`core/source_policy.py` 的唯一生产调用方是旧构建/渲染链路；删除后它只被测试使用。为避免在主项目保留仅测试使用的生产模块，删除该副本，测试改为导入模板的 `film_runtime.core.source_policy` 继续校验参考源码。

### 决策 5：删除 `fonttools` 运行时依赖

`fonttools` 只被 `core/fonts.py` 使用；模板在自己的 `pyproject.toml` 中声明依赖，主项目删除该模块后同步移除依赖，避免留下未使用的安装面。

## Risks / Trade-offs

- [测试模块被 monkeypatch 到主项目路径，迁移后失效] → 逐个把 patch 目标改为 `film_runtime` 对象；运行受影响的测试文件确认。
- [模板运行时与主项目副本在默认路径/环境上有差异] → 测试只使用临时作品目录与模板副本；真实浏览器节点按 AGENTS.md 单独选择运行。
- [删除测试造成契约覆盖缺口] → 只删除验证旧实现内部细节的用例；材料校验、来源校验、命令行为、模板准备／采集／交付链路的用例保留并实际运行。
- [文档仍有“旧模块保留”表述] → 同一变更中更新 ARCHITECTURE、README 与 code-scene-runtime。

## Migration Plan

单次提交完成：删除模块与依赖 → 收敛 `code_scenes` 与 `core/assets` → 迁移／删除测试 → 更新文档 → 运行相关测试 → 提交。回滚只需 revert 该提交；作品与模板不受影响。

## Open Questions

无。
