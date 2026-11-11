## Why

仓库已有夜曲风格包 `vibe-night`，但寓言外观仍只有指导值：没有可安装的包，制作者每次都要手工构造扁平插画的配色、三层视差、本能读数仪表与规则卡。同时两套风格都缺少仓库内可直接对照的示例——只有零散的试制作品在 `videos/` 内且不入库，风格是否真的能落到成片上无法被验证和回归。

本次把 B 寓言转成第二个正式风格包，并给两套风格各配一个可校验、可渲染的示例。示例按用户明确授权放在 `styles/` 下，不占用 `examples/` 的三个固定名额，`examples/` 集合保持不变。

## What Changes

- 新增正式风格包 `styles/vibe-fable/`：清单、tokens、指导、B 寓言组件与无旁白屏幕字幕，组件以 TSX 实现。
- 风格注册改为只把**含有效 `style.json`** 的直接子目录视为风格包；`styles/examples/` 作为保留的非包目录存放示例，不改变已有 `styles/<id>/` 的位置与指纹语义。
- 新增两个风格示例：`styles/examples/vibe-night/fold/`（《折叠》，血红蛋白镰状细胞）与 `styles/examples/vibe-fable/pigeon/`（《鸽子的迷信》），均为 v8 场景；素材自绘，署名与许可保留在作品材料。
- 示例校验接入既有测试：清单固定、v8 契约、风格包一致性、无生成媒体入库；`examples/` 三例仍是唯一固定集合。
- 同步 `styles/README.md`、风格接入契约与 README 的当前能力。

## Capabilities

### New Capabilities

- `vibe-fable-style`：B 寓言风格包的注册内容、色板与版式、组件、字体与示例验收。

### Modified Capabilities

- `style-registry`：注册范围从「登记 `vibe-night`」扩展为「登记两个正式风格包」，并明确非包目录 `styles/examples/` 不被发现。

## Impact

- 新增 `styles/vibe-fable/`、`styles/examples/` 与对应测试、规格、文档。
- 修改 `src/m2v/core/styles.py` 的目录发现逻辑与 `m2v styles` 输出。
- 不新增视频类型或 CLI 命令；不改变分镜 schema、共享字幕层、制作门、审核轮次与导出门禁。
- `examples/` 的三个固定示例与 `example_catalog.py` 不变，示例数量上限规则不被触碰。
