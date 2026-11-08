"""五类统一 v9 代码场景的配置与打包：入口校验、录制配置、静态模块构建。

录制的另一半（逐帧采集、片段缓存与编码验收）在 `capture.py`；两半共享这里的
`scene_config`/`build_scene`，`capture` 只单向依赖本模块，因此包内没有循环导入。
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from film_runtime.core.assets import REPOSITORY_ROOT
from film_runtime.core.errors import VideoError
from film_runtime.core.video_config import DEFAULT_FPS, validate_fps


WEB = REPOSITORY_ROOT


MEDIA_URL_PREFIX = "/media"


_LITERALS = re.compile(r"'([^'\\\n]*)'|\"([^\"\\\n]*)\"|`([^`\\]*)`")


def digest(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def validate_entry(root: Path, entry: object, props: object) -> None:
    if not isinstance(entry, str) or "\\" in entry:
        raise VideoError("code.entry 必须为 scenes/ 下的相对 TSX 路径")
    file = (root / entry).resolve()
    if (not entry.startswith("scenes/") or not file.is_relative_to((root / "scenes").resolve())
            or not file.is_relative_to(root.resolve()) or file.suffix != ".tsx" or not file.is_file()):
        raise VideoError("code.entry 必须引用作品 scenes/ 下存在的 TSX 文件")
    if not isinstance(props, dict):
        raise VideoError("code.props 必须为 JSON 对象")
    try:
        json.dumps(props, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise VideoError("code.props 必须为有限 JSON 值") from exc


def implementation_inputs() -> dict[str, str]:
    # 代码场景目录里可能再有子目录（例如电影套件拆成 `cinematic/`），因此递归收集：
    # 漏掉一层会让「改了套件源码」不再改变片段缓存键与准备指纹。共享动效原语是纯 TS，
    # 同样必须进入实现指纹，否则改原语不会让引用作品重新准备。
    files = [Path(__file__),
             *(path for name in ("capture.py", "pure_capture.py", "worker.py")
               if (path := Path(__file__).with_name(name)).is_file()),
             WEB / "scripts/build-code-scene.mjs", WEB / "asset-loaders.json",
             WEB / "pyproject.toml", WEB / "uv.lock", WEB / "package.json", WEB / "pnpm-lock.yaml",
             WEB / "pnpm-workspace.yaml", *sorted((WEB / "patches").rglob("*.patch")),
             WEB / "src/fonts.ts", WEB / "src/frames.json", WEB / "src/video-config.json", WEB / "src/frames.ts",
             REPOSITORY_ROOT / "fonts/registry.json",
             WEB / "src/code-scene/entries.json",
             *sorted((WEB / "src/assets/math").glob("*.woff2")),
             *sorted((WEB / "src/code-scene").rglob("*.tsx")), *sorted((WEB / "src/code-scene").rglob("*.ts")),
             *sorted((WEB / "src/code-scene").rglob("*.js")),
             *sorted((WEB / "public/fonts").glob("*"))]
    return {file.relative_to(REPOSITORY_ROOT).as_posix(): digest(file) for file in files
            if file.is_file() and not file.name.endswith(('.test.ts', '.test.tsx'))}


CAPTURE_FIELDS = {"mode", "timebase", "jobs", "blockFrames", "verifyFrames"}


def capture_settings(props: object) -> dict:
    """校验并返回 `content.props.capture` 的录制声明。

    `capture` 是作品 props 里的保留键，只控制录制，不参与画面数据。默认 local /
    sequential；未声明时调用方不得向配置增加任何键，以免改变既有缓存键。
    """
    if props is None:
        props = {}
    if not isinstance(props, dict):
        raise VideoError("content.props 必须为 JSON 对象")
    capture = props.get("capture", {})
    if not isinstance(capture, dict):
        raise VideoError("content.props.capture 必须为 JSON 对象")
    unknown = sorted(set(capture) - CAPTURE_FIELDS)
    if unknown:
        raise VideoError(f"content.props.capture 含未知字段：{'、'.join(unknown)}")
    mode = capture.get("mode", "sequential")
    if mode not in ("sequential", "pure-time"):
        raise VideoError("content.props.capture.mode 必须为 sequential 或 pure-time")
    timebase = capture.get("timebase", "global" if mode == "pure-time" else "local")
    if timebase not in ("local", "global"):
        raise VideoError("content.props.capture.timebase 必须为 local 或 global")
    if mode == "pure-time" and timebase != "global":
        raise VideoError("pure-time 场景必须使用全局时间；请移除 timebase: local")
    jobs = capture.get("jobs", 1)
    if type(jobs) is not int or not 1 <= jobs <= 4:
        raise VideoError("content.props.capture.jobs 必须为 1～4 的整数")
    block_frames = capture.get("blockFrames")
    if block_frames is not None and (type(block_frames) is not int or not 1 <= block_frames <= 36000):
        raise VideoError("content.props.capture.blockFrames 必须为 1～36000 的整数")
    verify_frames = capture.get("verifyFrames", 4)
    if type(verify_frames) is not int or not 2 <= verify_frames <= 4:
        raise VideoError("content.props.capture.verifyFrames 必须为 2～4 的整数")
    return {"mode": mode, "timebase": timebase, "jobs": jobs,
            "blockFrames": block_frames, "verifyFrames": verify_frames}


def _visible_props(props: dict) -> dict:
    """从片段缓存键中剥离运行时采集参数，只保留会改变画面的 capture 声明。"""
    capture = props.get("capture")
    if not isinstance(capture, dict):
        return props
    visible = {key: value for key, value in capture.items() if key in ("mode", "timebase")}
    if not visible:
        return {key: value for key, value in props.items() if key != "capture"}
    return {**props, "capture": visible}


def validate_capture(props: object) -> None:
    """材料校验入口：非法录制声明在 validate/prepare 阶段就失败。"""
    capture_settings(props)


def scene_config(scene: dict, frame: dict, media: dict, *, fps: int = DEFAULT_FPS) -> dict:
    """录制配置与片段缓存输入；统一契约不复用旧档位缓存。"""
    props = scene["content"].get("props", {})
    settings = capture_settings(props)
    config = {"productionContract": "standalone-v3", "props": _visible_props(props), "fps": validate_fps(fps),
              "durationInFrames": scene["durationInFrames"],
              "width": frame["width"], "height": frame["height"],
              "subtitleSafeArea": frame["subtitle"]["safeArea"],
              "segmentWindows": {key: {name: value - scene["startFrame"] for name, value in window.items()}
                                 for key, window in scene["segmentWindows"].items()},
              "media": media, "sources": scene["content"].get("preparedSources", {})}
    if settings["timebase"] == "global":
        start = scene.get("startFrame", 0)
        duration = scene["durationInFrames"]
        config["timeline"] = {"sceneStartFrame": start,
                              "sceneEndFrame": scene.get("endFrame", start + duration),
                              "durationInFrames": duration}
    if settings["mode"] == "pure-time":
        config["captureMode"] = "pure-time"
    if scene.get("eventFrames"):
        config["eventFrames"] = scene["eventFrames"]
    claims = [segment.get("claims") or [] for segment in scene.get("narrationSegments", [])]
    if any(claims):
        config["claims"] = claims
    # 运动模糊与 SSAA 只在作品显式声明时进入配置：standard 作品的缓存键逐字节不变。
    motion = ((scene["content"].get("props") or {}).get("look") or {}).get("motion")
    if motion:
        config["motion"] = motion
    return config


def build_scene(root: Path, scene: dict, work: Path) -> dict[str, str]:
    """为正式录制和 lookdev 共用同一源码闸门、打包器与输入摘要。"""
    content = scene["content"]
    validate_entry(root, content.get("entry"), content.get("props", {}))
    try:
        result = subprocess.run([shutil.which("node") or "node", str(WEB / "scripts/build-code-scene.mjs"),
            str(root), content["entry"], str(work)], cwd=WEB, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VideoError(f"代码场景 {scene['id']} 构建失败：{exc}") from exc
    if result.returncode:
        raise VideoError(f"代码场景 {scene['id']} 构建失败：{result.stderr[-4000:]}")
    built_inputs = json.loads((work / 'input-digests.json').read_text(encoding='utf-8'))
    source_inputs = {}
    for name in json.loads((work / "inputs.json").read_text(encoding="utf-8")):
        file = Path(name)
        if digest(file) != built_inputs.get(str(file)):
            raise VideoError(f'构建期间场景输入已变化：{file}；请重试')
        if file.is_relative_to(root):
            source_inputs["file:" + file.relative_to(root).as_posix()] = digest(file)
    return source_inputs


def copy_build_outputs(source: Path, destination: Path) -> None:
    """缺口、并行块和网页预览复用同一产物清单，避免漏掉CSS或模型资源。"""
    names = json.loads((source / 'outputs.json').read_text(encoding='utf-8'))
    for name in names:
        path = (source / name).resolve()
        target = (destination / name).resolve()
        if (not path.is_relative_to(source.resolve()) or not path.is_file()
                or not target.is_relative_to(destination.resolve())):
            raise VideoError('场景构建产物缺失或越界')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def source_texts(root: Path) -> dict[str, str]:
    """作品场景源码里出现的字串，按文件归集。

    v9 的可见文字基本都在作品代码里，而**缺字是唯一一种静默失败**：浏览器直接回退到
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
            raise VideoError(f"媒体解析地址非法：{src!r}")
        files[src] = root / "assets/media" / src[len(MEDIA_URL_PREFIX) + 1:]
    return files
