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

from . import catalog

# 当前支持的脚本版本。字段结构变化时必须递增，并在校验时给出明确提示。
SUPPORTED_VERSION = 1

# 场景 ID 允许的字符：字母、数字、下划线、连字符。用于网页 DOM 与日志定位。
_SCENE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")

# 已知场景类型及其 data 中的必填/可选字段。新增类型时同步更新
# docs/PROJECT_PLAN.md 的组件清单与 SKILL.md 中的说明。
#
# annotations 是「图形标注」：写在图形上、用来点明图示含义的短词（例如天平的
# 「命运的考试 / 一次上场」）。它属于内容层，因此和文案一样写在分镜里，由网页
# 决定画在哪个位置；键名由每支视频的构图约定，校验器只保证它是短字符串映射。
_SCENE_FIELDS: dict[str, dict[str, set[str]]] = {
    "title": {"required": {"text"}, "optional": {"subtitle", "emphasis", "annotations", "figure"}},
    "quote": {"required": {"text"}, "optional": {"attribution", "emphasis", "annotations", "figure"}},
    "comparison": {"required": {"left", "right"}, "optional": {"title", "annotations", "figure"}},
    "timeline": {"required": {"items"}, "optional": {"title", "annotations", "figure"}},
    "diagram": {"required": {"nodes"}, "optional": {"edges", "title", "annotations", "figure"}},
    "number": {"required": {"value"}, "optional": {"label", "caption", "annotations", "figure"}},
    "list": {"required": {"items"}, "optional": {"title", "annotations", "figure"}},
    "conclusion": {"required": {"text"}, "optional": {"action", "emphasis", "annotations", "figure"}},
}

# 声明用哪个视觉组件画这一幕。详见 references/figure-catalog.md。
_FIGURE_FIELDS = {"kind", "labels", "motion", "params"}
_FIGURE_MOTIONS = ("calm", "normal", "impact")
_VISUAL_THEMES = ("dark", "light")
_VISUAL_LAYOUTS = ("center", "lower")

# 设计语言预设：在既有令牌之外启用一套完整的版式系统（字号阶、间距网格、
# 对比度下限、观感闸门）。未声明时画面与既有作品逐帧一致，详见
# references/keynote-design-system.md。
_VISUAL_PRESETS = ("keynote",)

# 参与「单行字数」检查的文本字段，以及各字段的推荐上限。
# 依据 references/visual-spec.md 的字号下限与行数约定：超过上限时应拆场景，
# 而不是缩小字号。标题类允许更长，因为短标题强行折行反而破坏构图。
_MAX_LINE_CHARS = 14
_TEXT_LINE_LIMITS: dict[str, int] = {
    "text": 20,
    "title": 16,
    "left": 8,
    "right": 8,
    "subtitle": 20,
    "action": 16,
    "label": 16,
    "caption": 20,
}

# 低于该帧数的场景来不及完成一次入场动效（30fps 下 0.8 秒）。
_MIN_SCENE_FRAMES = 24

# 图形标注是画在图上的词，必须短到能塞进图形旁边；过长会挤掉图形本身。
_ANNOTATION_MAX_CHARS = 12

# 场景内会被强调短语覆盖的文本字段，用于检查 emphasis 是否真的能命中。
_EMPHASIS_TEXT_FIELDS: dict[str, tuple[str, ...]] = {
    "title": ("text", "subtitle"),
    "quote": ("text", "attribution"),
    "conclusion": ("text", "action"),
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


def validate(data: Any, *, declarative: bool = False) -> Report:
    """校验分镜脚本 dict，返回结构化报告。data 不是 dict 时直接判错。"""
    report = Report()
    if not isinstance(data, dict):
        report.error("$", "脚本根节点必须是 JSON 对象")
        return report

    _validate_version(data, report)
    _validate_framerate(data, report)
    _validate_dimensions(data, report)
    if "visual" in data:
        _validate_visual(
            data["visual"],
            "visual",
            {"theme": _VISUAL_THEMES, "preset": _VISUAL_PRESETS},
            report,
        )
    if declarative:
        _reject_unknown(data, {"version", "fps", "width", "height", "title", "scenes", "visual"}, "", report)
    # 后续换算必须用可信的 fps；非法值已在校验中报错，这里只是避免算术崩溃
    _validate_scenes(data, report, _safe_fps(data), declarative)
    return report


def _reject_unknown(value: dict[str, Any], allowed: set[str], path: str, report: Report) -> None:
    for key in sorted(set(value) - allowed):
        report.error(f"{path}.{key}" if path else key, "声明式路径不支持此字段")


def _validate_visual(value: Any, path: str, fields: dict[str, tuple[str, ...]], report: Report) -> None:
    if not isinstance(value, dict):
        report.error(path, "visual 必须是对象")
        return
    _reject_unknown(value, set(fields), path, report)
    for name, choices in fields.items():
        if name in value and value[name] not in choices:
            report.error(f"{path}.{name}", f"必须是 {'/'.join(choices)} 之一")


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


def _validate_scenes(data: dict[str, Any], report: Report, fps: int, declarative: bool = False) -> None:
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
        if "visual" in scene:
            _validate_visual(scene["visual"], f"{path}.visual", {"layout": _VISUAL_LAYOUTS}, report)
        if declarative:
            _reject_unknown(scene, {"id", "type", "durationInFrames", "narration", "data", "visual"}, path, report)

        scene_id = scene.get("id")
        if not isinstance(scene_id, str) or not scene_id:
            report.error(f"{path}.id", "场景缺少非空字符串 id")
        elif not _SCENE_ID_RE.match(scene_id):
            report.error(f"{path}.id", f"id '{scene_id}' 只允许字母、数字、下划线和连字符")
        elif scene_id in seen_ids:
            report.error(f"{path}.id", f"id '{scene_id}' 与 scenes[{seen_ids[scene_id]}] 重复")
        else:
            seen_ids[scene_id] = index

        _validate_duration(scene, f"{path}.durationInFrames", report, fps)
        if "narration" in scene and not isinstance(scene["narration"], str):
            report.error(f"{path}.narration", "narration 必须是字符串；静音场景请省略或使用空字符串")
        _validate_scene_payload(scene, path, report, declarative)

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


def _validate_duration(scene: dict[str, Any], path: str, report: Report, fps: int) -> None:
    duration = scene.get("durationInFrames")
    if not isinstance(duration, int) or isinstance(duration, bool):
        report.error(path, "durationInFrames 必须是整数帧数")
    elif duration <= 0:
        report.error(path, f"durationInFrames={duration} 必须大于 0")
    elif duration < _MIN_SCENE_FRAMES:
        # 短于此长度的场景，入场动效会被压缩到看不清，通常意味着应该并入相邻场景。
        report.warn(
            path,
            f"仅 {duration} 帧（{duration / fps:.1f} 秒 @{fps}fps），"
            f"入场动效会被压缩到看不清，建议并入相邻场景",
        )


def _validate_scene_payload(scene: dict[str, Any], path: str, report: Report, declarative: bool = False) -> None:
    scene_type = scene.get("type")
    if not isinstance(scene_type, str) or not scene_type:
        report.error(f"{path}.type", "场景缺少非空字符串 type")
        return
    if scene_type not in _SCENE_FIELDS:
        (report.error if declarative else report.warn)(
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
        (report.error if declarative else report.warn)(
            f"{path}.data.{name}", f"类型 '{scene_type}' 未定义字段 '{name}'"
        )

    if scene_type in ("timeline", "list"):
        items = data_field.get("items")
        if "items" in data_field and (not isinstance(items, list) or not items):
            report.error(f"{path}.data.items", "items 必须是非空数组")
        elif isinstance(items, list):
            for i, item in enumerate(items):
                if isinstance(item, str) and not item.strip():
                    report.error(f"{path}.data.items[{i}]", "文本项不能是空白字符串")
                elif isinstance(item, str):
                    _warn_on_long_line(item, f"{path}.data.items[{i}]", report)

    if "emphasis" in data_field:
        _validate_emphasis(data_field["emphasis"], f"{path}.data.emphasis", report)
        _warn_on_unmatched_emphasis(scene_type, data_field, f"{path}.data.emphasis", report)

    if "annotations" in data_field:
        _validate_annotations(data_field["annotations"], f"{path}.data.annotations", report)

    if "figure" in data_field:
        _validate_figure(data_field["figure"], f"{path}.data.figure", report, declarative)
    elif declarative and catalog.resolve_kind(scene_type, None) is None:
        report.error(f"{path}.data.figure.kind", "此场景类型没有默认组件，请显式指定 kind")

    if scene_type == "diagram":
        _validate_diagram(data_field, f"{path}.data", report)

    _warn_on_component_capacity(scene_type, data_field, f"{path}.data", report)
    _warn_on_long_text(data_field, f"{path}.data", report)


def _validate_figure(value: Any, path: str, report: Report, declarative: bool = False) -> None:
    """校验选组件的那一小段声明。

    结构层保证 kind 是字符串、motion 是三个节奏之一、labels/params 是对象；
    「这个 kind 存不存在、它认识哪些标注键、能吃下多少条目」由组件目录说了算
    （见 references/figure-catalog.md 与 a2v/catalog.py）。
    """
    if not isinstance(value, dict):
        report.error(path, "figure 必须是对象，形如 {\"kind\": \"iceberg\"}")
        return
    kind = value.get("kind")
    if not isinstance(kind, str) or not kind.strip():
        report.error(f"{path}.kind", "figure.kind 必须是非空字符串")
        return
    for name in sorted(set(value) - _FIGURE_FIELDS):
        (report.error if declarative else report.warn)(f"{path}.{name}", f"figure 未定义字段 '{name}'")
    motion = value.get("motion")
    if motion is not None and motion not in _FIGURE_MOTIONS:
        report.error(
            f"{path}.motion",
            f"motion 必须是 {'/'.join(_FIGURE_MOTIONS)} 之一，实际为 {motion!r}",
        )
    for name in ("labels", "params"):
        if name in value and not isinstance(value[name], dict):
            report.error(f"{path}.{name}", f"figure.{name} 必须是对象")
    if isinstance(value.get("labels"), dict):
        _validate_annotations(value["labels"], f"{path}.labels", report)
    if value.get("params"):
        # 机制已经接通（会带进组件），但当前没有组件读取任何键，
        # 与其让人以为写了就生效，不如在开渲前说清楚
        (report.error if declarative else report.warn)(
            f"{path}.params",
            "当前没有组件读取 params，写了不会改变画面；需要可调几何时先在组件里实现",
        )

    entry = catalog.component(kind.strip())
    if entry is None:
        # 未知组件只警告：目录允许扩展，网页挂载时会立刻抛出更明确的错误
        (report.error if declarative else report.warn)(
            f"{path}.kind",
            f"组件 '{kind}' 不在目录中（已知：{'、'.join(catalog.known_kinds())}），"
            "渲染前请确认网页已注册该组件",
        )
        return
    labels = value.get("labels")
    if isinstance(labels, dict):
        unknown = sorted(set(labels) - entry.labels)
        if unknown:
            (report.error if declarative else report.warn)(
                f"{path}.labels.{unknown[0]}",
                f"组件 '{kind}' 不认识标注键 {('、'.join(unknown))}，"
                f"它认识的是 {('、'.join(sorted(entry.labels)))}；写错的标签不会显示",
            )


def _warn_on_component_capacity(
    scene_type: str, data_field: dict[str, Any], path: str, report: Report
) -> None:
    """按组件声明的容量检查条目数。

    组件会按数量收缩几何，但超出舒适区后标签会挤在一起，读不出来。
    默认组件也参与检查：分镜没写 figure 时它照样会挂载。
    """
    entry = catalog.component(catalog.resolve_kind(scene_type, data_field.get("figure")) or "")
    if entry is None or entry.items is None:
        return
    for field in ("items", "nodes"):
        value = data_field.get(field)
        if not isinstance(value, list):
            continue
        low, high = entry.items
        if not low <= len(value) <= high:
            report.warn(
                f"{path}.{field}",
                f"组件 '{entry.kind}' 适合 {low}–{high} 项，当前 {len(value)} 项，"
                "再多会挤在一起读不出来",
            )


def _validate_annotations(value: Any, path: str, report: Report) -> None:
    """校验图形标注：非空的「短词 -> 短词」映射。

    键名（如 left / right / gauge）由每支视频的构图约定，校验器不预设枚举，
    只保证网页拿到的是一组能安全画进图形的短字符串，并提醒过长的标注。
    """
    if not isinstance(value, dict) or not value:
        report.error(path, "annotations 必须是非空对象，形如 {\"left\": \"命运的考试\"}")
        return
    for key in sorted(value.keys()):
        key_path = f"{path}.{key}"
        if not isinstance(key, str) or not key.strip():
            report.error(path, "annotations 的键必须是非空字符串")
            continue
        item = value[key]
        if not isinstance(item, str) or not item.strip():
            report.error(key_path, "图形标注必须是非空字符串")
            continue
        if len(item.strip()) > _ANNOTATION_MAX_CHARS:
            report.warn(
                key_path,
                f"图形标注 {len(item.strip())} 个字符，超过 {_ANNOTATION_MAX_CHARS} 字，"
                "画在图形旁边会挤压构图",
            )


def _warn_on_long_text(data_field: dict[str, Any], path: str, report: Report) -> None:
    """按视觉规范检查单行字数：超出上限时应拆场景，而不是缩小字号。

    这些是**警告**：文案长度属于表达取舍，校验器只负责在开渲前提醒，
    由作者决定是否拆分；`--strict` 可以把它们提升为失败。
    分镜里的换行符是硬换行，因此逐行判断而不是判断整段长度。
    """
    for field, limit in _TEXT_LINE_LIMITS.items():
        value = data_field.get(field)
        if not isinstance(value, str):
            continue
        _warn_on_long_line(value, f"{path}.{field}", report, limit)


def _warn_on_long_line(text: str, path: str, report: Report, limit: int = _MAX_LINE_CHARS) -> None:
    lines = text.split("\n")
    for index, line in enumerate(lines):
        stripped = line.strip()
        if len(stripped) <= limit:
            continue
        where = f"{path} 第 {index + 1} 行" if len(lines) > 1 else path
        report.warn(
            where,
            f"单行 {len(stripped)} 个字符，超过 {limit} 字的上限，建议拆成多个场景或手动换行",
        )


def _warn_on_unmatched_emphasis(
    scene_type: str, data_field: dict[str, Any], path: str, report: Report
) -> None:
    """强调短语必须能在画面文本里原样命中，否则网页标不出重点色。

    网页按「第一处出现」替换，因此短语里多一个空格或标点就会静默失效；
    这里提前把这类不可见的失效暴露出来。
    """
    phrases = data_field.get("emphasis")
    if not isinstance(phrases, list):
        return
    fields = _EMPHASIS_TEXT_FIELDS.get(scene_type)
    if not fields:
        # 其他类型的文案字段不在本模块的检查范围内，避免误报。
        return
    haystack = "\n".join(
        value for value in (data_field.get(name) for name in fields) if isinstance(value, str)
    )
    if not haystack:
        return
    for index, phrase in enumerate(phrases):
        if not isinstance(phrase, str) or not phrase.strip():
            continue
        if phrase not in haystack:
            report.warn(
                f"{path}[{index}]",
                f"强调短语 '{phrase}' 未出现在该场景的文本中，画面上不会生效",
            )


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
    #: 根级视觉声明（主题 / 设计语言预设）。原样保留，便于体检与渲染判断
    #: 这支片子用的是哪套版式，而不必回头再读一遍 JSON。
    visual: dict[str, Any] = field(default_factory=dict)

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


def load(path: str | Path, *, declarative: bool = False) -> tuple[Storyboard | None, Report]:
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

    report = validate(data, declarative=declarative)
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
        visual=dict(data.get("visual") or {}),
    )
