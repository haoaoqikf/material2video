"""通用 v8 代码场景的配置与打包：入口校验、录制配置、静态模块构建。

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
from m2v.core.assets import REPOSITORY_ROOT
from m2v.core.errors import M2VError
from m2v.core.video_config import FPS


WEB = REPOSITORY_ROOT / "web"


MEDIA_URL_PREFIX = "/media"


CINEMATIC_DEPS = ("postprocessing", "@react-three/postprocessing")


_LITERALS = re.compile(r"'([^'\\\n]*)'|\"([^\"\\\n]*)\"|`([^`\\]*)`")


def require_cinematic_dependencies() -> None:
    missing = [name for name in CINEMATIC_DEPS if not (WEB / "node_modules" / name).exists()]
    if missing:
        raise M2VError(f"缺少电影级后期依赖：{'、'.join(missing)}；请先运行 pnpm -C web install")


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
    # 代码场景目录里可能再有子目录（例如电影套件拆成 `cinematic/`），因此递归收集：
    # 漏掉一层会让「改了套件源码」不再改变片段缓存键与准备指纹。
    files = [Path(__file__), WEB / "scripts/build-code-scene.mjs", WEB / "package.json", WEB / "pnpm-lock.yaml",
             WEB / "src/fonts.ts", WEB / "src/frames.json", WEB / "src/video-config.json", WEB / "src/frames.ts",
             *sorted((WEB / "src/code-scene").rglob("*.tsx")), *sorted((WEB / "src/code-scene").rglob("*.js")),
             *sorted((WEB / "public/fonts").glob("*"))]
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
    # 运动模糊与 SSAA 只在作品显式声明时进入配置：standard 作品的缓存键逐字节不变。
    motion = ((scene["content"].get("props") or {}).get("look") or {}).get("motion")
    if motion:
        config["motion"] = motion
    return config


def build_scene(root: Path, scene: dict, work: Path) -> dict[str, str]:
    """为正式录制和 lookdev 共用同一源码闸门、打包器与输入摘要。"""
    require_cinematic_dependencies()
    content = scene["content"]
    validate_entry(root, content.get("entry"), content.get("props", {}))
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
    return source_inputs


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
