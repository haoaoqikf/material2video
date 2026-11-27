# 目录约定与输出路径

每部作品有稳定的 slug。仓库内作品位于 `videos/<type>/<slug>/`，也可用 `--content-root` 或 `M2V_CONTENT_ROOT` 指定仓库外内容根；两种位置使用同一命令。五类 `type` 来自 `src/m2v/type_system/catalog.json`，没有类别层。`videos/` 下的内容和所有 `outputs/` 均不入库。

仓库自带示例位于 `examples/<type>/<slug>/`，源码、分镜、素材配方与说明入库；媒体和生成产物不入库。五部清单见 [examples/README.md](../../../../examples/README.md)。

```text
videos/<type>/<slug>/
├── project.json              # v3；materials 只声明 storyboard
├── storyboard.json           # v9；五类共用
├── scenes/                   # 本作品 TSX 入口及专属画面组件
├── article.md                # input.kind=article 时的源文
├── assets/                   # 登记媒体、声音和结构化来源文件
└── outputs/
    ├── prepared.json         # contractVersion 3 的当前准备记录
    ├── previews/video.mp4    # 可选短预演
    ├── video.mp4             # 正式成片
    └── ...                   # 技术检查、证据与缓存
```

`m2v init --type <type> --project <slug>` 在内容根的 `videos/<type>/<slug>/` 创建模板。传完整路径时必须与该归属一致。类型、画幅、分镜或源码改变后重新 `prepare`；旧类型和准备记录不自动迁移。示例素材按各自 `assets/recipe.json` 恢复并校验摘要，字体按 `fonts/registry.json` 恢复。

成片及其同名 provenance/performance 记录在作品 `outputs/`。目录归属只取当前项目材料，不根据文件名猜测类型。

## 构建与录制缓存

- 独立工程的 Remotion 构建缓存位于作品 `.cache/m2v-bundles/`。同一缓存根保留最近使用的 8 份构建。渲染与取帧期间有进程占用的构建继续保留。所有位置均被占用时，本次使用临时构建。
- 场景录制在 `outputs/code-cache/.recordings/` 生成中间帧。每个分块通过编码核验后即可回收其逐帧图，边界见证保留到该组校验完成。中断回收核对创建进程和子进程的启动身份。独立运行时在后续录制中回收超过 24 小时的残留，管理入口可识别超过一小时且已明确结束的任务。
- 发布的片段及收据位于 `outputs/code-cache/`。录制、预览服务与合成通过租约保护在用媒体。空闲时按最近使用顺序将可重建片段控制在 512 MiB 内，保留制作记录引用的片段。
- 独立工程持有自己的运行时。已生成工程在作品中更新运行时后需重新核验准备和评审绑定。管理端的存量清理可通过现有工程直接运行。

## 清理预览与执行

仓库内作品和示例默认纳入盘点。可用 `--project` 重复指定目录或用 `--content-root` 同时查找仓库外的作品。历史作品用 `--project` 指定。显示的是文件逻辑大小，链接、硬链接和文件系统分配量会影响磁盘实际回收。

```powershell
uv run m2v storage inventory
uv run m2v storage plan --project <作品>
uv run m2v storage clean --project <作品> --plan-sha256 <预览摘要>
uv run m2v storage compact-plan --project <作品>
uv run m2v storage compact --project <作品> --plan-sha256 <预览摘要>
uv run m2v review export --project <作品> --pack-id <评审包ID> --out <隔离目录>
```

清理执行前重新核对摘要、目录身份、进程和制作引用。评审封存先按原清单校验，再按摘要保留媒体字节。近期尚未导入的观察目录及直接登记的本地说明链接继续保留。生成新评审包时小批补封存此前已导入报告的包，错误与跳过项逐项报告。封存或清理后核对当前成片及旁车摘要和适用评审状态。对人工基线和未识别目录按[修订流程](video-revision.md)核对当前引用、原始素材与原件保留。

使用 Qwen3-TTS 的工程可按[独立工程说明](../../../../templates/standalone/README.md)共享或恢复模型权重。
