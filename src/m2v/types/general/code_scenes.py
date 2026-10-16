"""可信 React 场景构建与实时录制。录制产物是准备输入，导出不运行作品代码。"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
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
WIDTH, HEIGHT, FPS = 864, 920, 30
READY_TIMEOUT_MS = 30000


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
             WEB / "src/fonts.ts", WEB / "src/palette.ts", *sorted((WEB / "src/code-scene").glob("*.tsx")),
             *sorted((WEB / "public/fonts").glob("*"))]
    return {str(file.relative_to(REPOSITORY_ROOT)): digest(file) for file in files if file.is_file()}


def asset_inputs(root: Path) -> dict[str, str]:
    result = {}
    for file in sorted((root / "assets").rglob("*")):
        if file.is_file():
            if not file.resolve().is_relative_to(root):
                raise M2VError("代码场景资源符号链接越界")
            result["file:" + file.relative_to(root).as_posix()] = digest(file)
    return result


def record(root: Path, scene: dict, inputs: dict[str, str], theme: str = "dark") -> str:
    """构建可达源码，缓存有效时不启动浏览器；动态本地素材也绑定摘要。"""
    from playwright.sync_api import sync_playwright
    content = scene["content"]
    validate_entry(root, content.get("entry"), content.get("props", {}))
    cache = root / "outputs/code-cache"
    cache.mkdir(parents=True, exist_ok=True)
    config = {"props": content.get("props", {}), "fps": FPS, "durationInFrames": scene["durationInFrames"],
              "theme": theme,
              "segmentWindows": {key: {name: value - scene["startFrame"] for name, value in window.items()}
                                 for key, window in scene["segmentWindows"].items()}}
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
        # 动态 URL 不在打包图中。绑定整个资源目录，新增/删除资源也改变缓存键。
        assets = asset_inputs(root)
        source_inputs.update(assets)
        inputs.update(source_inputs)
        inputs["codeAssets"] = fingerprint(assets)
        with sync_playwright() as pw:
            browser_version = pw.chromium.executable_path
            executable = Path(browser_version)
            key = fingerprint({"config": config, "sources": source_inputs, "implementation": implementation_inputs(),
                               "browser": digest(executable), "size": [WIDTH, HEIGHT], "capture": "cdp-png-444-v1"})
            output = cache / f"{key}.mp4"
            receipt = cache / f"{key}.json"
            if output.is_file() and receipt.is_file() and receipt.read_text() == digest(output):
                logger.info("代码场景 %s 复用录制缓存", scene["id"])
            else:
                logger.info("代码场景 %s 开始实时录制：%.2f 秒", scene["id"], config["durationInFrames"] / FPS)
                _capture(pw, root, work, config)
                _encode(work, output, config["durationInFrames"])
                receipt.write_text(digest(output))
        relative = output.relative_to(root).as_posix()
        inputs["file:" + relative] = digest(output)
        return relative


def _capture(pw, root: Path, work: Path, config: dict) -> None:
    """CDP 帧含真实时间戳；逐帧落盘，避免把长视频帧留在内存。"""
    errors: list[str] = []
    config_text = json.dumps(config, ensure_ascii=True).replace("<", "\\u003c")
    (work / "index.html").write_text('<!doctype html><html><head><meta charset="utf-8"></head>'
        '<body style="margin:0;overflow:hidden">'
        '<div id="root" style="width:864px;height:920px;overflow:hidden"></div>'
        f'<script>window.__M2V_CODE_CONFIG__={config_text}</script><script src="scene.js"></script></body></html>', encoding="utf-8")
    # 只开放 assets 与字体，不暴露作品配置、源文或任意文件；没有本地素材的作品不挂载 assets。
    mounts = {"/fonts": WEB / "public/fonts"}
    if (root / "assets").is_dir():
        mounts["/assets"] = root / "assets"
    with LocalServer(work, mounts=mounts) as server:
        browser = pw.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        try:
            context = browser.new_context(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1,
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
                    raise M2VError("代码场景就绪失败：" + "; ".join(errors or ["30 秒内未调用 ready() / 字体未就绪"]))
                page.wait_for_timeout(50)
            session = context.new_cdp_session(page)
            frames: list[tuple[str, float]] = []
            def on_frame(event):
                name = f"frame-{len(frames):06d}.png"
                (work / name).write_bytes(base64.b64decode(event["data"]))
                frames.append((name, event["metadata"]["timestamp"]))
                session.send("Page.screencastFrameAck", {"sessionId": event["sessionId"]})
            session.on("Page.screencastFrame", on_frame)
            # PNG 而不是 JPEG：录制片段会与外壳背景拼接，JPEG 的色度子采样会让片段底色
            # 比外壳偏两三级，在深色画面上显出可见的方块边缘。
            session.send("Page.startScreencast", {"format": "png", "maxWidth": WIDTH, "maxHeight": HEIGHT, "everyNthFrame": 1})
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


def _encode(work: Path, output: Path, frames: int) -> None:
    temporary = work / "encoded.mp4"
    # yuv444p 而不是 yuv420p：片段会与外壳背景直接拼接，4:2:0 的色度抽样会让底色偏一两个色阶，
    # 在深色画面上显出方块边缘；4:4:4 的往返对纯色是精确的。
    audio.ffmpeg(["-f", "concat", "-safe", "0", "-i", str(work / "frames.txt"), "-an", "-vf",
                  f"fps={FPS},scale={WIDTH}:{HEIGHT},tpad=stop_mode=clone:stop_duration=1",
                  "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv444p", "-crf", "18", str(temporary)])
    security.deliver(temporary, output)
