"""分镜脚本（storyboard）的数据模型与校验。

分镜脚本是「文章 → 动画网页 → 视频」链路中的内容真源：
- AI 依据它编写动画网页（网页读取同一份 JSON 绘制画面）；
- 渲染脚本依据它推导总帧数并驱动逐帧截图。

本模块只负责解析与结构校验，不做任何 I/O 之外的事情，
保证校验逻辑可以在纯 Python 单元测试中复用。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# 当前支持的脚本版本。字段结构变化时必须递增，并在校验时给出明确提示。
SUPPORTED_VERSION = 1

# 场景 ID 允许的字符：字母、数字、下划线、连字符。用于网页 DOM 与日志定位。
_SCENE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")

# 已知场景类型及其 data 中的必填/可选字段。新增类型时同步更新
# docs/PROJECT_PLAN.md 的组件清单与 SKILL.md 中的说明。
_SCENE_FIELDS: dict[str, dict[str, set[str]]] = {
    "title": {"required": {"text"}, "optional": {"subtitle", "emphasis"}},
    "quote": {"required": {"text"}, "optional": {"attribution", "emphasis"}},
    "comparison": {"required": {"left", "right"}, "optional": {"title"}},
    "timeline": {"required": {"items"}, "optional": {"title"}},
    "diagram": {"required": {"nodes"}, "optional": {"edges", "title"}},
    "number": {"required": {"value"}, "optional": {"label", "caption"}},
    "list": {"required": {"items"}, "optional": {"title"}},
    "conclusion": {"required": {"text"}, "optional": {"action", "emphasis"}},
}


@dataclass(frozen=True)
class Issue:
    """一条校验结果。path 指向 JSON 内的层级位置，便于 AI 定位修正。"""

    level: str  # "error" 或 "warning"
    path: str  # 例如 "scenes[2].durationInFrames"
    message: str

    def format(self) -> str:
        return f"[{self.level}] {self.path}: {self.message}"


@dataclass
class Report:
    """校验报告：errors 不通过则禁止渲染，warnings 默认放行。"""

    issues: list[Issue] = field(default_factory=list)

    def add(self, level: str, path: str, message: str) -> None:
        self.issues.append(Issue(level, path, message))

    def error(self, path: str, message: str) -> None:
        self.add("error", path, message)

    def warn(self, path: str, message: str) -> None:
        self.add("warning", path, message)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_json(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [{"path": i.path, "message": i.message} for i in self.errors],
            "warnings": [{"path": i.path, "message": i.message} for i in self.warnings],
        }


def validate(data: Any) -> Report:
    """校验分镜脚本 dict，返回结构化报告。data 不是 dict 时直接判错。"""
    report = Report()
    if not isinstance(data, dict):
        report.error("$", "脚本根节点必须是 JSON 对象")
        return report

    _validate_version(data, report)
    _validate_framerate(data, report)
    _validate_dimensions(data, report)
    # 后续换算必须用可信的 fps；非法值已在校验中报错，这里只是避免算术崩溃
    _validate_scenes(data, report, _safe_fps(data))
    return report


def _safe_fps(data: dict[str, Any]) -> int:
    """取出可安全参与算术的 fps，非法时回退 30。

    校验器的职责是「报告问题」而不是「自己抛异常」，因此所有用于计算的
    字段都要先做类型收敛。
    """
    fps = data.get("fps")
    if isinstance(fps, int) and not isinstance(fps, bool) and fps > 0:
        return fps
    return 30


def _validate_version(data: dict[str, Any], report: Report) -> None:
    version = data.get("version")
    if not isinstance(version, int) or isinstance(version, bool):
        report.error("version", "version 必须是整数")
    elif version != SUPPORTED_VERSION:
        report.error("version", f"不支持的脚本版本 {version}，当前支持 {SUPPORTED_VERSION}")


def _validate_framerate(data: dict[str, Any], report: Report) -> None:
    fps = data.get("fps")
    if not isinstance(fps, int) or isinstance(fps, bool) or not 1 <= fps <= 120:
        report.error("fps", "fps 必须是 1..120 之间的整数")
        return
    if fps not in (24, 25, 30, 60):
        report.warn("fps", f"fps={fps} 不是常见值（24/25/30/60），请确认渲染目标")


def _validate_dimensions(data: dict[str, Any], report: Report) -> None:
    """校验画布尺寸。

    字段类型不可信，先把非法值过滤掉再比较，否则 `"1080" > 1920`
    这类比较会抛出 TypeError，让校验器本身崩溃。
    """
    resolved: dict[str, int] = {}
    for key, default in (("width", 1080), ("height", 1920)):
        value = data.get(key, default)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            report.error(key, f"{key} 必须是正整数")
        elif value % 2 != 0:
            # H.264 yuv420p 要求宽高为偶数，奇数会导致编码失败。
            report.error(key, f"{key}={value} 是奇数，H.264 编码要求宽高为偶数")
        else:
            resolved[key] = value
    if len(resolved) == 2 and resolved["width"] > resolved["height"]:
        report.warn("width", "宽度大于高度，与竖屏短视频的定位不符")


def _validate_scenes(data: dict[str, Any], report: Report, fps: int) -> None:
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        report.error("scenes", "scenes 必须是非空数组")
        return

    seen_ids: dict[str, int] = {}
    total_frames = 0
    for index, scene in enumerate(scenes):
        path = f"scenes[{index}]"
        if not isinstance(scene, dict):
            report.error(path, "场景必须是 JSON 对象")
            continue

        scene_id = scene.get("id")
        if not isinstance(scene_id, str) or not scene_id:
            report.error(f"{path}.id", "场景缺少非空字符串 id")
        elif not _SCENE_ID_RE.match(scene_id):
            report.error(f"{path}.id", f"id '{scene_id}' 只允许字母、数字、下划线和连字符")
        elif scene_id in seen_ids:
            report.error(f"{path}.id", f"id '{scene_id}' 与 scenes[{seen_ids[scene_id]}] 重复")
        else:
            seen_ids[scene_id] = index

        _validate_duration(scene, f"{path}.durationInFrames", report)
        if "narration" in scene and not isinstance(scene["narration"], str):
            report.error(f"{path}.narration", "narration 必须是字符串；静音场景请省略或使用空字符串")
        _validate_scene_payload(scene, path, report)

        duration = scene.get("durationInFrames")
        if isinstance(duration, int) and not isinstance(duration, bool) and duration > 0:
            total_frames += duration

    if total_frames > 0:
        seconds = total_frames / fps
        if seconds > 180:
            report.warn(
                "scenes",
                f"总时长约 {seconds:.0f} 秒，超过竖屏短视频的常见上限，请确认是有意为之",
            )


def _validate_duration(scene: dict[str, Any], path: str, report: Report) -> None:
    duration = scene.get("durationInFrames")
    if not isinstance(duration, int) or isinstance(duration, bool):
        report.error(path, "durationInFrames 必须是整数帧数")
    elif duration <= 0:
        report.error(path, f"durationInFrames={duration} 必须大于 0")


def _validate_scene_payload(scene: dict[str, Any], path: str, report: Report) -> None:
    scene_type = scene.get("type")
    if not isinstance(scene_type, str) or not scene_type:
        report.error(f"{path}.type", "场景缺少非空字符串 type")
        return
    if scene_type not in _SCENE_FIELDS:
        report.warn(
            f"{path}.type",
            f"类型 '{scene_type}' 不在已知组件清单中，渲染前请确认网页已实现该类型",
        )
        return

    data_field = scene.get("data")
    if not isinstance(data_field, dict):
        report.error(f"{path}.data", "已知类型的场景必须提供 data 对象")
        return

    spec = _SCENE_FIELDS[scene_type]
    for name in sorted(spec["required"]):
        if name not in data_field:
            report.error(f"{path}.data.{name}", f"类型 '{scene_type}' 缺少必填字段 '{name}'")
    for name in sorted(set(data_field) - spec["required"] - spec["optional"]):
        report.warn(f"{path}.data.{name}", f"类型 '{scene_type}' 未定义字段 '{name}'，网页将忽略它")

    if scene_type in ("timeline", "list"):
        items = data_field.get("items")
        if "items" in data_field and (not isinstance(items, list) or not items):
            report.error(f"{path}.data.items", "items 必须是非空数组")
        elif isinstance(items, list):
            for i, item in enumerate(items):
                if isinstance(item, str) and not item.strip():
                    report.error(f"{path}.data.items[{i}]", "文本项不能是空白字符串")

    if "emphasis" in data_field:
        _validate_emphasis(data_field["emphasis"], f"{path}.data.emphasis", report)

    if scene_type == "diagram":
        _validate_diagram(data_field, f"{path}.data", report)


def _validate_emphasis(value: Any, path: str, report: Report) -> None:
    """emphasis 是要高亮的短语列表，网页据此在文本中标记重点。"""
    if not isinstance(value, list) or not value:
        report.error(path, "emphasis 必须是非空数组")
        return
    for i, phrase in enumerate(value):
        if not isinstance(phrase, str) or not phrase.strip():
            report.error(f"{path}[{i}]", "emphasis 的每一项必须是非空字符串")


def _validate_diagram(data_field: dict[str, Any], path: str, report: Report) -> None:
    nodes = data_field.get("nodes")
    if "nodes" in data_field and (not isinstance(nodes, list) or not nodes):
        report.error(f"{path}.nodes", "nodes 必须是非空数组")
        return
    if not isinstance(nodes, list):
        return

    node_ids: set[str] = set()
    for i, node in enumerate(nodes):
        if isinstance(node, str):
            if not node.strip():
                report.error(f"{path}.nodes[{i}]", "节点文本不能是空白字符串")
            else:
                node_ids.add(node)
        elif isinstance(node, dict) and isinstance(node.get("id"), str) and node["id"]:
            node_ids.add(node["id"])
        else:
            report.error(f"{path}.nodes[{i}]", "节点必须是字符串或含 id 的对象")

    edges = data_field.get("edges", [])
    if not isinstance(edges, list):
        report.error(f"{path}.edges", "edges 必须是数组")
        return
    for i, edge in enumerate(edges):
        pair: list[Any] | None = None
        if isinstance(edge, list) and len(edge) == 2:
            pair = edge
        elif isinstance(edge, dict):
            pair = [edge.get("from"), edge.get("to")]
        if not pair or not all(isinstance(v, str) and v for v in pair):
            report.error(f"{path}.edges[{i}]", "边必须是 [from, to] 数组或含 from/to 的对象")
        elif node_ids and (pair[0] not in node_ids or pair[1] not in node_ids):
            report.error(f"{path}.edges[{i}]", f"边 {pair[0]} -> {pair[1]} 引用了不存在的节点")


@dataclass(frozen=True)
class Scene:
    """解析后的单个场景。start_frame 由前一场景的时长累加得到。"""

    id: str
    type: str
    duration_in_frames: int
    start_frame: int
    data: dict[str, Any]
    narration: str | None

    @property
    def end_frame(self) -> int:
        """不包含在场景内：返回值等于下一场景的 start_frame。"""
        return self.start_frame + self.duration_in_frames


@dataclass(frozen=True)
class Storyboard:
    """解析后的完整分镜脚本。"""

    version: int
    fps: int
    width: int
    height: int
    title: str | None
    scenes: tuple[Scene, ...]

    @property
    def total_frames(self) -> int:
        return sum(s.duration_in_frames for s in self.scenes)

    def scene_at(self, frame: int) -> Scene:
        """返回包含给定帧的场景；越界时钳制到首/末场景，保证 seek 稳定。"""
        if not self.scenes:
            raise ValueError("分镜脚本没有任何场景")
        for scene in self.scenes:
            if scene.start_frame <= frame < scene.end_frame:
                return scene
        return self.scenes[-1] if frame >= self.total_frames else self.scenes[0]


def load(path: str | Path) -> tuple[Storyboard | None, Report]:
    """从 JSON 文件加载并校验分镜脚本。

    返回 (storyboard, report)：解析失败或存在 error 时 storyboard 为 None，
    便于调用方在报告与模型之间二选一使用。
    """
    path = Path(path)
    report = Report()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        report.error("$", f"无法读取脚本文件 {path}: {exc}")
        return None, report

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        report.error("$", f"JSON 解析失败（第 {exc.lineno} 行第 {exc.colno} 列）: {exc.msg}")
        return None, report

    report = validate(data)
    if not report.ok:
        return None, report
    return _build(data, report), report


def _build(data: dict[str, Any], report: Report) -> Storyboard:
    """把已通过校验的 dict 构造为 Storyboard。"""
    scenes: list[Scene] = []
    cursor = 0
    for index, item in enumerate(data.get("scenes", [])):
        duration = item["durationInFrames"]
        scenes.append(
            Scene(
                id=item["id"],
                type=item["type"],
                duration_in_frames=duration,
                start_frame=cursor,
                data=item.get("data", {}),
                narration=item.get("narration"),
            )
        )
        cursor += duration
    return Storyboard(
        version=data["version"],
        fps=data["fps"],
        width=data.get("width", 1080),
        height=data.get("height", 1920),
        title=data.get("title"),
        scenes=tuple(scenes),
    )
