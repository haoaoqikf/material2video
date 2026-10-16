## Why

Windows 上的 `tempfile` 临时目录带一份收紧的 ACL（只有 `SYSTEM`、`Administrators` 与 `OWNER RIGHTS`，且关闭继承），产物 `replace` 到最终位置会把这份 ACL 一起带走：当前账号仍能读写，但以标准权限运行的打包应用打不开。用户双击成片时 Windows 11「媒体播放器」报 `0x80070005 你没有访问该文件的权限`。

这个缺陷 2026-10-09 已在金融类型上修过一次，但修法只落在金融与住宅的渲染模块里，且是「记得调用一次」。通用类型的成片与溯源文件、混音主音轨、代码场景录制片段、导入素材、配音缓存与打包缓存条目仍然只搬运不修复；工作区实测 2031 个产物处于不可读状态，其中包含三个固定示例的 `video.mp4`。所以这次不是再补一处调用，而是把「搬运 + 修复」收成一个交付原语，并给交付结果加上复核。

## What Changes

- 新增交付原语 `security.deliver` 与 `security.deliver_directory`：搬运到最终位置与交回所在目录继承权限是同一个动作，交付后复核目标本身。
- 所有从临时目录搬出的产物改走交付原语：通用成片与溯源记录、混音主音轨、代码场景录制片段、导入素材、配音缓存、打包缓存目录；金融与住宅渲染原有的单独调用合并进原语。
- 复核仍缺少标准权限进程可用的授权时，日志报告目标与所在目录，指出「父目录本身就是收紧的」这一根因。
- 新增回归用例：真实 `icacls` 复现缺陷、各交付路径确实走交付原语、交付结果可被标准权限进程打开。
- 修复工作区已有不可读产物。

## Capabilities

### New Capabilities
- （无）

### Modified Capabilities
- `modular-video-production`: 新增「交付产物的访问权限」要求，统一规定从临时目录搬出的产物必须继承所在目录权限、必须成对搬运与修复，并在交付后复核。
- `react-code-scenes`: 「实时录制及复用」补上录制片段落盘后的交付权限。
- `article-media-assets`: 「公开媒体导入」补上采用素材落盘后的交付权限。

## Impact

- `src/m2v/core/security.py`：新增 `deliver`、`deliver_directory` 与交付复核，模块说明改述为「交付路径统一走交付原语」。
- 交付点：`types/general/explainer_render.py`、`types/general/explainer_prepare.py`、`types/general/code_scenes.py`、`types/general/media_assets.py`、`types/financial/financial_render.py`、`types/housing/housing_render.py`、`engine/tts.py`、`engine/bundle_cache.py`。
- 测试：新增 `tests/test_delivery_access.py`。
- 文档：`.agents/skills/material2video/references/paths-and-outputs.md` 补充交付权限说明。
- 不影响成片编码参数、分镜结构、模板集合与渲染契约；非 Windows 平台无行为差异。
