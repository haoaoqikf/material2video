# 制作工具与本地证据接入记录

本记录对应任务 3.2 与 3.4。

## 输入与检查器分离

- `src/m2v/production/dependencies.py` 只遍历作品可达源码、宿主、字体、登记媒体、配置、依赖锁与本地构建脚本；主项目 SDK、`web/` 参考源码和模板更新不进入作品媒体身份。
- 动态导入与动态素材 ID 保守扩大作品内绑定；越界目录联接在任何读取前拒绝。
- 渲染溯源记录实际构建输入、准备身份、帧窗、编码参数与交付摘要；QA、评审报告与检查器输出版本分别记录，并各自绑定当前准备与视频摘要。检查规则更新要求重新检查，不自动使画面输入陈旧。

## 本地产物读取

- `validate/prepare/preview/render/qa` 通过 `standalone/executor.py` 调用作品本地入口，并复核实际文件摘要、准备身份、帧窗和技术参数。
- `status` 使用本地 `inspect` 与当前 `outputs/prepared.json`；`review/issues/baseline` 读取 `outputs/` 下的本地产物与评审记录。
- `lookdev` 的静帧、接触表与样片：静帧与本地采集通过新增的 `lookdev` 命令完成，样片通过本地 `preview` 生成；主项目复核样片的准备身份、起止帧、帧率、画幅与交付摘要后，只负责取点、拼图与证据整理。
- `review timeline` 通过新增的 `materialize` 命令物化全片片段，复制到盲审目录，并使用作品自己的 `scripts/build-review-player.mjs` 与 `src/production/player.tsx` 构建播放器。

## 验证

- `tests/standalone/test_management_bindings.py` 覆盖旧 SDK 引用拒绝、目录联接越界、实现输入变化与候选搬移；`test_management_adapter.py` 覆盖委托结果与独立技术复核；`test_management_samples.py` 覆盖本地样品与来源绑定。
- `tests/standalone/test_local_lookdev.py` 覆盖本地静帧合成范围与越界拒绝。
- 在 `text-motion/fold` 上实际运行 `m2v lookdev --sheet 1 2 --still-scale 1`，通过本地 `lookdev` 生成静帧与接触表；准备身份与当前记录一致。
- 在隔离模板工程实际运行 `m2v review timeline`，本地 `materialize` 生成全片片段，作品脚本构建 `player.js`、`timeline.json`、字体与音频；主项目未使用 `web/` 渲染根。

## 保留范围

- 主项目旧 `types/scene_film` 准备／采集模块保留为模板提取依据和仓库测试对象，不再被生产命令调用；公开 SDK 入口、全局依赖登记与仓库场景映射已删除。
- 未迁移的外部检查器规则与主观评审不在本记录范围；技术检查通过不表示制作完成或关闭独立评审问题。
