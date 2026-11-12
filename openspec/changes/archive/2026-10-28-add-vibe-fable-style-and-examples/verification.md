# 验证与审查

## 实施范围

- `styles/vibe-fable/`：清单、tokens、GUIDE 与十个组件。不携带字体资产，复用宿主已注册的 `M2V Sans` / `M2V Inter`。
- `src/m2v/core/styles.py`：风格发现跳过保留目录 `examples`，`load_style` 对保留名明确失败。
- `src/m2v/types/general/explainer.py`：屏幕字幕窗口在幕显式声明时长时不得越界。
- 文档与测试同步：`styles/README.md`、风格接入契约、README、PROJECT_PLAN、`tests/test_vibe_fable_style.py`。

`examples/` 的三个固定示例与 `example_catalog.py` 未改动，示例数量上限规则未被触碰。

## 验证

- `uv run m2v styles --json` 返回 `vibe-fable` 与 `vibe-night`，`styles/examples/` 不出现在清单中。
- 风格与示例相关测试：含慢速用例共 54 项通过、1 项跳过（无符号链接权限）。
- 全量非慢速回归（单进程）：940 passed、5 skipped、52 项按 `slow` 排除。并发跑测试时 `test_bundle_cache` 会因共享 `web/.bundle` 缓存互相干扰而偶发失败，单进程与单独运行该文件均通过，与本变更无关。
- `sync_docs.py --check` 通过：入口 1419、方案 1434、制作与迭代 1791、最终 1267 字符。
- OpenSpec 变更 strict 校验通过。

## 独立审查发现与修正

独立只读审查提出 2 项阻塞与 8 项一般问题，全部核实并处理：

**一般问题**

- 保留目录只影响发现、不禁止加载 → `load_style` 对保留名明确失败，测试改为「放入合法清单仍须失败」。
- 文档残留「B 寓言未安装」旧话 → 已同步状态、外观采纳、能力边界与未来合并四段。
- 风格接入契约未记录保留目录 → 补入包结构一节。
- 画布文字用通用字体族 `serif` / `sans`，实际回退到系统字体 → 改为包内登记的 `Vibe Night Serif` 与宿主 `M2V Sans`。
- 示例 README 多处与画面不符 → 按重写后的实现重写，并写明字幕间隙、机位与轨迹的真实分布。
- 字幕窗口越幕无校验 → 校验器与测试各补一条；示例本身已合规。
- 缺「示例变更不影响包指纹」回归 → 新增用例，改示例文件后包指纹不变。

另修正：`PROJECT_PLAN` 风格配对写反、文档状态自相矛盾、重复顶行（`again` 幕）、未使用的 `ParallaxBand` 导入、proposal 重复用词。

## 审查结论与限制

- 示例实现与字幕为自行编写；素材使用仍需分别核验来源与许可。
- 未改变分镜 schema、共享字幕层、制作门、审核轮次与导出门禁。

## 主规格与归档

同步 `openspec/specs/style-registry/spec.md` 的注册范围与保留目录规则，新增 `openspec/specs/vibe-fable-style/spec.md`；变更归档至 `openspec/changes/archive/`。

> 2026-11-12 内容清理：已删除用户指定作品的专属内容；本档案仅保留其余历史范围，不代表本轮重新验证。
