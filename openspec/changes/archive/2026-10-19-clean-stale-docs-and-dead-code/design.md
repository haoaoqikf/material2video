## Context

动机见 `proposal.md` 的 Why。设计相关的现状约束：

- `src/m2v/engine/gallery/__init__.py` 已经确立了「包 `__init__` 只做重导出 + `__all__`」的写法，
  因此把过大模块改成包是本仓库既有模式，不是新引入的适配层。
- 类型目录（`src/m2v/types/catalog.json`）与 `SKILL.md`/`README.md`/`docs/PROJECT_PLAN.md` 的
  类型清单由 `sync_docs.py` 单向生成，改目录后必须重新生成。
- 成片指纹把实现文件算进摘要：`financial.render_inputs_digest`、`housing_render._inputs_digest`、
  `explainer_prepare.implementation_digest` 都逐个列了实现文件，拆包后必须让摘要覆盖新文件，
  否则「改了实现却判成当前」。
- 测试大量使用 `monkeypatch.setattr(模块, 私有名, …)` 顶掉打包与渲染进程，因此合并后的替身目标
  必须落在真正执行的那一层。

## Goals / Non-Goals

**Goals**

- 每个契约只有一处实现、一处文档真源。
- 拆分后的公开名、函数签名、stdout 协议与判定逻辑完全不变；错误消息逐字保持（唯一例外见 Decisions）。
- 指纹覆盖面在拆分后不缩小。

**Non-Goals**

- 不引入新能力、不改渲染契约与分镜结构。
- 不为拆分的模块保留「旧路径仍然可用」的兼容层：改名后一次性更新全部调用点。
- 不拆分 `openspec/specs/**`（一个能力一个 spec 文件是 OpenSpec 的结构约束）与内聚的小文件。

## Decisions

**D1：合并校验原语，但保留各类型自己的语义化校验。**
`core/validate.py` 只收 `fail`/`obj`/`number`/`integer`/`text`/`items`/`positive_number` 七个语义
明确的原语。`financial._required_text`（消息「不能为空」且返回 `.strip()`）、`housing._text`
（同样 `.strip()`）、`catalog._require_text`（消息带「类型目录」前缀）语义不同，留在原处。
备选：把 `_required_text` 也并进来——会让三处不同的报错措辞被强行统一，属行为变化，故否。

**D2：`cinematic.py` 用 `_obj = obj` 这样的导入别名，不改 30 处调用点。**
该模块内多处把 `obj` 当局部变量名（`obj = _obj(look, …)`），直接改名为 `obj` 会让局部变量遮蔽
函数。别名让调用点与局部变量都保持原样，重复实现照样只剩一份。备选：重命名全部局部变量——纯
风格收益，改动面大，否。

**D3：无声渲染管线抽成 `SilentRenderSpec` + `generate`/`render`。**
差异（composition id、尺寸、材料名、目标文件名、时长推导、摘要函数、props 构造、溯源 type、
日志文案、报告 extra、进度行是否入日志）全部声明化；流程只有一份。通用类型只复用其中的
`metadata_confirm` 与 `write_report`：它的溯源要先写进临时目录再经 `security.deliver` 搬运，
与无声类型的直接落盘不同，强行统一会动到交付权限路径。

**D4：统一 composition 元数据不匹配的文案。**
四个入口（金融、住宅、通用、look-dev）各有一份同样的闭包，措辞两种顺序。合并后统一为
「期望 …，实际 …」，判定与阻断行为不变，且没有测试断言这四句文案。备选：加 `actual_first`
开关保留两种顺序——为一个纯文案差异加参数，否。

**D5：适配器保留模块级 `prepare`/`validate`/`preview`/`render`/`review_gate` 名字。**
`build_silent_type` 造出 `VideoType` 后，把它的四个生命周期入口再绑定成模块级名字：注册表用它，
测试与手工排查也直接调它们。这不是兼容层——名字本来就存在，只是改为指向同一份实现。

**D6：拆包后指纹改用 `implementation_files()` / 逐文件列表。**
`remotion` 包新增 `implementation_files()`；金融与住宅的摘要函数从 `Path(remotion.__file__)`
改为纳入该列表全部文件。否则 `__init__.py` 只有重导出，实现改动不再让候选过期。

**D7：文档按「读者的问题域」拆，而不是按行数机械切。**
`render-contract.md` 拆成「代码场景运行时契约」与「引擎、打包与编码」；`paths-and-outputs.md`
拆成「路径与归属」与「交付、溯源与报告」；`media-contract.md` 拆成「准备记录与字幕」与
「配音与韵律」。重复段落（交付权限、成片溯源、性能报告、字体覆盖）只保留在拆分后的
`delivery-and-provenance.md` 与 `design-tokens.md`，另一侧改指针。

**D8：`openspec/specs/video-production-workflow` 只改一处需求。**
「输入到输出全链路门禁」按 MODIFIED 处理：保留输入审查与候选采用证据，删除 130～170 字与
35～45 秒门禁。该门禁的实现（`article_text` 的 `standard_length_result`/`review_template`/
`save_candidate`）本次一并删除，规格与代码同时对齐。

**D9：拆包后不保留「打在包上也能生效」的魔术转发。**
`remotion` 包最初用一个 `ModuleType.__setattr__` 子类把包上的赋值转发给持有同名绑定的子模块，
好处是测试一行不用改。但它会让 `import m2v.engine.remotion.bundle` 取到函数而不是子模块，且把
「属性赋值」变成跨模块副作用——正是这个仓库一贯拒绝的隐式行为。改为：子模块 `bundle.py` 更名
`bundling.py` 消除与公开函数 `bundle` 的同名冲突，测试替身改打在**真正执行它的子模块**上
（`remotion.session._spawn`、`remotion.bundling._bundle_into` 等），`__init__` 的文档里写明这条规则。

**D10：金融类型保留 `financial.py` 作为公开面，而不是让 13 个调用点改导入路径。**
`materials.py`（材料契约与校验）与 `plan.py`（编排、锚点、迁移）是两份实现，`financial.py` 只声明
类型常量并重导出公开名，`from m2v.types.financial import financial` 与 `financial.X` 的用法不变。
理由：这些名字是类型的公开契约（`WIDTH`/`HEIGHT`/`FPS`/`load_project`/`build_render_props`/
`render_inputs_digest`/`prepare_line_plan`/`migrate_line`），改名只会制造机械改动，不增加清晰度。
`materials.py` 仍有 545 行：三份材料互相引用、私有校验辅助被两边共用，再切一层会出现循环导入，
收益低于风险，因此按职责停在这里。

**D11：`remotion.require_environment` 随本轮删除。**
它做「起进程前检查前端依赖与外部程序」的预检，但全仓库零调用——测试里的三处 `setattr` 是替身，
不是消费方。留着会被下一次读代码的人当成活能力。

## Risks / Trade-offs

- [拆包后指纹漏掉新文件，导致「改了实现却判成当前」] → D6：包级 `implementation_files()`，并在
  金融与住宅的摘要函数里纳入；验证时确认摘要随实现文件变化。
- [合并渲染管线时行为漂移（临时目录前缀、进度日志、报告字段）] → 差异声明化（`log_progress`、
  `report_extra`）；`tests/test_render_performance.py` 仍按阶段断言耗时与 `session` 字段。
- [测试替身打在旧位置而静默失效] → 三个测试文件的 `monkeypatch` 目标改到 `render_pipeline` 上，
  并保留「重复导出只生成一次」的断言；失效会直接报 `AttributeError`。
- [文档拆分丢事实] → 合并/拆分时逐句核对事实去向，旧文件名在 tracked 文件里必须无残留引用，
  并逐条检查相对链接与锚点。
- [拆分引入循环导入] → `remotion` 包内共享常量放在被依赖的底层模块，`__init__` 只重导出；
  `code_scenes` 的 `materialize` 归到采集侧、`financial` 的 `_validate_plan`/`_validate_pacing` 归到
  材料侧，保证依赖单向；拆完用公开面比对与全量回归验证。
- [测试替身打在包上静默失效] → 见 D9：替身一律打在执行它的子模块，并在 `__init__` 文档里写明；
  失效会立刻表现为真实起进程或断言不触发，而不是静默通过。

## Migration Plan

一次性提交，无迁移工具：旧模块名与旧文档名在本次全部替换，调用点同步更新；不保留别名文件。
回滚即 `git revert` 本次提交。

## Open Questions

- 示例 `render-rough.py` / `render-risk.py` 目前是「整片动态粗预演」与「风险帧」的唯一实现，却调用
  私有 `code_scenes._capture`。是否把它提升为 CLI 命令（例如 `m2v preview --fps`）留待后续单独评估，
  本次只记录不动。
