## REMOVED Requirements

### Requirement: 作品材料与检索声明
**Reason**: `stock-montage` 独立类型及其 `brief.json` 人手材料入口被删除；素材作品改用 v6 `article-narrative` 分镜，主题、逐幕关键词、目标时长、画布比例、可选口播与音床都写在同一份 storyboard 里。
**Migration**: 不需要迁移工具；旧作品按 v6 文章分镜重新编排，素材经 `m2v article assets import` 重新导入留证。

### Requirement: 在线图库检索与下载
**Reason**: 检索与下载合并为「检索只产出候选、导入才写作品文件」两步：`m2v article assets search` 只列候选，`m2v article assets import` 才是唯一入口。旧实现按幕强制必须有候选，且直接下载进作品目录。
**Migration**: 不需要迁移工具；改用文章媒体导入边界，某一幕没有候选不再是失败。

### Requirement: 素材来源与许可留证
**Reason**: 留证记录改为作品内 `assets/media-sources.json`，按内容摘要寻址，来源页、作者、许可、实测尺寸与时长都在同一处；不再有按幕绑定的检索记录文件。
**Migration**: 不需要迁移工具；重新导入素材即生成新的来源记录。

### Requirement: 素材可核验与不可信输入拒绝
**Reason**: 一致性校验并入文章 prepare：分镜引用的素材必须能在导入记录里找到同路径条目，且摘要与实测尺寸一致，否则准备失败。
**Migration**: 不需要迁移工具；替换素材后重新导入并重新 prepare。

### Requirement: 自动剪辑时间轴
**Reason**: 时间轴由 v6 文章 prepare 统一编译：旁白幕按真实语音时长、无旁白镜头按声明帧数或目标剩余时长分配，媒体幕按素材时长校验入点。
**Migration**: 不需要迁移工具；旧 brief 的分幕改写为 v6 幕与 `durationFrames`。

### Requirement: 可选口播与字幕
**Reason**: 逐幕口播改为 v6 分镜的 `narrationSegments`，图片与视频幕允许没有旁白；字幕仍由真实语音边界派生并烧录进画面。
**Migration**: 不需要迁移工具；口播文本搬进对应幕的旁白段。

### Requirement: 可选音床与交付音轨
**Reason**: 音床并入 v6 分镜顶层 `soundtrack`，并与新增的内置/本地音效一起混成单条母版轨；成片音轨规格不变。
**Migration**: 不需要迁移工具；把音床声明从 brief 搬进分镜的 `soundtrack.music`。

### Requirement: 画面、离线渲染与评审门禁
**Reason**: 画面由 `ArticleExplainer` 统一绘制，渲染期素材仍经回环 HTTP 提供；完整预演自动验收、不要求人工评审的规则由文章类型沿用。
**Migration**: 不需要迁移工具；重新 prepare 并生成完整预演。

### Requirement: Pixabay 来源接入
**Reason**: Pexels 与 Pixabay 改为文章可选图库来源，按 provider 名称选择官方地址与凭据变量；图库不再绑定独立类型。
**Migration**: 不需要迁移工具；在 `m2v article assets search --provider pixabay` 中显式选择。

### Requirement: Pixabay 缓存与凭据保护
**Reason**: 24 小时检索缓存与凭据脱敏规则随图库适配层保留，缓存位置改为作品 `outputs/gallery-cache/`，凭据仍只从环境变量读取。
**Migration**: 不需要迁移工具；缓存按需重建。
