# 验证与审查

## 实施范围

新增第二个正式风格包 `styles/vibe-fable`（B 寓言）与两个风格示例，并把风格示例与风格包在目录上分离。

- `styles/vibe-fable/`：清单、tokens、GUIDE 与十个组件。不携带字体资产，复用宿主已注册的 `M2V Sans` / `M2V Inter`。
- `styles/examples/vibe-night/fold/`：《折叠》九幕 33 秒；`styles/examples/vibe-fable/pigeon/`：《鸽子的迷信》六幕 33 秒。
- `src/m2v/core/styles.py`：风格发现跳过保留目录 `examples`，`load_style` 对保留名明确失败。
- `src/m2v/types/general/explainer.py`：屏幕字幕窗口在幕显式声明时长时不得越界。
- 文档与测试同步：`styles/README.md`、风格接入契约、外部参考项目登记、vibe-knowledge-film 指引、README、PROJECT_PLAN、`tests/test_vibe_fable_style.py`。

`examples/` 的三个固定示例与 `example_catalog.py` 未改动，示例数量上限规则未被触碰。

## 验证

- `uv run m2v styles --json` 返回 `vibe-fable` 与 `vibe-night`，`styles/examples/` 不出现在清单中。
- `uv run m2v validate` 与 `prepare` 在两个示例上均通过；`lookdev --stills` 与 `--sheet` 实际出帧，逐帧检查后修正。
- 风格与示例相关测试：含慢速用例共 54 项通过、1 项跳过（无符号链接权限）。
- 全量非慢速回归（单进程）：940 passed、5 skipped、52 项按 `slow` 排除。并发跑测试时 `test_bundle_cache` 会因共享 `web/.bundle` 缓存互相干扰而偶发失败，单进程与单独运行该文件均通过，与本变更无关。
- `sync_docs.py --check` 通过：入口 1419、方案 1434、制作与迭代 1791、最终 1267 字符。
- OpenSpec 变更 strict 校验通过。

## 独立审查发现与修正

独立只读审查提出 2 项阻塞与 8 项一般问题，全部核实并处理：

**阻塞**

1. **寓言计时器按幕重置。** 录制逐幕挂载，`elapsedSeconds` 是幕内时间，原实现每幕从 0 开始，计时器永远走不到 15 秒，与「食物按时间来」的核心机制矛盾。改为每幕在 `content.props.clock.startSeconds` 声明全片起点，场景换算绝对时间；实采跨幕帧确认读数连续（1 秒→14、8 秒→7、26 秒→4、31 秒→14）。
2. **示例是上游 `film.js` 的函数级移植，字幕逐字照抄。** 违反仓库「不复制清单」与本次自己的声明。已重写：鸽子、箱子、计时器、食槽的形体、比例、画法与调色改由本文件自行决定（计时器改为环形刻度 + 弧 + 端点，不再用指针与扇区）；两个示例的屏幕字幕全部按自己的句子重写。

**一般问题**

- 保留目录只影响发现、不禁止加载 → `load_style` 对保留名明确失败，测试改为「放入合法清单仍须失败」。
- `vibe-knowledge-film.md` 残留「B 寓言未安装」旧话 → 已同步状态、外观采纳、能力边界与未来合并四段。
- 风格接入契约未记录保留目录 → 补入包结构一节。
- 画布文字用通用字体族 `serif` / `sans`，实际回退到系统字体 → 改为包内登记的 `Vibe Night Serif` 与宿主 `M2V Sans`。
- 示例 README 多处与画面不符 → 按重写后的实现重写，并写明字幕间隙、机位与轨迹的真实分布。
- 字幕窗口越幕无校验 → 校验器与测试各补一条；示例本身已合规。
- 缺「示例变更不影响包指纹」回归 → 新增用例，改示例文件后包指纹不变。
- `fold` 收尾出处未渲染 → 收尾幕渲染 `credit` 小字。

另修正：`PROJECT_PLAN` 风格配对写反、`external-projects` 状态自相矛盾、重复顶行（`again` 幕）、未使用的 `ParallaxBand` 导入、proposal 重复用词。

## 审查结论与限制

- 两个示例是**风格示例**，不是完整评审过的交付作品：没有核心样片、全片粗片与最终终审记录，示例 README 已如实写明。
- 形状是示意，不追求解剖或行为学精确；《折叠》只画一条链、二维近似排布，《鸽子的迷信》的箱子与计时器是画的。完整来源与事实保留在示例 README。
- 上游 `engine/`、`film.js`、GIF/JPG、角色与画面未复制；示例沿用已登记样片的**选题与分镜结构**，实现与字幕为自行编写。上游 MIT 许可要求保留显著部分的版权声明；本次未复制其代码，因此不加 NOTICE，示例 README 明确登记「选题与分镜结构来源」。
- 未改变分镜 schema、共享字幕层、制作门、审核轮次与导出门禁。

## 主规格与归档

同步 `openspec/specs/style-registry/spec.md` 的注册范围与保留目录规则，新增 `openspec/specs/vibe-fable-style/spec.md`；变更归档至 `openspec/changes/archive/`。
