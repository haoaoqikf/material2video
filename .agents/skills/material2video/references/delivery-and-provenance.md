# 交付与溯源

> **适用范围：** 本文描述从候选到交付的收口规则：交付文件的访问权限、成片溯源、渲染性能
> 报告，以及一次全片生成与候选保留。目录归属、默认输出与清理规则见
> [目录约定与输出路径](paths.md)，准备记录字段见[准备记录与字幕](prepared-and-subtitles.md)；
> 制作门、适用条件、证据失效见[评审契约](review-contract.md)。旧版副本处理见[修订入口](video-revision.md#执行顺序与已有命令)。

## 交付权限

所有从临时目录搬到最终位置的产物都在搬运的同时交回所在目录的继承权限：成片、溯源记录、
混音主音轨、代码场景录制片段、导入素材与缓存条目。成片与准备音轨都先写在临时目录里，
再移动到最终位置：Windows 的 `tempfile.TemporaryDirectory()` 会创建一个**刻意收紧**的目录，
ACL 只有 `SYSTEM` / `Administrators` / `OWNER RIGHTS` 且关闭继承；文件把这份 ACL 带到最终位置后，
管理员账号自己仍能读写，但**以标准权限运行的打包应用会读不到**——Windows 11 新版「媒体播放器」
打开成片时报 `0x80070005 你没有访问该文件的权限`，而 ffmpeg 与浏览器上传都不受影响，
所以问题只在用户双击播放时暴露。

`src/m2v/core/security.py` 在文件落到最终位置后调用 `grant_inherited_access()`
（`icacls /reset`），让文件重新遵循父目录的继承规则；`m2v render` 与 `m2v prepare`
在每个交付文件上都会执行一次，失败只记警告日志、不影响已经渲染好的成片。

- 交付统一走 `m2v.core.security.deliver`（整个目录用 `deliver_directory`），不要手写 `Path.replace`。
- 交付后复核目标本身；仍缺少普通用户授权条目时日志会报告目标与所在目录，指出问题在父目录。
- 复核判据是 `security.has_usable_access`；非 Windows 平台不存在这个问题，`icacls` 为 Windows 自带命令。

排查时注意两点，否则很容易误判为「文件没问题」：

- 缺陷在 `%TEMP%` 下**不会复现**——那里的临时目录额外继承了一条宽松的
  `CREATOR OWNER`，会把问题掩盖掉；用例必须把临时目录建在目标目录里；
- `has_usable_access()` 只解析 icacls 的**授权行**。icacls 输出的第一行含文件路径，
  而用户名往往就在路径里（`C:\Users\<名>\...`），按整份输出做子串匹配会一律
  误判为「权限正常」。

## 成片溯源

渲染成功后会在成片旁写一份溯源，例如 `video.mp4` → `video.provenance.json`。
它回答的是「这支片子是哪一版资产渲的」，因为成片不入库、也没有别的东西会提醒你它
已经落后于源码：实测发生过两支作品的成片比动效重写早了几个小时，仍然带着被修掉的
旧曲线，看上去却仍然是「上次验收通过」的样子。只有正式导出写溯源，预演不写。
`schemaVersion` 当前为 1。三类共用同一形状，例如：

```json
{
  "schemaVersion": 1,
  "type": "data-evolution",
  "projectId": "<作品 ID>",
  "preparedFingerprint": "…",
  "compositionId": "SceneFilm",
  "inputs": {"storyboard": "…", "implementation": "…", "file:request.json": "…", "renderer": "…"},
  "durationInFrames": 1800,
  "fps": 30,
  "width": 1080,
  "height": 1920
}
```

`type` 是三类之一；`preparedFingerprint` 对应 `outputs/prepared.json`。 `inputs` 记录分镜、实现、来源文件、声音与可达渲染代码的摘要；有声作品另写声音与交付字段。结构化来源经相同的准备记录与溯源机制绑定，不另写专项格式。

有声作品的 `audio.masterSampleRate` 与 `audio.masterChannels` 读取实际母版WAV头；旁白为单声道不代表混音母版也是单声道。不要把这些来源字段与最终AAC的采样率、声道数混用。

溯源**不参与交付判定**，它只是「这个成片是哪次准备渲的」的答案；判定由正式渲染
独立复核准备指纹与文件摘要完成。

几条口径值得记住：

- **只指纹真正影响画面的东西**：`inputs.renderer` 是 composition 入口沿 import 可达的
  文件摘要——改一个没被任何组件用到的文件不该让成片报落后，而改一个被引用的组件文件
  就该报。第三方依赖由 `package.json` 与锁文件覆盖：依赖版本变了，成片同样判落后。否则闸门会变成噪音，
  人开始忽略它——那等于没有闸门。
- **文本资产按 LF 归一化后哈希，其余按原字节**：git 的换行归一化会在工作区静默翻转
  行尾，只差行尾的文件不该被判成落后（否则会出现人怎么重渲都消不掉的假落后）。
  归一化清单是 `.css` / `.mjs` / `.json` / `.html` / `.svg` / `.md` 一类文本后缀；
  `.ts` / `.tsx` 不在其中，按原字节哈希。
- **键记文件在哪，不记引用怎么写**：仓库 `web/` 别名目录里的文件一律记
  `/__m2v_web__/…` 键，作品自己的文件记 `__m2v_workspace__/…` 键，两者都不在时
  只记文件名。复核时按同一套规则反解，因此换机器、换目录、换内容根都读得回来，
  也不需要再传 `--content-root`。

当前没有自动复核溯源的命令：溯源只如实记录这批指纹，判落后要拿它记的值与当前值比对。
旧的 `version: 3/4` 溯源（含 `captureFormat`、`assets.files` 与页面路径）属于已删除的
网页截图链路，只作历史参考，不要拿来判断当前成片。

## 渲染性能报告

同一支成片还写一份 `<同名>.performance.json`（同样不入库），回答的是另一类问题：
这次渲染慢在哪、缓存有没有命中、用了几个并发、开了几次浏览器。它**不参与交付判定**，
写不进去只告警，不会让一次已经验收通过的渲染失败。每次 Remotion 渲染在成片同级写一份
结构化报告（已被 `.gitignore` 忽略）：

```json
{
  "version": 1,
  "entry": "render",
  "generatedAt": "2026-09-20T12:00:00+00:00",
  "output": "video.mp4",
  "storyboard": "<分镜的绝对路径>",
  "frames": 1200, "fps": 60, "width": 1080, "height": 1920,
  "concurrency": 1,
  "stages": { "cache": 0.03, "bundle": null, "metadata": 4.1, "render": 91.8, "mux": 0.5, "probe": 1.4 },
  "skipped": ["bundle"],
  "executedSeconds": 97.8,
  "totalSeconds": 98.4,
  "environment": {
    "platform": "Windows-11-10.0.26300-SP0", "machine": "AMD64", "processor": "…",
    "cpuCount": 18, "memoryGiB": 31.6,
    "python": "3.12.10", "node": "v22.23.2", "remotion": "4.0.526",
    "ffmpeg": "ffmpeg version …", "executable": "…/python.exe"
  },
  "cache": { "status": "hit", "key": "…", "detail": "命中并复核了 55 个产物文件" },
  "session": { "browsersOpened": 1, "handshakeSeconds": 4.1 }
}
```

字段包括各阶段秒数（`cache` / `bundle` / `metadata` / `render` / `mux` / `probe`）、
跳过阶段列表、缓存命中状态与键、实际并发、帧数与分辨率、`entry`（`render` 还是 `preview`）、
`generatedAt` / `executedSeconds` / `totalSeconds`，以及 `environment`（平台、CPU 与内存、
Python / Node / Remotion / ffmpeg 版本）——两次报告的数字只有在这个前提下才可比。

`entry` 标明数据来自哪个入口（`preview` 或 `render`），因为正式门禁下的数字与限帧
试渲染不同源，混着比会得出错误结论。`environment` 用来解释「同一份材料在两台机器上
为什么快慢不同」。各类型还会往报告根上补几个自己的字段（例如讲解渲染的
`layoutCheckSeconds`、通用视频的 `session.browsersOpened` / `observedPeakMemoryBytes`）。

`render` 已包含编码（两者在 Remotion 内部重叠），因此没有独立的 `encode` 阶段；
未执行的阶段是 `null` 且列在 `skipped` 里，不用 `0` 冒充实测。报告是附加信息：
写失败只告警，不会让一次已经验收通过的渲染失败。

## 一次全片生成与候选保留

`outputs/candidates/<指纹>.mp4` 与同名旁车保存完整候选，`outputs/delivery.json` 保存当前输入/实现/参数绑定、文件摘要、状态及失败原因。检查或交付重试必须复用摘要有效的候选，不能重新编码；旧 preview-record.json 不再参与门禁。三类作品的正式输出统一为 `outputs/video.mp4`。

异常退出留下 `delivery.lock` 时，先确认没有制作进程再移除锁。

## 周期记录核验

周期历史在每次扫描内固定归属并逐行校验，结束时重新读取完整周期身份；检测到扫描期间的周期变化则拒绝该次结果。即使只读查询缓存已预热，也保留这次收尾复查。性能优化不跨操作缓存来源或凭据，不省略历史行。
