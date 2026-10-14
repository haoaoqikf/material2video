## 1. 类型身份与材料

- [x] 1.1 在 `src/m2v/types/catalog.json` 登记 `stock-montage`：说明、摘要、规划文案、skill 指引与 `brief` 材料模板（主题、逐幕关键词、目标时长、画布、转场与运动、可选口播、可选音床、图库配置）。
- [x] 1.2 在 `src/m2v/cli.py` 的 `_register_builtins` 注册新类型，并挂载 `m2v stock search --project <目录>` 子命令。
- [x] 1.3 用 `m2v types` 与 `m2v init --type stock-montage` 确认登记与模板落盘可用。

## 2. 在线检索与下载

- [x] 2.1 新增 `src/m2v/types/stock/provider.py`：图库适配器协议、Pexels 实现（图片与视频检索、媒体文件选择）、可注入的 HTTP 传输、`provider.apiBase` 覆盖与凭据只从环境变量读取。
- [x] 2.2 新增 `src/m2v/types/stock/search.py`：按幕检索、确定性评分与去重、下载到 `assets/stock/`、写 `outputs/footage-search.json`（brief 指纹、检索参数、逐幕候选与入选、来源/作者/许可/尺寸/时长/摘要）。
- [x] 2.3 失败路径：缺少凭据、未知图库名、某幕无候选、下载或响应异常时给出可照做的报错，且不落盘部分结果。

## 3. 类型适配器

- [x] 3.1 新增 `src/m2v/types/stock/adapter.py`：`validate` 校验 brief 字段、检索记录与 brief 指纹一致、逐幕素材存在且摘要匹配、来源与作者与许可非空、路径不越界。
- [x] 3.2 `prepare`：编译帧精确时间轴（时长分配、视频裁剪入出点、静图推拉平移、硬切/交叉淡化），复用 TTS 口播与字幕、共享声音契约与混音，登记素材为 `file:` 输入。
- [x] 3.3 `preview` / `render`：渲染期用 `LocalServer` 暴露作品目录并在 props 注入 `mediaBase`，成片走既有媒体验收与溯源。
- [x] 3.4 `review_criteria` 覆盖画面质量、剪辑节奏与素材来源合规；`review_template` 与门禁沿用统一入口。

## 4. 画面与前端接线

- [x] 4.1 新增 `web/src/compositions/StockMontage.tsx`：按幕渲染图片与视频、推拉平移、交叉淡化、字幕带与来源署名行。
- [x] 4.2 在 `web/src/Root.tsx` 注册 `StockMontage` composition（时长/尺寸/帧率由 props 推导）。
- [x] 4.3 画面单测：时长推导、幕边界、运动参数与字幕显示区间。

## 5. 测试

- [x] 5.1 `tests/test_stock_montage.py`：用本地假图库服务覆盖检索成功、逐幕候选不足、缺少凭据、素材摘要变化、路径越界与许可缺失。
- [x] 5.2 覆盖时间轴编译：时长分配夹取、素材过短失败、交叉淡化越界、口播超容量失败。
- [x] 5.3 覆盖音床：单条母版音轨、参数非法被拒、声音摘要写入准备记录。
- [x] 5.4 端到端离线渲染验证：用本机生成的短视频与图片、本地假图库完成 search → validate → prepare → preview，验收帧数、尺寸、帧率与音轨。

## 6. 文档、验证与归档

- [x] 6.1 新增 `.agents/skills/material2video/references/stock-montage-video.md`：材料字段、检索与凭据要求、许可留证、剪辑规则与门禁。
- [x] 6.2 运行 `python .agents/skills/material2video/scripts/sync_docs.py` 同步 README 与项目规划清单，并检查链接与示例。
- [x] 6.3 运行新类型测试与全量离线回归，确认新增失败为零，记录既存失败项。
- [x] 6.4 检查暂存内容并提交源码、测试与文档，随后同步 `openspec/specs/` 主规格、归档本变更并提交归档结果。
