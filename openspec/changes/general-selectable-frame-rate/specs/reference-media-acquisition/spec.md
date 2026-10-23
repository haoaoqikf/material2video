## MODIFIED Requirements

### Requirement: 参考音轨提取
`m2v ref audio <参考目录> --project <作品目录> --user-authorized <授权说明>` SHALL 先按 `recipe.json` 校验参考目录，再从视频的第一条音频流提取完整音轨到 `<作品>/assets/audio/<名称>.wav`（PCM 16-bit、48 kHz、保留源声道），并写同名 `.provenance.json`。`<名称>` 省略时 SHALL 为 `ref-<作品ID>`。

provenance SHALL 记录参考作品 ID、类型、作者、文案、来源链接、最终链接、抓取时间、参考视频相对路径与 SHA-256/字节数，以及提取音频的路径、SHA-256、字节数、采样数、时长、采样率、声道、位深、60 fps 总帧数与取整方式。provenance SHALL 记录提取时间与 ffmpeg 版本，并 SHALL 记录用户授权原文、「未取得书面许可、用户指定复用不构成许可」的许可状态、第三方音乐风险与署名。

命令 SHALL 输出按作品实际fps向上取整的总帧数（`(samples × fps + sampleRate - 1) // sampleRate`）；尚未创建分镜时 SHALL 使用作品声明或通用默认30 fps。原始留证的60帧分析信息 SHALL 保留。命令 SHALL 提供时间轴帧率与可直接粘贴的 `soundtrack.music` 片段（`gainDb: 0`、`loop: false`、`fadeInMs: 0`、`fadeOutMs: 0`）。音频采样数对应时长超过600秒时 SHALL 拒绝。

命令 SHALL NOT 修改参考目录。目标已存在时 SHALL 默认拒绝；只有参考视频摘要、音频摘要与字节数均一致时才可复用，否则 SHALL 要求 `--force`，并在 `--force` 时同时替换音频与 provenance。名称含路径分隔符、绝对路径、`..`、Windows 保留名或已带 `.wav` / `.provenance.json` 后缀时 SHALL 拒绝。参考目录校验失败、作品不是 `general`、参考作品不是视频、视频没有音频流时 SHALL 失败且不留下临时或部分文件。

#### Scenario: 参考音轨时间轴帧率
- **WHEN** 为30或60 fps的通用作品提取参考音轨
- **THEN** 留证保留60 fps分析帧数，命令粘贴片段按作品帧率给出编排帧数和时间轴fps

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
