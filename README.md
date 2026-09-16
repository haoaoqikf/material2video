# article2video

将观点型文章转换成竖屏信息可视化短视频的个人内容生产项目。

**文章是内容层，网页是表现层，视频是最终发布格式。** 项目把抽象观点、因果关系和核心模型
转化为观众可以直观看到的思想结构。

## 这是什么

一个**项目级 Skill**：由 AI 编程工具（Codex、Claude Code、DSH 等）读懂文章并生成动画网页，
再由确定性脚本把网页逐帧渲染成 MP4。AI 不直接生成视频，因此画面可控、可改、可重渲染。

```text
文章 → 分镜 JSON → 配音与字幕准备（可选）→ 动画网页 → 逐帧渲染与音轨合成 → 竖屏 MP4
```

Skill 位于 [`.agents/skills/article2video/`](.agents/skills/article2video/SKILL.md)，
该目录被 Codex 与 DSH 直接识别；Claude Code 需要时可用软链接映射到 `.claude/skills/`。

## 当前状态

已完成**可选自动配音与字幕的视频端到端链路**：

- 分镜 JSON 的结构校验（版本、帧率、尺寸、场景 ID、时长、组件字段、关系图节点引用）；
- 网页与渲染脚本之间的确定性渲染契约 `window.__A2V__`，并提供时间轴运行时
  （帧状态推导、入场动效原语、预览播放控制）；
- 本地 HTTP 预览（网页需 fetch 分镜 JSON，`file://` 下会被同源策略拒绝）；
- Playwright 逐帧截图 + ffmpeg 管道编码，输出 1080 × 1920 / 30fps / H.264 `yuv420p` MP4，
  渲染后自动解码验收帧数与分辨率；
- 一个可直接运行的完整示例：`examples/why-effort-fails/`（5 幕，1350 帧，45 秒）；
- edge-tts 中文自动配音、逐句字幕烧录与 SRT 导出；配音超时自动延长场景；
- 配音按场景缓存，统一 WAV 音轨支持预览播放、拖动和最终 AAC 合成；
- 自动化测试覆盖校验、缓存与失败恢复、字幕时间轴、预览同步和有声/无声渲染。

尚未实现、请勿当作已有能力使用：**背景音乐**、
**AI 自动分镜**（分镜目前由人或 AI 工具直接编写）、**平台发布**。

## 快速开始

```bash
# 1. 安装依赖（首次）
uv sync
uv run playwright install chromium

# 2. 校验分镜
uv run python .agents/skills/article2video/scripts/validate.py examples/why-effort-fails/storyboard.json

# 3. 本地预览（浏览器中确认节奏与排版）
uv run python .agents/skills/article2video/scripts/preview.py examples/why-effort-fails

# 4. 渲染
uv run python .agents/skills/article2video/scripts/render.py \
  --page examples/why-effort-fails/index.html \
  --storyboard examples/why-effort-fails/storyboard.json \
  --out outputs/why-effort-fails.mp4

# 5. 测试
uv run pytest
```

国内网络下安装较慢时可指定镜像：

```bash
UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple uv sync
PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright uv run playwright install chromium
```

## 自动配音与字幕

无声命令保持兼容。要输出有声视频，先按每幕 `narration` 准备媒体：

```bash
uv run python .agents/skills/article2video/scripts/prepare.py \
  --storyboard examples/why-effort-fails/storyboard.json \
  --out-dir outputs/why-effort-fails-media

uv run python .agents/skills/article2video/scripts/preview.py examples/why-effort-fails \
  --media outputs/why-effort-fails-media/media.json

uv run python .agents/skills/article2video/scripts/render.py \
  --page examples/why-effort-fails/index.html \
  --storyboard examples/why-effort-fails/storyboard.json \
  --media outputs/why-effort-fails-media/media.json \
  --out outputs/why-effort-fails-voiced.mp4
```

默认音色 `zh-CN-XiaoxiaoNeural`、语速 `+0%`；可用 `--voice`、`--rate=-10%` 调整，
`--force` 强制重新合成。首次合成需要联网，无需 API key；已有缓存可离线重新准备与导出。
输出 MP4 内含字幕和 AAC 配音，同时生成同名 SRT。背景音乐尚未实现。

原分镜不被覆盖；原场景时长作为最短时长，配音较长时自动延长并留 300ms 收尾。
示例原长 45 秒，本机默认配音实测 46.27 秒；在线服务结果可能变化，以媒体清单为准。
修改分镜后重新执行 prepare（未改变的口播命中缓存）。详细接口和错误处理见
[配音与字幕](.agents/skills/article2video/references/media-contract.md)。

## 制作一支新视频

1. 在 `videos/<slug>/` 下新建目录，写入 `article.md` 与 `storyboard.json`；
2. 复制 `examples/why-effort-fails/index.html` 作为模板，改写视觉与场景；
3. 依次执行上面的校验、预览、渲染命令。

分镜字段、网页契约与排版规范见 Skill 内的
[渲染契约](.agents/skills/article2video/references/render-contract.md)、
[分镜脚本结构](.agents/skills/article2video/references/storyboard-schema.md)、
[竖屏视觉规范](.agents/skills/article2video/references/visual-spec.md)。

## 关键约束

- **单一真源**：文案与原始时长写在 `storyboard.json`；启用配音时，网页和脚本共用媒体清单中的派生时长；
- **帧驱动**：画面只由帧号推导。禁止 CSS `animation`/`transition`、`Date.now()`、
  `Math.random()`，否则逐帧截图会闪烁且不可复现；
- **性能取舍**：中间帧默认用 JPEG q98 采集（1080 × 1920 实测约 66ms/帧，PNG 约 225ms），
  需要逐像素比对时用 `--capture-format png`。

## 文档导航

- [项目规划](docs/PROJECT_PLAN.md)：处理链路、组件清单与阶段路线（未来方向的权威来源）
- [协作约定](AGENTS.md)：中文协作、Git 与交付规则
- [Skill 主文档](.agents/skills/article2video/SKILL.md)：完整工作流与排查手册

本仓库未配置远端，不含账号系统、云端任务队列或自动发布能力。
