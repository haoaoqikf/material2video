# 作品集

[首页](index.html)展示五部示例。页面直接由静态服务器托管，加载本地样式和媒体。源码、教程和架构链接返回 GitHub 仓库。

从仓库根目录启动静态服务器，再打开 `http://127.0.0.1:8000/`。

```text
python -m http.server 8000 --bind 127.0.0.1 --directory docs/site
```

## 重新生成展示资源

需要 Python 3.11 或更新版本、Pillow、PATH 上带有 `libx264` 的 `ffmpeg` 和 `ffprobe`。本次使用 FFmpeg 9.0.2 和 Pillow 13.0.0。命令从仓库根目录运行。字体已恢复时可省略第一条。

```text
uv run python fonts/fetch.py
python -m pip install "Pillow==13.0.0"
python scripts/build-site-assets.py
```

[生成脚本](../../scripts/build-site-assets.py)读取太阳系、运气、复利、美国科技里程碑四个示例现成的 `outputs/video.mp4`，以及《全球市值前十》的 `outputs/previews/video.mp4`。市值预览对应完整编排中的 70.8 秒起、58 帧窗口，取该预览内部 0.9 秒的真实画面。片段和海报时点及选用理由见脚本内的 `WORKS`。缺少源文件时，脚本会列出缺项。

脚本从源媒体抽帧并切出 H.264 短片，使用 Pillow 将真实帧和仓库已登记的 Noto Sans SC 字体排成 1280 × 640 社交预览。重新执行会覆盖同名资源并打印体积。成片和局部预览原件留在示例的 `outputs/`。网站随仓库保存海报及四段 8–9 秒的无声片段。市值页展示海报，现有预览约 1.93 秒。

## GitHub Pages

[部署工作流](../../.github/workflows/pages.yml)直接上传 `docs/site`。在 GitHub 仓库的 Settings → Pages 中将发布来源选为 GitHub Actions。社交预览图可在仓库 Settings 的 Social preview 区域上传 [social-preview.png](assets/social-preview.png)。
