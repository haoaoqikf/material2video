## 1. 材料契约与校验

- [x] 1.1 把 `building.json` schema 升到 v2：新增 `openings[].sill`、`roof {type,height,overhang}`、`stairs {side,offset,width}`，保留稳定构件 ID/类别/楼层/最终几何；v1 明确失败并提示升级。验证：`uv run pytest tests/types/building_construction/test_building_construction.py` 覆盖合法 v2、v1 拒绝、窗台超高、屋顶/楼梯非法参数。
- [x] 1.2 把 `construction.json` schema 升到 v2：用 `shots` 替换 `camera`，新增 `initial`、`steps`（`stage/select/action/after/startSeconds/endSeconds`）与 `shots[].hide`；验证阶段覆盖、镜头覆盖/不重叠、步骤窗口、依赖无环、步骤不早于依赖结束。
- [x] 1.3 实现 glob 选择器展开与构件覆盖校验：每个非 `initial` 构件恰好匹配一次，选择器不重叠、不未知、不空匹配；错误报告步骤与构件 ID。验证：新增单元测试覆盖未匹配、重复、重叠、未知选择器与依赖环。
- [x] 1.4 更新 `src/m2v/type_system/catalog.json` 的 init 模板与类型说明，运行 `uv run m2v init --type building-construction` 生成 v2 材料并通过 `uv run m2v validate`。验证：`tests/types/building_construction/test_building_construction.py::test_init_and_prepare_frames` 更新为 60 秒/1800 帧并通过。

## 2. 三维画面与建造动作

- [x] 2.1 在 `web/src/types/building_construction/` 新增确定性构件图生成：场地、开挖、基础、柱、梁、板、楼梯与梯井、墙体真实洞口（`THREE.Shape` holes + `ExtrudeGeometry`）、坡屋顶/平屋顶、门窗、庭院；ID 规则与 Python 校验器一致。验证：前端单元测试对固定材料断言 ID 集合、洞口数量、无重复，并快照关键几何包围盒。
- [x] 2.2 实现步骤动作 `excavate/pour/grow/slide/lift/rotate/insert/spread` 的闭式求值：只读 `frame`、步骤窗口与显式参数，不读上一帧；依赖只约束开始时间。验证：任意帧正序、倒序、重复求值得到同一变换；测试覆盖每个动作端点与中点。
- [x] 2.3 实现 `shots` 相机轨道与 `hide` 取景隐藏：镜头覆盖、边界硬切、近景剖切、最终镜头恢复全部构件。验证：测试覆盖镜头越界/重叠拒绝，代表帧检查近侧墙隐藏后柱梁板仍可见、恢复后不缺构件。
- [x] 2.4 用 raw three.js 重写 `BuildingConstruction.tsx`：`WebGLRenderer`、透视相机、平行主光 + 半球补光、shadow map、接触阴影、材质区分、`EdgesGeometry` 轮廓、背景渐变与暗角；`delayRender`/`continueRender` 控制字体与场景就绪。验证：`pnpm -C web exec tsc --noEmit` 通过，`lookdev` 能出代表帧。
- [x] 2.5 增加 SVG 覆盖层：阶段轨、当前构件名称与引线、完工幽灵轮廓、3 m 比例尺与“建造过程示意”小字；标签夹取在安全区，不遮挡连接点。验证：代表帧逐张检查标签位置；尺寸不足或遮挡时调整后重出帧。

## 3. 首例材料与成片

- [x] 3.1 把 `videos/building-construction/two-story-house/building.json` 与 `construction.json` 重写为 v2：入口与主要门窗放在默认机位可见立面，坡屋顶/女儿墙完整，楼梯与梯井对齐，60 秒/1800 帧，7 个阶段、6 个镜头、约 20 个步骤。验证：`uv run m2v validate --project videos/building-construction/two-story-house` 与 `uv run m2v prepare --project ...` 通过。
- [x] 3.2 出代表帧核对建造顺序：场地/开挖、基础、一层柱梁板、二层柱梁板、墙体、屋顶、门窗、完工；检查柱梁板交接、洞口、遮挡、悬浮、穿插、z-fighting 与主体占比。验证：`uv run m2v lookdev --project ... --sheet 2 8 12 18 24 30 36 42 48 54 59` 逐张通过。
- [x] 3.3 完整渲染 1800 帧并跑 QA，记录渲染时长、峰值内存、同帧 PSNR、输出帧数/尺寸/帧率/时长与无音轨。验证：`uv run m2v render`、`uv run m2v qa` 通过；同帧重复与乱序探针 PSNR ≥ 60 dB。
- [x] 3.4 按“独立观察者复述”场景做一次盲看：不提供设计材料，让观察者复述建造顺序与柱梁板墙/屋顶/门窗连接；不能复述时回到镜头、步骤或标签修正并重渲染。验证：复述记录写入 `videos/building-construction/two-story-house/NOTES.md` 或评审记录。

## 4. 文档、测试与交付

- [x] 4.1 更新 `.agents/skills/material2video/references/building-construction-video.md` 的材料 v2、镜头/步骤/动作、剖切、标签与 60 秒首例说明；更新 `src/m2v/type_system/catalog.json` 的 summary/plan，运行 `uv run python .agents/skills/material2video/scripts/sync_docs.py` 同步 README/PROJECT_PLAN/SKILL。验证：`sync_docs.py --check` 通过。
- [x] 4.2 扩充 Python 与前端测试：v1 拒绝、v2 字段、选择器覆盖、依赖环、镜头覆盖、取景隐藏不改建成状态、动作端点、同帧确定性；运行 `uv run pytest`、`uv run pytest -m "not slow"`、`pnpm -C web exec vitest run` 与 `tsc --noEmit`。验证：无失败。
- [x] 4.3 检查暂存范围只含类型实现、首例材料、测试与文档，排除 `videos/` 媒体、`outputs/`、缓存与生成帧；提交。验证：`git status --short` 干净且无生成媒体，commit 包含代码与材料。
- [x] 4.4 按现有审核策略完成适用独立评审与问题复查，关闭必改项后标记制作完成。验证：评审记录包含复述结论、代表帧、同帧确定性与画面缺陷检查。
- [x] 4.5 同步 `openspec/specs/building-construction-video/spec.md`，运行 `openspec archive remake-building-construction-video` 并提交归档结果。验证：`openspec validate --specs --strict` 通过。
