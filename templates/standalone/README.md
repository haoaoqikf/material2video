# 独立视频工程

本目录拥有运行源码、依赖锁文件、字体恢复和成片导出能力，可以复制、改名并放到任意目录。生成后由作品维护本地代码；主项目组件和模板后续更新不会自动改变本作品。

环境：Python 3.11+、uv、Node.js 22.12+、pnpm 10.15.0。本模板目前实测 Python 3.12、Node.js 22.23.2 和 Windows。三维作品另声明实际GPU／驱动前提，不承诺跨硬件逐字节一致。

作品内 `.npmrc` 使用较短的 pnpm 虚拟库目录与目录名，减少 Windows 深层作品路径叠加依赖名后出现文件无法读取的风险；它随初始化复制到作品，不借用共享依赖目录。已有工程调整此配置后须重新执行 `pnpm install`，让实际依赖布局与配置一致。

## 恢复与运行

```powershell
pnpm install --frozen-lockfile --ignore-workspace
uv sync --frozen
pnpm run setup --download --install-browser
pnpm run validate
pnpm run build
pnpm run render
pnpm run preview --serve
```

`setup --download` 允许按 `fonts/registry.json` 的登记恢复缺失字体；有完整本地缓存时可省略。已有文件摘要不符会失败，不覆盖、不接受内容漂移。`--install-browser` 恢复当前Playwright版本对应的完整Chromium；合成与场景采集使用这一浏览器，导出时不隐式下载另一浏览器。

纪实口播默认使用本地 Kokoro，其他类型也可在 `project.json` 声明 `tts.backend: "kokoro"`。按旁白选择并记录音色后，安装可选依赖并在作品内恢复模型：

```powershell
uv sync --frozen --extra kokoro
python models/fetch.py --download --voice zf_027
```

`models/registry.json` 固定模型 revision、文件摘要与许可，`models/` 下的二进制由 `.gitignore` 排除；`setup --download`、`validate` 与准备前检查会按登记恢复或校验。数字与拉丁字母旁白当前不支持，需改写为中文或改用 `edge-tts`。

使用 Qwen3-TTS 声音克隆（`tts.backend` 为 `qwen3-tts`，音色形如 `clone_tuixiu`）时，安装可选依赖并在作品内恢复主模型与 stable-ts 对齐模型：

```powershell
uv sync --frozen --extra qwen3-tts
python models/qwen3-tts/fetch.py --download --voice clone_<slug>
python models/qwen3-tts/fetch.py --check --voice clone_<slug>
```

`models/qwen3-tts/registry.json` 同时登记参考音色档案（参考音频、参考文本、语言、来源、用户授权与 SHA256）。参考音色是作品资产，不能从模型仓库恢复；更换参考音频或参考文本会改变语音缓存键。数字与拉丁字母旁白当前同样不支持。

正式渲染会检查当前准备记录，必要时先准备，然后逐帧采集、合成字幕和转场、混音并验证媒体，输出 `outputs/video.mp4` 及旁车。它生成技术候选，不自动代表研究、视听品质或独立审核完成。预览服务使用同一本地场景与合成实现，第一次需要准备场景片段；随后可以播放、暂停和定位。

只准备材料可运行 `pnpm run video:prepare`。该脚本显式命名，避免包管理器的安装生命周期自动触发视频制作。也可以直接执行 `uv run --frozen python scripts/video.py prepare`。检查片段可使用 `pnpm run preview --limit-frames 30`；此命令写片段视频，网页交互预览使用 `--serve`。

## 创作与资源

固定保留 RESEARCH.md、DESIGN.md 和每个 design/scenes/<scene-id>.md，默认记录目标、画面与注意力、实现、验证与未知四问；起步材料不代表正式美术通过。

场景入口在 `scenes/`；本地时间与资源就绪接口在 `src/code-scene/`；最终合成在 `src/scene-film/`。修改 `project.json`、`storyboard.json` 和场景即可创作。按作品需要自行采用本地组件或在 `package.json` 声明精确版本的第三方库，并更新本作品锁文件、来源与许可记录。没有主项目SDK或跨目录源码别名。

`src/assets/fonts.json` 声明实际注册字体，来源与摘要在 `fonts/registry.json`，许可在 `fonts/licenses/`。使用 Kokoro 配音时，来源、revision、摘要与许可以 `models/registry.json` 为准，许可文本在 `models/licenses/`；使用 Qwen3-TTS 时以 `models/qwen3-tts/registry.json` 为准，许可文本在 `models/qwen3-tts/licenses/`。媒体使用作品内 `assets/media-sources.json` 登记；存在 `assets/fetch.py` 或 `assets/sound-recipe.json` 时，setup调用本地恢复入口。渲染使用已经恢复的本地快照；更新数据或重新合成旁白属于显式准备操作。

当前基础模板没有预装三维、图表、公式或金融／建筑／汽车准备模块；需要时将所采用的实现、依赖及资源完整落到作品内。缺失采用模块时必须先补齐，不通过主项目回退。

## 原生场景试制与技术检查

```powershell
pnpm run sample --entry scenes/opening.tsx --kind static --duration-seconds 3 --frame 30
pnpm run qa
pnpm test
```

sample 使用 kind=static 时输出同源网页、指定关键帧和输入记录，不调用视频编码；kind=motion 另生成完整局部视频，不要求全片配音。`pnpm run qa`检查候选的技术信号；画面判断和制作完成仍需实际复核。资源、依赖、源码或配置改变后，旧准备和对应样品需要重新验证。

`runtime` 字段是可选的制作工具执行协议：默认工程提供本地命令数组，便于外部工具调用同一实现。直接运行本工程不需要安装主项目，也不需要外部制作管理服务。

源码、配置、锁文件、配方和许可可纳入作品自身Git；媒体、字体二进制、依赖、缓存和outputs由本地 `.gitignore` 排除。
