"""可信 React 场景构建与实时录制。录制产物是准备输入，导出不运行作品代码。

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
from m2v.core import security
from m2v.engine import audio
from m2v.engine.http_server import LocalServer

logger = logging.getLogger(__name__)
WEB = REPOSITORY_ROOT / "web"
FPS = 30
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
             WEB / "src/fonts.ts", WEB / "src/frames.json", WEB / "src/frames.ts",
             *sorted((WEB / "src/code-scene").glob("*.tsx")), *sorted((WEB / "public/fonts").glob("*"))]
    return {str(file.relative_to(REPOSITORY_ROOT)): digest(file) for file in files if file.is_file()}


def record(root: Path, scene: dict, inputs: dict[str, str], *, frame: dict, media: dict, media_digest: str) -> str:
    """构建可达源码，缓存有效时不启动浏览器；画幅与媒体映射都进缓存键。"""
    from playwright.sync_api import sync_playwright
    content = scene["content"]
    validate_entry(root, content.get("entry"), content.get("props", {}))
    width, height = frame["width"], frame["height"]
    cache = root / "outputs/code-cache"
    cache.mkdir(parents=True, exist_ok=True)
    config = {"props": content.get("props", {}), "fps": FPS, "durationInFrames": scene["durationInFrames"],
              "width": width, "height": height, "subtitleSafeArea": frame["subtitle"]["safeArea"],
              "segmentWindows": {key: {name: value - scene["startFrame"] for name, value in window.items()}
                                 for key, window in scene["segmentWindows"].items()},
              "media": media}
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
                               "browser": digest(executable), "size": [width, height], "capture": "cdp-png-444-v2"})
            output = cache / f"{key}.mp4"
            receipt = cache / f"{key}.json"
            if output.is_file() and receipt.is_file() and receipt.read_text() == digest(output):
                logger.info("代码场景 %s 复用录制缓存", scene["id"])
            else:
                logger.info("代码场景 %s 开始实时录制：%.2f 秒，%d×%d",
                            scene["id"], config["durationInFrames"] / FPS, width, height)
                _capture(pw, root, work, config)
                _encode(work, output, config["durationInFrames"], width, height)
                receipt.write_text(digest(output))
        relative = output.relative_to(root).as_posix()
        inputs["file:" + relative] = digest(output)
        return relative


def _capture(pw, root: Path, work: Path, config: dict) -> None:
    """CDP 帧含真实时间戳；逐帧落盘，避免把长视频帧留在内存。"""
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
    with LocalServer(work, mounts=mounts, files=files) as server:
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
                page.wait_for_timeout(50)
            session = context.new_cdp_session(page)
            frames: list[tuple[str, float]] = []
            def on_frame(event):
                name = f"frame-{len(frames):06d}.png"
                (work / name).write_bytes(base64.b64decode(event["data"]))
                frames.append((name, event["metadata"]["timestamp"]))
                session.send("Page.screencastFrameAck", {"sessionId": event["sessionId"]})
            session.on("Page.screencastFrame", on_frame)
            # PNG 而不是 JPEG：作品画面本就要与片段直接对齐，JPEG 的色度子采样会在
            # 纯色区域显出可见的方块边缘。
            session.send("Page.startScreencast", {"format": "png", "maxWidth": width, "maxHeight": height, "everyNthFrame": 1})
            # 初始画面在 start 前采集，所有后续时序以浏览器实际开始时间为零。
            page.wait_for_timeout(50)
            start = page.evaluate("() => {window.__M2V_CODE__.start(); return Date.now()/1000;}")
            deadline = time.monotonic() + config["durationInFrames"] / FPS
            while time.monotonic() < deadline:
                if errors:
                    raise M2VError("代码场景运行失败：" + "; ".join(errors[:5]))
                page.wait_for_timeout(min(100, max(1, (deadline-time.monotonic())*1000)))
            session.send("Page.stopScreencast")
            if errors or not frames:
                raise M2VError("代码场景录制失败：" + "; ".join(errors or ["没有捕获画面"]))
            duration = config["durationInFrames"] / FPS
            # 丢弃就绪前导，保留起点之前最近的已绘制帧作为 t=0 画面。
            chosen = [(name, max(0., stamp-start)) for name, stamp in frames if stamp <= start+duration]
            initial = max((i for i, (_, stamp) in enumerate(chosen) if stamp == 0), default=0)
            chosen = chosen[initial:]
            lines = []
            for index, (name, stamp) in enumerate(chosen):
                end = chosen[index+1][1] if index+1 < len(chosen) else duration
                lines.extend([f"file '{name}'", f"duration {max(.001, end-stamp):.9f}"])
            lines.append(f"file '{chosen[-1][0]}'")
            (work / "frames.txt").write_text("\n".join(lines), encoding="utf-8")
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
    audio.ffmpeg(["-f", "concat", "-safe", "0", "-i", str(work / "frames.txt"), "-an", "-vf",
                  f"fps={FPS},scale={width}:{height},tpad=stop_mode=clone:stop_duration=1",
                  "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv444p", "-crf", "18", str(temporary)])
    security.deliver(temporary, output)
