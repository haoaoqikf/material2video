# reference-media-acquisition Specification

## Purpose

规定从抖音分享链接获取单条参考素材的输入、下载、留证与校验行为：媒体默认只用于制作分析，来源与摘要可复核；用户明确授权时可提取音轨到作品并留证，参考画面仍不进入成片；不依赖自研签名算法。

## Requirements

### Requirement: 分享输入解析
系统 SHALL 接受抖音分享文本或裸 URL，并取出其中第一个抖音链接；SHALL 支持 `v.douyin.com` 短链、`douyin.com/video|note/<id>` 与 `iesdouyin.com/share/...`。输入不含抖音链接时 SHALL 停止并给出可用的示例。

#### Scenario: 分享文本
- **WHEN** 用户粘贴包含说明文字、短链和日期的整段分享文本
- **THEN** 系统只提取短链并发起获取，不把说明文字当作 URL

#### Scenario: 非抖音链接
- **WHEN** 用户给出其他站点的链接或不含链接的文本
- **THEN** 系统报告不支持该输入，并展示分享链接的写法

### Requirement: 详情提取路径

系统 SHALL 优先使用 yt-dlp 的 Douyin 提取器读取作品详情与可下载地址；用户可提供 Netscape cookie 文件（`--cookies`）以改善提取条件。yt-dlp 无法提取时，系统 MAY 退回浏览器页面解析：页面自行完成 `a_bogus` 等签名，系统 SHALL NOT 自行实现或逆向签名参数。视频作品 SHALL 优先读取页面请求的详情接口；图文作品 SHALL 允许从页面内嵌的 RSC 载荷读取。两条路径都失败时 SHALL 报告最终 URL 与页面标题，并提示使用可见浏览器重试。

#### Scenario: yt-dlp 提取成功
- **WHEN** yt-dlp 能读取该作品并返回视频地址
- **THEN** 系统使用 yt-dlp 的规范化详情，不启动浏览器

#### Scenario: yt-dlp 提取失败
- **WHEN** 平台要求签名、cookie 不足或 yt-dlp 提取器失效
- **THEN** 系统输出明确日志并退回浏览器解析；用户显式禁用兜底时失败并提示提供 `--cookies`

#### Scenario: 视频详情
- **WHEN** 页面请求 `/aweme/v1/web/aweme/detail/` 并返回 `aweme_detail`
- **THEN** 系统使用该响应中的作品信息，不再额外请求签名接口

#### Scenario: 图文详情
- **WHEN** 页面没有请求详情接口，但内嵌载荷含有该作品的 `images`
- **THEN** 系统解析内嵌载荷并标记为图文作品

#### Scenario: 取数失败
- **WHEN** yt-dlp 与浏览器都无法取得详情，或页面被风控、需要登录
- **THEN** 系统失败退出，输出最终 URL、标题与 `--headed` 重试提示，不生成部分素材

### Requirement: 媒体下载
系统 SHALL 把视频保存为 `video.mp4`，把图文逐张保存到 `images/`；SHALL 校验响应非空且文件头与媒体类型一致，SHALL NOT 把 HTML 风控页当作媒体保存。视频 SHALL 优先选择 h264 编码中码率最高的直链。

#### Scenario: 视频直链
- **WHEN** 详情给出多个 h264 码率档位
- **THEN** 系统按码率从高到低尝试，成功一档即停止

#### Scenario: 全部直链失败
- **WHEN** 所有候选直链都返回错误或非媒体内容
- **THEN** 系统清理未完成的临时文件并报告每次尝试的失败原因

#### Scenario: 图文作品
- **WHEN** 详情中的 `images` 非空
- **THEN** 系统按顺序下载每张图片，并优先使用无水印地址

### Requirement: 来源与摘要留证
每个参考素材目录 SHALL 包含 `metadata.json` 与 `recipe.json`。`metadata.json` SHALL 记录作品 ID、类型、作者、文案、发布时间、来源链接与抓取时间；`recipe.json` SHALL 记录每个媒体文件的相对路径、SHA-256、字节数与可实测的尺寸。参考素材目录 SHALL 位于不进入版本控制的 `refs/` 下。

#### Scenario: 新下载
- **WHEN** 下载成功
- **THEN** 目标目录同时存在媒体、`metadata.json` 与 `recipe.json`，且摘要对应实际文件

#### Scenario: 已存在
- **WHEN** 目标目录已存在且 `recipe.json` 校验通过
- **THEN** 系统报告已存在并复用，不重复下载

#### Scenario: 已存在但摘要不符
- **WHEN** 目标目录存在但文件缺失或被替换
- **THEN** 系统停止并提示使用 `--force` 显式替换，不静默覆盖

### Requirement: 留证校验
`m2v ref verify <目录>` SHALL 按 `recipe.json` 重新计算每个文件的 SHA-256 与字节数，并 SHALL 在缺失、尺寸变化或不符时失败并指出具体文件。

#### Scenario: 校验通过
- **WHEN** 目录内文件与 `recipe.json` 完全一致
- **THEN** 命令报告每个文件通过并退出 0

#### Scenario: 文件被替换
- **WHEN** 任一文件内容或字节数变化
- **THEN** 命令指出该文件并失败，不修改任何文件

### Requirement: 使用边界
参考素材 SHALL 只用于分析、比对与制作参考；默认 SHALL NOT 被渲染链路当作可复用画面或音频输入。`refs/` 与浏览器 profile SHALL 加入忽略列表，凭据与 cookie 不得进入版本控制。

用户明确指定复用单条参考作品音频时，系统 SHALL 允许通过 `m2v ref audio` 把该作品的音频提取为作品目录内的独立音频资产；该资产 SHALL 只用于该作品的 `soundtrack.music`，参考视频画面 SHALL NOT 进入成片，渲染链路 SHALL NOT 直接读取 `refs/`。例外 SHALL 逐条记录用户授权原文、来源、摘要与许可状态，不得扩展为默认能力。

#### Scenario: 默认边界
- **WHEN** 用户只执行 `ref fetch` / `ref verify`
- **THEN** 参考媒体不进入任何作品的渲染输入

#### Scenario: 用户明确指定复用
- **WHEN** 用户明确要求复用某一条参考作品的完整音频，并对该作品执行 `m2v ref audio`
- **THEN** 系统只提取音频到作品 `assets/audio/`，写入来源与摘要 provenance，参考视频画面仍不进入成片

#### Scenario: 入库检查
- **WHEN** 用户提交仓库改动
- **THEN** 参考素材、`recipe.json`、`metadata.json`、提取音频与浏览器 profile 都不出现在暂存内容中

### Requirement: 参考音轨提取
`m2v ref audio <参考目录> --project <作品目录> --user-authorized <授权说明>` SHALL 先按 `recipe.json` 校验参考目录，再从视频的第一条音频流提取完整音轨到 `<作品>/assets/audio/<名称>.wav`（PCM 16-bit、48 kHz、保留源声道），并写同名 `.provenance.json`。`<名称>` 省略时 SHALL 为 `ref-<作品ID>`。

provenance SHALL 记录参考作品 ID、类型、作者、文案、来源链接、最终链接、抓取时间、参考视频相对路径与 SHA-256/字节数，以及提取音频的路径、SHA-256、字节数、采样数、时长、采样率、声道、位深、60 fps 总帧数与取整方式。provenance SHALL 记录提取时间与 ffmpeg 版本，并 SHALL 记录用户授权原文、「未取得书面许可、用户指定复用不构成许可」的许可状态、第三方音乐风险与署名。

命令 SHALL 输出按作品实际fps向上取整的总帧数（`(samples × fps + sampleRate - 1) // sampleRate`）与时间轴fps，以及可直接粘贴的 `soundtrack.music` 片段（`gainDb: 0`、`loop: false`、`fadeInMs: 0`、`fadeOutMs: 0`）。尚无分镜时使用项目声明帧率或三类作品默认30 fps。原始留证中的60 fps分析帧数 MUST 保留。音频时长超过600秒时 SHALL 拒绝。

命令 SHALL NOT 修改参考目录。目标已存在时 SHALL 默认拒绝；只有参考视频摘要、音频摘要与字节数均一致时才可复用，否则 SHALL 要求 `--force`，并在 `--force` 时同时替换音频与 provenance。名称含路径分隔符、绝对路径、`..`、Windows 保留名或已带 `.wav` / `.provenance.json` 后缀时 SHALL 拒绝。参考目录校验失败、作品类型不在三类之中、参考作品不是视频、视频没有音频流时 SHALL 失败且不留下临时或部分文件。

#### Scenario: 参考音轨时间轴帧率
- **WHEN** 为30或60 fps的通用作品提取参考音轨
- **THEN** provenance保留60 fps分析帧数，命令片段按作品帧率给出编排帧数及时间轴fps

#### Scenario: 成功提取
- **WHEN** 参考目录校验通过、视频含音频流，且命令提供 `--user-authorized`
- **THEN** 作品 `assets/audio/` 下出现 WAV 与 provenance，摘要和时长与实际文件一致，参考目录不变

#### Scenario: 缺少授权说明
- **WHEN** 未提供 `--user-authorized`
- **THEN** 命令拒绝执行，不写任何音频

#### Scenario: 参考摘要不符
- **WHEN** 参考视频被替换或缺失
- **THEN** 命令在提取前失败并指出具体文件

#### Scenario: 覆盖保护
- **WHEN** 目标音频已存在且来源或摘要不一致
- **THEN** 命令拒绝覆盖；只有 `--force` 才同时替换音频与 provenance

#### Scenario: 无音频流
- **WHEN** 参考视频没有音频流
- **THEN** 命令失败并说明该作品无法复用音频

#### Scenario: 名称越界
- **WHEN** 名称为 `../escape`、`a/b`、`CON` 或以 `.wav` 结尾
- **THEN** 命令拒绝执行，`assets/audio/` 外不产生文件
