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
- 场景录制在 `outputs/code-cache/.recordings/` 生成中间帧，正常退出时移除工作目录。后续录制回收超过 24 小时、且创建进程和已登记的采集子进程均已退出的旧工作目录。已发布的片段及收据保留在 `outputs/code-cache/`。
- 独立工程持有自己的运行时代码。以后升级既有作品的运行时，需要重新核验其准备记录和评审绑定。
