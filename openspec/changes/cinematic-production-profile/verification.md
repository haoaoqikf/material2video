# 验证与审查记录

本文件按阶段记录 cinematic 变更的实施与验证结果。任务全部完成后按项目约定同步主规格、归档并提交。

## 阶段 1：口径修正与文档基线（1.1–1.7）

- 固定示例名单改为 buffer-smoothing、darts-trial-and-error、solar-system-journey，并同步横竖屏与时长描述；`AGENTS.md` 的名单此前已正确，无需改动。
- `media-contract.md` 的「节拍音效当前不渲染」改为「已进入母版混音」，并补一条音效混音验收口径（定位起点、越界失败、叠入后仍按同一响度与真峰值复核、素材摘要进指纹）。
- `PROJECT_PLAN.md` 加入 standard/cinematic 双档位与电影级路线；「复杂转场或第二套渲染引擎」改为「不换引擎，以镜头、后期与母版实现」；保留不自动选曲，明确配乐来自本地素材或确定性程序化音床。
- 新增 `references/cinematic-video.md`：参考板、look bible、镜头语法、材质/后期/声音清单、五阶段门禁、20 项检查表、感知评分卡、反模式与成本表。
- `SKILL.md` 增加档位表、cinematic 触发词、阶段门禁与 look-dev 批准例外（standard 自动通过的唯一例外）。
- `production-workflow.md` 增加 cinematic 分支命令；`visual-review-rubric.md` 增加十项评分卡；`design-tokens.md` 说明 cinematic look 不替代作品自由设计。
- 验证：`sync_docs.py --check` 无漂移；文档相对链接 78 项、JSON 示例 13 项全部有效；`test_doc_examples.py` 与 `test_type_catalog.py` 通过。

**实现状态口径**：阶段 1 只交付文档，cinematic 代码尚未落地，因此参考文档与 `SKILL.md` 都显式标注「实现完成前仓库实际可用的仍是 standard 链路」。该标注在阶段 6 更新为「当前支持」。

## 阶段 2：档位、字段与指纹（2.1–2.7）

- `project.json` 新增可选 `productionProfile`（standard/cinematic，缺省 standard）。非法值在 `general` 类型校验阶段失败；金融与住宅类型显式拒绝 `--profile`，不静默按 standard 处理。
- 档位写入准备记录的 `props.productionProfile` 与 `productionProfileSource`（`default`/`project`/`command-line`）、`inputs.profile`、预演记录与成片溯源的 `productionProfile`/`productionProfileSource`。
- 幕级新增 `leadInFrames`（0–1800）、`tailFrames`（0–1800）、`readingHoldFrames`（0–360）；未声明时阅读停留仍为 24 帧，时间轴与既有行为一致。留白计入幕长，旁白窗口整体后移。
- `content.props.shots` 与 `look` 增加类型/范围/未知字段校验，`narrationSegments[].claims` 校验非空、去重与长度上限；错误按 `scenes[<幕>].content.props.shots[<镜头 id>]` 定位。
- 准备指纹与片段缓存键：档位与 `claims` 只在**非默认**时写进录制配置，standard 作品不声明新字段时缓存键与既有片段逐字节一致；`shots`/`look` 本身在 `props` 内，`leadIn`/`tail`/`readHold` 改变幕长与旁白窗口，都会让旧片段失效。
- CLI 新增 `prepare --profile standard|cinematic`，非法值由 argparse 拒绝；实际来源写入准备记录。

### 与任务措辞的一处偏离（2.3）

任务写「镜头时间窗落在旁白段内」。按 60 秒样例的实际时长分布（9 段旁白各约 5–7 秒）与「hero 必须 8–12 秒连续」的硬要求，把 hero 限制在**单段旁白内**在数学上不成立。因此实现的判定是：

- 每个镜头必须落在本幕时长内；
- **声明** `segment` 的镜头必须**完整覆盖**该旁白段的窗口（这是作者对「这个镜头讲的就是这段旁白」的承诺）；
- 没有声明 `segment` 的镜头只查幕时长——冷开场、收尾与跨段 hero 都属于这一类。

`claims` 与镜头的可见性对应关系由 QA 的 claims 检查负责（每条 claims 必须落在至少一个镜头的时间窗内）。该口径已同步写入 `storyboard-schema.md` 与 `cinematic-video.md`。

## 阶段 3：共享电影套件与确定性（3.1–3.4、3.6–3.8；3.5 待做）

- 依赖：`postprocessing@6.39.5` 与 `@react-three/postprocessing@3.2.0` 进入 `web/package.json` 与锁文件，并加入代码场景的批准依赖清单。两份指纹（`implementation_inputs` 与 `build_input_fingerprint`）本来就把 `package.json`/`pnpm-lock.yaml` 计入，因此 bundle cache 键与片段缓存键自动更新，无需另加开关。
- 套件：`web/src/code-scene/cinematic.tsx` 导出 `LookProvider`/`useLook`/`useShot`、`CameraRig`、`PostFX`、`Starfield`、`ParticleBelt`、`Atmosphere`、`Rings`、`SunSurface`、`Corona`、`Prominence`、`OortCloud`、`Comet`，以及 `pathIntersectsSphere`/`cameraPathRisk`/`backgroundRisk`、`activeShot`/`ease`/`seededRandom`/`hashSeed`。SDK 的上下文与类型拆到 `context.ts`，避免 SDK 入口与套件互相导入成环。
- 确定性：`PostFX` 关闭 MSAA、自带「镜头 id 哈希 + 帧号」种子的颗粒效果，不使用库里依赖 `Math.random` 生成噪点纹理的 `Noise`；相机位置、朝向、FOV、滚转与曝光全部由帧号算出。
- `useMediaAsset` 现在返回 `colorSpace`、`alpha` 与登记许可。它们由实测像素格式推导、许可取来源记录原文，**不写回来源记录**，因此既有作品不需要重新导入素材。
- `lut` 由「任意文本」收紧为内置调色档名（`neutral`/`deep-space`/`teal-amber`/`warm-film`）：录制期不取外网、不读作品目录，非法值明确失败。
- 依赖缺失的失败口径：`code_scenes.require_cinematic_dependencies()` 在打包前检查两个后期包，缺了直接报「请先运行 pnpm -C web install」，不会静默渲染成没有后期的画面。

### 真实浏览器验证（新增 `tests/test_cinematic_scene_kit.py`，9 项）

- **同帧可复现**：同一场景两次独立录制、同一帧的截图 PSNR ≥ 60dB（实测相等）。
- **镜头确实在动**：同一镜头首末帧 PSNR < 40。
- **后期生效**：开与关后期的同一帧 PSNR < 45。
- **标准画面不受影响**：把 `export * from './cinematic'` 从 SDK 摘掉后重建，标准场景同一帧 PSNR 为 `inf`（逐像素相同）。
- **批准边界未被放宽**：`lodash` 仍被拒绝。
- **套件自身过确定性闸门**：对 `cinematic.tsx` 跑 `source_policy.scan` 无违规。
- **穿球与背景裁切检查**：纯函数结果在页面内直接断言（命中、未命中、余量不足、星空壳外与超出远裁剪面）。
- 另有 Python 侧用例覆盖缺依赖提前失败、`lut` 非法值、`useMediaAsset` 新字段。

## 阶段验证结果

- 完整 Python 回归：收集 545 项、541 项通过、4 项跳过、无失败（阶段 2 结束时为 532 项，阶段 3 新增 13 项）。
- 前端：`pnpm -C web test` 4 个文件 58 项通过；`pnpm -C web build`（含 `tsc --noEmit`）通过，保留既有 chunk 体积提示。
- 文档相对链接 78 项、JSON 示例 13 项全部有效；`sync_docs.py --check` 无漂移。
- QA 与资产审计模块以自造小媒体与真实成片双向验证；`lookdev` 的取点、样片窗口与接触表有单元测试覆盖。
