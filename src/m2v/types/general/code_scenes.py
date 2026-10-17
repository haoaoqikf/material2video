"""可信 React 场景构建与逐帧录制。录制产物是准备输入，导出不运行作品代码。

v8 的作品代码控制整张画布：录制 viewport、页面根元素、ffmpeg 标准化与 composition
都用作品声明的画幅。共享层只提供片段回放与字幕，不再画标题或内容框。
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from m2v.core.assets import REPOSITORY_ROOT
from m2v.core.errors import M2VError
from m2v.core.fingerprints import fingerprint
from m2v.core.video_config import FPS
from m2v.core import security
from m2v.engine import audio
from m2v.engine.http_server import LocalServer

logger = logging.getLogger(__name__)
WEB = REPOSITORY_ROOT / "web"
READY_TIMEOUT_MS = 30000
#: 媒体解析地址的前缀：录制页只从这里取已登记素材，不暴露作品目录。
MEDIA_URL_PREFIX = "/media"


def digest(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def validate_entry(root: Path, entry: object, props: object) -> None:
    if not isinstance(entry, str) or "\\" in entry:
        raise M2VError("code.entry 必须为 scenes/ 下的相对 TSX 路径")
    file = (root / entry).resolve()
    if (not entry.startswith("scenes/") or not file.is_relative_to((root / "scenes").resolve())
            or not file.is_relative_to(root.resolve()) or file.suffix != ".tsx" or not file.is_file()):
        raise M2VError("code.entry 必须引用作品 scenes/ 下存在的 TSX 文件")
    if not isinstance(props, dict):
        raise M2VError("code.props 必须为 JSON 对象")
    try:
        json.dumps(props, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise M2VError("code.props 必须为有限 JSON 值") from exc


def implementation_inputs() -> dict[str, str]:
    files = [Path(__file__), WEB / "scripts/build-code-scene.mjs", WEB / "package.json", WEB / "pnpm-lock.yaml",
             WEB / "src/fonts.ts", WEB / "src/frames.json", WEB / "src/video-config.json", WEB / "src/frames.ts",
             *sorted((WEB / "src/code-scene").glob("*.tsx")), *sorted((WEB / "src/code-scene").glob("*.js")), *sorted((WEB / "public/fonts").glob("*"))]
    return {str(file.relative_to(REPOSITORY_ROOT)): digest(file) for file in files if file.is_file()}


def scene_config(scene: dict, frame: dict, media: dict, *, profile: str = "standard") -> dict:
    """录制配置，同时是片段缓存键的一部分。

    `profile` 与旁白 `claims` 只在**非默认**时写进配置：standard 作品不写这些字段时，
    缓存键与既有片段逐字节一致，不会因为新增档位概念而失效。
    """
    config = {"props": scene["content"].get("props", {}), "fps": FPS,
              "durationInFrames": scene["durationInFrames"],
              "width": frame["width"], "height": frame["height"],
              "subtitleSafeArea": frame["subtitle"]["safeArea"],
              "segmentWindows": {key: {name: value - scene["startFrame"] for name, value in window.items()}
                                 for key, window in scene["segmentWindows"].items()},
              "media": media}
    if profile != "standard":
        config["profile"] = profile
    claims = [segment.get("claims") or [] for segment in scene.get("narrationSegments", [])]
    if any(claims):
        config["claims"] = claims
    return config


def record(root: Path, scene: dict, inputs: dict[str, str], *, frame: dict, media: dict, media_digest: str,
           profile: str = "standard") -> str:
    """构建可达源码，缓存有效时不启动浏览器；画幅、媒体映射与档位都进缓存键。"""
    from playwright.sync_api import sync_playwright
    content = scene["content"]
    validate_entry(root, content.get("entry"), content.get("props", {}))
    width, height = frame["width"], frame["height"]
    cache = root / "outputs/code-cache"
    cache.mkdir(parents=True, exist_ok=True)
    config = scene_config(scene, frame, media, profile=profile)
    with tempfile.TemporaryDirectory(prefix="code-", dir=cache) as temporary:
        work = Path(temporary)
        try:
            result = subprocess.run([shutil.which("node") or "node", str(WEB / "scripts/build-code-scene.mjs"),
                str(root), content["entry"], str(work)], cwd=WEB, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=120)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise M2VError(f"代码场景 {scene['id']} 构建失败：{exc}") from exc
        if result.returncode:
            raise M2VError(f"代码场景 {scene['id']} 构建失败：{result.stderr[-4000:]}")
        source_inputs = {}
        for name in json.loads((work / "inputs.json").read_text(encoding="utf-8")):
            file = Path(name)
            if file.is_relative_to(root):
                source_inputs["file:" + file.relative_to(root).as_posix()] = digest(file)
        inputs.update(source_inputs)
        inputs["codeMedia"] = media_digest
        with sync_playwright() as pw:
            browser_version = pw.chromium.executable_path
            executable = Path(browser_version)
            key = fingerprint({"config": config, "media": media_digest, "sources": source_inputs,
                               "implementation": implementation_inputs(),
                               "browser": digest(executable), "size": [width, height], "capture": "fixed-clock-png-444-v3"})
            output = cache / f"{key}.mp4"
            receipt = cache / f"{key}.json"
            if output.is_file() and receipt.is_file() and receipt.read_text() == digest(output):
                logger.info("代码场景 %s 复用录制缓存", scene["id"])
            else:
                logger.info("代码场景 %s 开始逐帧录制：%.2f 秒，%d×%d",
                            scene["id"], config["durationInFrames"] / FPS, width, height)
                _capture(pw, root, work, config)
                _encode(work, output, config["durationInFrames"], width, height)
                receipt.write_text(digest(output))
        relative = output.relative_to(root).as_posix()
        inputs["file:" + relative] = digest(output)
        return relative


def _capture(pw, root: Path, work: Path, config: dict) -> None:
    """固定时间推进、绘制后截图；逐帧落盘且宿主超时不使用作品时钟。"""
    errors: list[str] = []
    width, height = config["width"], config["height"]
    config_text = json.dumps(config, ensure_ascii=True).replace("<", "\\u003c")
    (work / "index.html").write_text('<!doctype html><html><head><meta charset="utf-8"></head>'
        # 页面底色是编码兜底而不是作品主题：作品必须在 ready 之前自己画满不透明背景。
        '<body style="margin:0;overflow:hidden;background:#000">'
        f'<div id="root" style="width:{width}px;height:{height}px;overflow:hidden"></div>'
        f'<script>window.__M2V_CODE_CONFIG__={config_text}</script><script src="scene.js"></script></body></html>',
        encoding="utf-8")
    # 只开放已登记媒体与批准字体，不暴露作品配置、源文、导入记录或 assets 下的其他文件。
    mounts = {"/fonts": WEB / "public/fonts"}
    files = media_files(root, config["media"])
    with LocalServer(work, mounts=mounts, files=files, cors=True) as server:
        browser = pw.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        try:
            context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1,
                                          service_workers="block")
            def route_request(route):
                url = route.request.url
                if url.startswith(server.base_url + "/") or url.startswith(("data:", "blob:")):
                    route.continue_()
                else:
                    errors.append("代码场景禁止外网请求：" + url)
                    route.abort()
            context.add_init_script(path=str(WEB / "src/code-scene/capture-clock.js"))
            context.route("**/*", route_request)
            context.route_web_socket("**/*", lambda route: (errors.append("代码场景禁止 WebSocket"), route.close()))
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("response", lambda response: errors.append(f"资源加载失败：{response.url}") if response.status >= 400 else None)
            page.goto(server.base_url + "/index.html")
            deadline = time.monotonic() + READY_TIMEOUT_MS / 1000
            while not page.evaluate("Boolean(window.__M2V_CODE__?.ready)"):
                if errors or time.monotonic() >= deadline:
                    raise M2VError("代码场景就绪失败：" + "; ".join(errors or ["30 秒内未调用 ready() / 字体或素材未就绪"]))
                page.evaluate("window.__M2V_CAPTURE_CLOCK__.bootstrap()")
            session = context.new_cdp_session(page)
            started = time.monotonic()
            page.evaluate("window.__M2V_CODE__.start()")
            total = config["durationInFrames"]
            for frame_index in range(total):
                # 截图期间时钟冻结，超时使用注入前保留的原生真实定时器。
                try:
                    page.evaluate("""([frame, timeout]) => window.__M2V_CAPTURE_CLOCK__.deadline(
                        window.__M2V_CODE__.advanceToFrame(frame), timeout)""", [frame_index, READY_TIMEOUT_MS])
                except Exception as exc:
                    raise M2VError(f"代码场景第 {frame_index} 帧绘制失败：{exc}") from exc
                if errors:
                    raise M2VError(f"代码场景第 {frame_index} 帧运行失败：" + "; ".join(errors))
                # CDP 截取已完成绘制的画面；不依赖 screencast 的实时投递频率。
                shot = session.send("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False,
                                                               "optimizeForSpeed": True})
                (work / f"frame-{frame_index:06d}.png").write_bytes(base64.b64decode(shot["data"]))
                if frame_index % 300 == 0 or frame_index + 1 == total:
                    logger.info("代码场景逐帧采集 %d/%d，耗时 %.1f 秒", frame_index + 1, total, time.monotonic() - started)
        except M2VError:
            raise
        except Exception as exc:
            raise M2VError(f"代码场景浏览器录制失败：{exc}") from exc
        finally:
            browser.close()


#: 作品源码里可能被渲染的字串：单双引号与模板字面量。样式值多为 ASCII，误报代价低。
_LITERALS = re.compile(r"'([^'\\\n]*)'|\"([^\"\\\n]*)\"|`([^`\\]*)`")


def source_texts(root: Path) -> dict[str, str]:
    """作品场景源码里出现的字串，按文件归集。

    v8 的可见文字基本都在作品代码里，而**缺字是唯一一种静默失败**：浏览器直接回退到
    系统字体，字宽字重全变却不报错。因此把源码字面量一并交给字体体检，而不是只看分屏
    产出的字幕。定位用相对路径，便于直接打开那一行。
    """
    texts: dict[str, str] = {}
    for file in sorted((root / "scenes").rglob("*.tsx")):
        if not file.is_file() or not file.resolve().is_relative_to(root.resolve()):
            continue
        found = "".join(match.group(1) or match.group(2) or match.group(3) or ""
                        for match in _LITERALS.finditer(file.read_text(encoding="utf-8")))
        if found:
            texts[file.relative_to(root).as_posix()] = found
    return texts


def media_files(root: Path, media: dict) -> dict[str, Path]:
    """把媒体映射翻成「URL 路径 → 本地文件」，服务器只认这份白名单。"""
    files = {}
    for entry in media.values():
        src = entry["src"]
        if not isinstance(src, str) or not src.startswith(MEDIA_URL_PREFIX + "/"):
            raise M2VError(f"媒体解析地址非法：{src!r}")
        files[src] = root / "assets/media" / src[len(MEDIA_URL_PREFIX) + 1:]
    return files


def _encode(work: Path, output: Path, frames: int, width: int, height: int) -> None:
    temporary = work / "encoded.mp4"
    # yuv444p 而不是 yuv420p：片段会与作品画布直接拼接，4:2:0 的色度抽样会让底色偏
    # 一两个色阶，在深色画面上显出方块边缘；4:4:4 的往返对纯色是精确的。
    captured = sorted(work.glob("frame-*.png"))
    if len(captured) != frames or any(path.name != f"frame-{i:06d}.png" for i, path in enumerate(captured)):
        raise M2VError("代码场景采集帧缺失，拒绝补帧编码")
    audio.ffmpeg(["-framerate", str(FPS), "-start_number", "0", "-i", str(work / "frame-%06d.png"),
                  "-an", "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv444p", "-crf", "18", str(temporary)])
    # 解码实际帧数，不能仅相信容器时长或声明帧率。
    from imageio_ffmpeg import get_ffmpeg_exe
    result = subprocess.run([get_ffmpeg_exe(), "-v", "error", "-i", str(temporary), "-map", "0:v:0",
                             "-f", "framehash", "-"], capture_output=True, text=True, timeout=300)
    decoded = sum(bool(line.strip()) and not line.startswith("#") for line in result.stdout.splitlines())
    if result.returncode or decoded != frames:
        raise M2VError(f"代码场景编码帧数不符：期望 {frames}，实际 {decoded}")
    security.deliver(temporary, output)
