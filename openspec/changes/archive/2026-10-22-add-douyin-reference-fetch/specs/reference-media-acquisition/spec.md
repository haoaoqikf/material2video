## Purpose

规定从抖音分享链接获取单条参考素材的输入、下载、留证与校验行为：媒体只用于制作分析，来源与摘要可复核，不进入成片，也不依赖自研签名算法。

## ADDED Requirements

### Requirement: 分享输入解析
系统 SHALL 接受抖音分享文本或裸 URL，并取出其中第一个抖音链接；SHALL 支持 `v.douyin.com` 短链、`douyin.com/video|note/<id>` 与 `iesdouyin.com/share/...`。输入不含抖音链接时 SHALL 停止并给出可用的示例。

#### Scenario: 分享文本
- **WHEN** 用户粘贴包含说明文字、短链和日期的整段分享文本
- **THEN** 系统只提取短链并发起获取，不把说明文字当作 URL

#### Scenario: 非抖音链接
- **WHEN** 用户给出其他站点的链接或不含链接的文本
- **THEN** 系统报告不支持该输入，并展示分享链接的写法

### Requirement: 浏览器取详情
系统 SHALL 通过浏览器页面取得作品详情，SHALL NOT 自行实现或逆向 `a_bogus` 等签名参数。视频作品 SHALL 优先读取页面请求的详情接口；图文作品 SHALL 允许从页面内嵌的 RSC 载荷读取。两条路径都失败时 SHALL 报告最终 URL 与页面标题，并提示使用可见浏览器重试。

#### Scenario: 视频详情
- **WHEN** 页面请求 `/aweme/v1/web/aweme/detail/` 并返回 `aweme_detail`
- **THEN** 系统使用该响应中的作品信息，不再额外请求签名接口

#### Scenario: 图文详情
- **WHEN** 页面没有请求详情接口，但内嵌载荷含有该作品的 `images`
- **THEN** 系统解析内嵌载荷并标记为图文作品

#### Scenario: 取数失败
- **WHEN** 页面被风控、需要登录或详情字段缺失
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
参考素材 SHALL 只用于分析、比对与制作参考，SHALL NOT 被渲染链路当作可复用画面或音频输入；`refs/` 与浏览器 profile SHALL 加入忽略列表，凭据与 cookie 不得进入版本控制。

#### Scenario: 入库检查
- **WHEN** 用户提交仓库改动
- **THEN** 参考素材、`recipe.json`、`metadata.json` 与浏览器 profile 都不出现在暂存内容中
