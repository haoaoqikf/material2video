## Why

测试总量已到 1161 个：非 slow 用例单次约 7 分钟，slow 用例还要起浏览器或跑真实渲染，更久。其中一批用例只重复断言仓库示例的固定帧数、时长、音效数量或路径，改一次示例就要同步改断言，发现缺陷的价值低、维护成本高。同时测试没有分层，日常改一个校验器也要面对接近全量的运行时间。

## What Changes

- 删除示例内容测试：`test_style_examples_strict`、`test_compound_interest_example`、`test_solar_system_*`、`test_solar_material_assets`、`test_vibe_night_fold_layout` 共 7 个文件、约 74 个用例。保留示例媒体恢复（`test_example_media`）、版本控制卫生、字体与风格包契约等产品测试。
- 删除重复或只检查文档措辞的低价值用例：风格注册表在两个风格文件里的重复断言、两处文档 token 检查。
- 新增测试分层：`media` 标记真实 ffmpeg 编解码用例；`slow` 继续表示浏览器、真实渲染与长时等待。默认 `uv run pytest` 只收集纯单元与契约用例，`--full` 才收集全部；显式 `-m` 仍完全交给调用方。
- 缩短 `render_session` 超时用例的等待（30 秒改为 1 秒），断言不变。
- 同步 README 的测试命令与 AGENTS.md 的验证层级。

## Capabilities

### New Capabilities

- `test-suite-tiering`：日常默认层、媒体层、浏览器/渲染层与全量的收集规则、标记语义和 CI 运行范围。

### Modified Capabilities

无。测试组织不改变 `m2v` 命令、材料、分镜或渲染契约。

## Impact

修改 `tests/`、`pyproject.toml`、`tests/conftest.py`、`README.md`、`AGENTS.md`。不修改产品代码、视频制作流程、评审门禁或渲染契约；CI 继续运行 `-m "not slow"` 子集。
