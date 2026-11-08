# 通用功能与示例处置台账

本表是实施清单，不是已完成能力；完成时补充具体文件、消费者、验证与提交。删除前必须检查直接与传递引用，不以七例未使用证明所有公开能力都无用途。

改造前源码修订为 `262f26aad083447fcf0bca32ad67421d70b4bf96`；[baseline.json](baseline.json)记录七例源码、恢复配方和已有产物摘要。[consumers.json](consumers.json)按实际分镜入口记录74项逐例递归本地文件引用、129项SDK符号采用及其真实声明位置，并保存66个共享Web模块的直接／反向依赖和SDK子入口。它区分实际场景入口与未采用的备用源码，不以SDK星导出数量冒充实际组件消费。主项目Python准备／采集／证据调用方见本表；改造时继续核对对应直接引用，删除尚未执行。

基础执行模板已提取到 `templates/standalone/`，具有自身Python命名空间、Node/Python锁文件、字体恢复和运行命令；主项目新建／validate／prepare／preview／render／QA已接入v3本地委托，七例及其他制作工具仍待切换。阶段验证与独立代码审查见[基础阶段记录](implementation-base.md)和[管理委托阶段记录](implementation-management.md)。

| 当前实现 | 当前消费者／职责 | 目标处置 | 状态 |
|---|---|---|---|
| web/src/code-scene/sdk.tsx、entries.json | 七例、当前作品及宿主 | 移除强制SDK总入口；拆成本地基础运行与按需采用源码 | 已删除公开入口与映射；七例改用作品内模块，`tests/support/code-scene-reference.tsx`仅作测试夹具 |
| web/scripts/build-code-scene.mjs | 场景准备与样品 | 改为作品本地构建，去仓库SDK映射、全局依赖解析 | 作品使用本地构建器；本脚本仅服务仓库参考测试，不再参与作品运行 |
| web/code-scene-dependencies.json及读取器 | 全局作品依赖登记 | 用作品本地依赖声明、锁文件与来源记录替代 | 已删除；作品在自己的`package.json`与锁文件中声明精确依赖 |
| code_scenes/config.py强制后期依赖 | 所有场景构建 | 删除无条件后期安装要求，仅采用后期的作品声明依赖 | 已删除；模板基础依赖不含后期，solar按需采用R3F与后期 |
| context、host、capture-clock、frame-tasks | 资源就绪、受控时间、异步采集 | 提取为基础本地模板，保留独特失败边界测试 | 已提取到`templates/standalone/src/code-scene/`；七例各自持有本地副本 |
| SceneFilm、transitions、fonts、frames | 成片合成与字幕 | 模板本地化，作品内单一配置来源 | 已提取到模板并随七例生成 |
| Python准备、采集、Remotion、混音 | 统一生产链路 | 提取成熟执行实现；作品本地命名空间及环境 | 已提取到`film_runtime`；主项目旧模块仅作模板来源与测试对象 |
| Painter、动效、路径、图表、镜头 | 逐例实际采用 | 根据引用收敛本地源码／参考，删除未采用总导出 | 七例按实际采用复制本地源码；未采用能力保留为参考 |
| diagram、math、icons、serif子入口 | 公式／衬线有示例消费者；其余待查公开用途 | 公式／衬线本地化；无消费者包装删除，保留选型建议 | math／serif随compound-connect与fold本地化；diagram／icons作为可选参考，不进入模板依赖 |
| financial/building/vehicle Web绘制包装 | 可选结构化来源，不被七例使用 | 查明真实引用；移除无用包装，保留数据快照及可选准备能力 | 保留主项目参考实现与来源准备；七例不预装，缺模块时明确报错 |
| 全局主题、样式令牌、安装依赖 | 旧来源场景与展示 | 逐项按消费者清理，保留本地实际必需配置 | 作品使用本地字体、画幅与合成配置；全局主题不再进入作品运行 |
| core.delivery、production.dependencies | 来源和媒体绑定 | 只复核作品实际输入，检查器版本单独记录 | 已解除候选／场景依赖的主项目渲染绑定；外部检查器规则及调用方尚待完成 |
| design_sample及production.samples | 原生采集与独立交付 | 采集委托本地，保留现有评审门禁 | 已完成本地委托、独立来源／媒体复核与相关门禁验证，见[样品阶段记录](implementation-samples.md) |
| src/m2v/engine/design_sample_viewer.html及主包资源登记 | 原主项目样品播放器；委托后无消费者 | 删除主项目副本，仅保留作品本地模板播放器 | 已删除；源码／包登记引用扫描确认无当前消费者 |

## 七例验收矩阵

| 示例 | 特有范围 | 独立资源恢复 | 脱库构建／预演 | 全片技术导出 | 受影响媒体复核 |
|---|---|---|---|---|---|
| text-motion/fold | Painter、衬线字体、事件声 | 已完成（3 项字体、5 个事件声） | 已完成 | 990 帧／33 秒，QA pass | 珠串、宋体字幕代表帧通过 |
| data-evolution/compound-interest | 精确数学、音床、事件声 | 已完成（2 项字体） | 已完成 | 870 帧／29 秒，QA pass | 双列收益与结论代表帧通过 |
| data-evolution/compound-connect | 公式字体、路径、事件声 | 已完成（22 项字体、6 个事件声） | 已完成 | 1200 帧／40 秒，QA pass | 差值图表与粒子代表帧通过 |
| principle-metaphor/pigeon | Painter、事件声 | 已完成（2 项字体、5 个事件声） | 已完成 | 990 帧／33 秒，QA pass | 实验室舞台代表帧通过 |
| principle-metaphor/luck-on-stage | 路径、Painter、事件声 | 已完成（2 项字体、6 个事件声） | 已完成 | 1230 帧／41 秒，QA pass | 概率盘与期望网格代表帧通过 |
| spatial-3d/solar-system-journey | R3F、镜头后期、15 段旁白、音乐／事件声 | 已完成（2 项字体、15 段旁白缓存） | 已完成 | 10473 帧／174.55 秒，QA pass | 水星、木星／土星、奥尔特云代表帧通过 |
| documentary-edit/american-science-milestones | 真实媒体、图表、12 幕 | 已完成（2 项字体、真实媒体复用） | 已完成 | 1800 帧／30 秒，QA pass | 电报、晶体管、大语言模型代表帧通过 |

## 历史处理

- 现有七例原地升级，主题、scene.id及视听要求保留；旧实现由Git历史查阅，不建立old／legacy双份工程。
- 忽略的videos历史及产物不批量改写；研究、失败报告和问题台账保留原结论。
- 媒体、字体和生成音频继续不入Git，配方、恢复代码、许可、工程和锁文件入Git。
- 本任务如创建忽略的历史快照，遵守同作品同类历史最多两次及依赖保护；不为架构改造例行复制整版媒体。

## 测试清理与保留范围

- 删除 `tests/common/test_scene_dependency_registry.py`：全局依赖登记与读取器已删除，不再有对应产品行为。
- 将 `still_props` 唯一行为测试迁到 `tests/standalone/test_local_lookdev.py`，改测作品本地模块，并增加越界拒绝。
- 仓库内参考入口测试改用 `tests/support/code-scene-reference.tsx`，继续覆盖 Painter、动效原语、组件出口与确定性源码闸门；该文件不是作品运行时。
- 保留 `test_canvas_painter`、`test_motion_components`、`test_motion_primitives`、`test_cinematic_scene_kit` 等针对参考源码的独特行为测试；保留交付失败、缓存、异步、计时与资源边界测试。
- 新增缺业务来源模块的明确失败测试；金融、建筑、车辆准备能力的既有直接测试继续运行。
