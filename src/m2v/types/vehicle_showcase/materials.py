"""SU7 汽车展示材料：离线资产清单、glTF 内嵌与渲染输入。"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from m2v.core.schema import validate_document
from m2v.core.validate import fail
from .schema import Manifest, Showcase

WIDTH = 1920
HEIGHT = 1080
FPS = 30
SHOWCASE_VERSION = 2
MANIFEST_VERSION = 1
MATERIALS = {"showcase": "showcase.json", "assets": "manifest.json"}
STUDIO_FIELDS = ("environment", "bodyAo", "floorNormal", "floorRoughness")
_MIME = {".bin": "application/octet-stream", ".webp": "image/webp", ".png": "image/png",
         ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".hdr": "image/vnd.radiance"}


def _load(path: Path, version: int) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        fail(path.name, f"无法读取有效 UTF-8 JSON：{exc}")
    if not isinstance(data, dict):
        fail(path.name, "必须是 JSON 对象")
    if data.get("schemaVersion") != version:
        if path.name == "showcase.json" and data.get("schemaVersion") == 1:
            fail(path.name, "schemaVersion 1 已停用：请升级到 2 并补齐 studio 影棚资产")
        fail(path.name, f"schemaVersion 必须为 {version}")
    return data


def _number(value: Any, where: str, *, low: float | None = None) -> float:
    if type(value) not in (int, float):
        fail(where, "必须是数字")
    try:
        number = float(value)
    except (OverflowError, ValueError):
        fail(where, "超出可表示范围")
    if not math.isfinite(number) or (low is not None and number < low):
        fail(where, "必须是有限数字" + (f"，且不小于 {low:g}" if low is not None else ""))
    return number


def _validate_showcase(show: dict[str, Any]) -> None:
    canvas = show["canvas"]
    if (canvas.get("width"), canvas.get("height")) != (WIDTH, HEIGHT):
        fail("showcase.json.canvas", f"固定为 {WIDTH}×{HEIGHT}")
    duration = show.get("durationSeconds")
    if not 10 <= duration <= 120:
        fail("showcase.json.durationSeconds", "必须是 10～120 的整数秒")
    if show.get("fps") != FPS:
        fail("showcase.json.fps", f"必须为 {FPS}")
    model = show["model"]
    normalized = Path(model)
    if normalized.is_absolute() or ".." in normalized.parts:
        fail("showcase.json.model", "必须是作品内相对路径")
    camera = show["camera"]
    for field in ("distance", "height", "orbitStartDegrees", "orbitEndDegrees"):
        _number(camera.get(field), f"showcase.json.camera.{field}")
    effects = show["effects"]
    for field in ("speedStartSeconds", "speedEndSeconds", "fadeOutSeconds"):
        _number(effects.get(field), f"showcase.json.effects.{field}", low=0)
    if not effects["speedStartSeconds"] < effects["speedEndSeconds"] < duration:
        fail("showcase.json.effects", "必须满足 启动秒数 < 疾驰结束秒数 < 总时长")
    if effects["fadeOutSeconds"] > duration:
        fail("showcase.json.effects.fadeOutSeconds", "不能超过总时长")
    studio = show["studio"]
    for field in STUDIO_FIELDS:
        relative = studio[field]
        normalized = Path(relative)
        if normalized.is_absolute() or ".." in normalized.parts:
            fail(f"showcase.json.studio.{field}", "必须是作品内相对路径")


def _validate_manifest(manifest: dict[str, Any]) -> None:
    assets = manifest["assets"]
    seen: set[str] = set()
    for index, item in enumerate(assets):
        where = f"manifest.json.assets[{index}]"
        path = item["path"]
        if Path(path).is_absolute() or ".." in Path(path).parts:
            fail(f"{where}.path", "必须是作品内相对路径")
        if path in seen:
            fail(f"{where}.path", "资产路径重复")
        seen.add(path)
        digest = item["sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(f"{where}.sha256", "必须是 64 位十六进制 SHA-256")


def _data_uri(file: Path) -> str:
    mime = _MIME.get(file.suffix.lower(), "application/octet-stream")
    return f"data:{mime};base64," + base64.b64encode(file.read_bytes()).decode("ascii")


def _embed_model(root: Path, model_path: str, manifest: dict[str, Any],
                 wheel_nodes: list[str]) -> str:
    path = (root / model_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        fail("showcase.json.model", f"模型不存在：{model_path}")
    registered = {item["path"]: item for item in manifest["assets"]}
    try:
        gltf = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        fail("showcase.json.model", f"模型不是有效 glTF JSON：{exc}")
    for buffer in gltf.get("buffers", []):
        uri = buffer.get("uri") if isinstance(buffer, dict) else None
        if isinstance(uri, str) and not uri.startswith("data:"):
            file = (path.parent / uri).resolve()
            rel = file.relative_to(root).as_posix()
            if rel not in registered:
                fail("manifest.json.assets", f"glTF 依赖未登记：{rel}")
            buffer["uri"] = _data_uri(file)
    for image in gltf.get("images", []):
        uri = image.get("uri") if isinstance(image, dict) else None
        if isinstance(uri, str) and not uri.startswith("data:"):
            file = (path.parent / uri).resolve()
            rel = file.relative_to(root).as_posix()
            if rel not in registered:
                fail("manifest.json.assets", f"glTF 依赖未登记：{rel}")
            image["uri"] = _data_uri(file)
    nodes = {node.get("name") for node in gltf.get("nodes", []) if isinstance(node, dict)}
    for name in wheel_nodes:
        if name not in nodes:
            fail("showcase.json.wheelNodes", f"glTF 中不存在节点：{name}")
    return json.dumps(gltf, ensure_ascii=False, separators=(",", ":"))


def _embed_studio(root: Path, studio: dict[str, Any], manifest: dict[str, Any]) -> dict[str, str]:
    """把影棚贴图内嵌为 data URI；未登记视为材料错误，不回退到内置环境。"""
    registered = {item["path"]: item for item in manifest["assets"]}
    embedded: dict[str, str] = {}
    for field in STUDIO_FIELDS:
        relative = studio[field]
        if relative not in registered:
            fail(f"showcase.json.studio.{field}", f"贴图未在 manifest.json 登记：{relative}")
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            fail(f"showcase.json.studio.{field}", f"贴图不存在：{relative}")
        embedded[field] = _data_uri(path)
    return embedded


def load_project(project_dir: str | Path) -> dict[str, Any]:
    root = Path(project_dir).resolve()
    if not root.is_dir():
        fail("作品目录", f"目录不存在：{root}")
    show = validate_document(
        Showcase, _load(root / MATERIALS["showcase"], SHOWCASE_VERSION), "showcase.json")
    manifest = validate_document(
        Manifest, _load(root / MATERIALS["assets"], MANIFEST_VERSION), "manifest.json")
    _validate_showcase(show)
    _validate_manifest(manifest)
    for asset in manifest["assets"]:
        file = (root / asset["path"]).resolve()
        if not file.is_relative_to(root) or not file.is_file():
            fail("manifest.json.assets", f"资产不存在：{asset['path']}")
        if hashlib.sha256(file.read_bytes()).hexdigest() != asset["sha256"]:
            fail("manifest.json.assets", f"资产摘要不匹配：{asset['path']}")
    model_gltf = _embed_model(root, show["model"], manifest, show["wheelNodes"])
    studio = _embed_studio(root, show["studio"], manifest)
    return {"showcase": show, "manifest": manifest, "modelGltf": model_gltf, "studio": studio}


def build_render_props(docs: dict[str, Any]) -> dict[str, Any]:
    show = docs["showcase"]
    return {
        "schemaVersion": 2,
        "durationInFrames": show["durationSeconds"] * FPS,
        "fps": FPS,
        "width": WIDTH,
        "height": HEIGHT,
        "showcase": show,
        "modelGltf": docs["modelGltf"],
        "studio": docs["studio"],
    }


def render_inputs_digest(project_dir: str | Path) -> str:
    root = Path(project_dir).resolve()
    from m2v.core.assets import REPOSITORY_ROOT
    import m2v.engine.remotion as remotion
    from m2v.engine import render_pipeline

    web = REPOSITORY_ROOT / "web"
    web_inputs = remotion.build_inputs()
    inputs: list[tuple[Path, Path]] = [(root, root / name) for name in MATERIALS.values()]
    inputs.extend((web, path) for path in web_inputs if path.is_relative_to(web))
    inputs.extend((REPOSITORY_ROOT, path) for path in web_inputs if not path.is_relative_to(web))
    package = Path(__file__).resolve().parent
    inputs.extend((package, path) for path in sorted(package.glob("*.py")))
    inputs.append((REPOSITORY_ROOT, Path(render_pipeline.__file__)))
    inputs.extend((REPOSITORY_ROOT, path) for path in remotion.implementation_files())
    manifest = _load(root / MATERIALS["assets"], MANIFEST_VERSION)
    for asset in manifest["assets"]:
        inputs.append((root, root / asset["path"]))
    digest = hashlib.sha256()
    for base, path in inputs:
        try:
            content = path.read_bytes()
        except OSError as exc:
            fail("渲染输入摘要", f"无法读取绑定文件 {path.name}：{exc}")
        digest.update(path.relative_to(base).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(content).digest())
    return digest.hexdigest()
