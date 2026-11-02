## MODIFIED Requirements

### Requirement: 详情提取路径

系统 SHALL 优先使用 yt-dlp 的 Douyin 提取器读取作品详情与可下载地址；用户可提供 Netscape cookie 文件（`--cookies`）以改善提取条件。yt-dlp 无法提取时，系统 MAY 退回浏览器页面解析：页面自行完成 `a_bogus` 等签名，系统 SHALL NOT 自行实现或逆向签名参数。视频作品 SHALL 优先读取页面请求的详情接口；图文作品 SHALL 允许从页面内嵌的 RSC 载荷读取。两条路径都失败时 SHALL 报告最终 URL 与页面标题，并提示使用可见浏览器重试。

#### Scenario: yt-dlp 提取成功
- **WHEN** yt-dlp 能读取该作品并返回视频地址
- **THEN** 系统使用 yt-dlp 的规范化详情，不启动浏览器

#### Scenario: yt-dlp 提取失败
- **WHEN** 平台要求签名、cookie 不足或 yt-dlp 提取器失效
- **THEN** 系统输出明确日志并退回浏览器解析；用户显式禁用兜底时失败并提示提供 `--cookies`

#### Scenario: 视频详情兜底
- **WHEN** 页面请求 `/aweme/v1/web/aweme/detail/` 并返回 `aweme_detail`
- **THEN** 系统使用该响应中的作品信息，不再额外请求签名接口

#### Scenario: 图文详情兜底
- **WHEN** 页面没有请求详情接口，但内嵌载荷含有该作品的 `images`
- **THEN** 系统解析内嵌载荷并标记为图文作品

#### Scenario: 取数失败
- **WHEN** yt-dlp 与浏览器都无法取得详情，或页面被风控、需要登录
- **THEN** 系统失败退出，输出最终 URL、标题与 `--headed` 重试提示，不生成部分素材
