## ADDED Requirements

### Requirement: Pixabay 来源接入

系统 SHALL 允许 `provider.name= pixabay` 检索图片与视频；仅声明名称时 MUST 使用 `https://pixabay.com/api` 和 `M2V_PIXABAY_API_KEY`，显式覆盖仍有效。未选择来源时 MUST 保留 Pexels 默认行为。Pixabay 素材 MUST 留存来源页、作者、Content License 及所下载版本的尺寸和视频时长，下载媒体时 MUST NOT 向 CDN 发送 API Key。

#### Scenario: 选择 Pixabay

- **WHEN** 作品选择 Pixabay 且对应环境变量已设置
- **THEN** 图片和视频可进入既有检索、下载与留证流程，使用 Pixabay 对应默认地址与凭据

#### Scenario: 兼容旧作品

- **WHEN** 作品未声明 provider.name
- **THEN** 仍使用 Pexels 默认地址与凭据变量

### Requirement: Pixabay 缓存与凭据保护

系统 SHALL 将成功的 Pixabay 检索响应缓存 24 小时，重复相同请求 MUST 使用有效缓存，过期或损坏时 MUST 重取。Key MUST 只从环境变量读取，MUST NOT 明文出现在缓存、文件名、检索记录或错误消息中；HTTP 错误与网络失败 MUST 报告可操作的脱敏信息。

#### Scenario: 重复查询

- **WHEN** 相同作品的相同查询在 24 小时内再次执行且缓存有效
- **THEN** 不再请求检索 API，仍可下载入选素材并生成来源记录

#### Scenario: 接口失败

- **WHEN** Pixabay 返回 HTTP 错误或网络连接失败
- **THEN** 检索失败并报告错误类别或 HTTP 状态码，错误消息不含 Key
