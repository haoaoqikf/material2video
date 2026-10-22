## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: 参考音轨提取
`m2v ref audio <参考目录> --project <作品目录> --user-authorized <授权说明>` SHALL 先按 `recipe.json` 校验参考目录，再从视频的第一条音频流提取完整音轨到 `<作品>/assets/audio/<名称>.wav`（PCM 16-bit、48 kHz、保留源声道），并写同名 `.provenance.json`。`<名称>` 省略时 SHALL 为 `ref-<作品ID>`。

provenance SHALL 记录参考作品 ID、类型、作者、文案、来源链接、最终链接、抓取时间、参考视频相对路径与 SHA-256/字节数，以及提取音频的路径、SHA-256、字节数、采样数、时长、采样率、声道、位深、60 fps 总帧数与取整方式。provenance SHALL 记录提取时间与 ffmpeg 版本，并 SHALL 记录用户授权原文、「未取得书面许可、用户指定复用不构成许可」的许可状态、第三方音乐风险与署名。

命令 SHALL 输出按 60 fps 向上取整的总帧数（`(samples × 60 + sampleRate - 1) // sampleRate`）与可直接粘贴的 `soundtrack.music` 片段（`gainDb: 0`、`loop: false`、`fadeInMs: 0`、`fadeOutMs: 0`）。总帧数超过 36000 时 SHALL 拒绝。

命令 SHALL NOT 修改参考目录。目标已存在时 SHALL 默认拒绝；只有参考视频摘要、音频摘要与字节数均一致时才可复用，否则 SHALL 要求 `--force`，并在 `--force` 时同时替换音频与 provenance。名称含路径分隔符、绝对路径、`..`、Windows 保留名或已带 `.wav` / `.provenance.json` 后缀时 SHALL 拒绝。参考目录校验失败、作品不是 `general`、参考作品不是视频、视频没有音频流时 SHALL 失败且不留下临时或部分文件。

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
