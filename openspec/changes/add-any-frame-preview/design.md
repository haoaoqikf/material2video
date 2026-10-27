## Context

`lookdev` 目前有两类入口：`run()` 出代表静帧、接触表与有声样片；`keyframes()` 只出三张代表静帧。取点都由 `still_frames()` 按 hero 镜头后段自动决定。另有一条独立路径 `m2v gates check --gate G4 --checkpoint <ID>` 按设计合同采集指定时刻，但那是正式制作证据，不能用于日常看图。

底层采集能力其实已经支持任意帧：`capture._capture(selected_frames=...)` 会从第 0 帧连续推进，只在选定帧位置截图（`capture.py:247-263`）。`native_stills()` 已按幕拆分并复用这条路径。缺的只是上层取点、标注与一致性核对。

## Goals / Non-Goals

目标是让"改完画面马上能看"的反馈环路从一轮完整生成缩短到一条命令，并为同帧一致性提供命令行入口。

非目标：不新增顶层 CLI 命令；不实现随机访问（运行时只接受连续帧推进，不改造）；不改变默认静帧与样片的任何行为；不新增门禁。

## Decisions

- **扩展 `lookdev` 而不是新建 `sheet`/`motion`/`det` 三个命令**：`modular-video-production` 已把 `lookdev` 定义为制作与质检入口，新建命令会形成第二个权威来源，也会重复实现一遍 general 类型守卫与分发。三个参数互斥，语义清晰。
- **时刻用秒，内部换算为帧**：作者看图时按秒思考，帧号由作品 fps 决定。换算在 Python 侧完成，并在启动浏览器前校验。
- **预校验放在采集之前**：`native_stills()` 现有的归属校验在全部采集完成之后（`lookdev.py:115-117`），非法时刻会先白跑一遍浏览器。新入口自己先按 `compiledScenes` 的 `[startFrame, endFrame)` 校验。
- **拼图加时间标注，且只用 ASCII**：没有时刻标注的拼图无法定位问题帧。标注用 ffmpeg `drawtext` 的 ASCII 数字与冒号，避免服务器缺中文字体导致整条命令失败。
- **一致性自检用两次独立采集**：运行时拒绝跳帧与倒序，因此不能靠"乱序重截"实现；两次独立会话各自从 0 推进到目标帧，比较最终合成结果，语义上等价于"同一帧重复渲染是否一致"。
- **比较前校验尺寸**：`look.motion.supersample` 会让 hero 帧按 2 倍像素输出（`capture.py:252-253`），`captureScale=1` 并不保证结果是 1×。尺寸不一致时明确失败，不给误判。
- **产物落 `outputs/lookdev/`**：复用既有目录与清单，不新建目录树；不写 `outputs/production/`。
- **不用 Pillow**：现有拼图与 PSNR 都走依赖内自带的 ffmpeg，保持一致，不引入新依赖。

## Risks / Trade-offs

- **代价随时刻位置增长**：没有随机访问，晚幕的远时刻要从该幕 0 帧推进。长片末段会明显慢；文档要写清，不承诺秒级返回。
- **跨幕多次 Node 构建**：`native_stills()` 对每个涉及的幕各构建一次。时刻分散在多个幕时会重复构建，接受这一代价，不改 `native_stills()` 的现有契约。
- **标注字体的平台差异**：`drawtext` 需要字体文件；只用 ASCII 数字可降低风险，若仍缺字体则退回不标注并明确提示。
- **一致性自检的成本翻倍**：两次采集等于双倍时间。属预期，且在文档中说明适用场景是"改了渲染相关实现后核对"，不是每次看图都跑。
- **清理会删图**：成功交付后 `outputs/lookdev/*.png` 按既有规则清理，清单保留。需要长期保存的证据图必须登记进 `visual-notes.md`。

## Migration Plan

纯新增参数，既有调用不受影响，无需迁移。文档更新后，`production-workflow.md` 中"指定时刻用 `gates check`"的说明改为区分两种用途：`lookdev --sheet` 是日常看图预览，`gates check` 是正式制作证据。完成后同步 `modular-video-production` 主规格并归档。
