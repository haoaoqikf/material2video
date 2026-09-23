"""分镜脚本（storyboard）的数据模型与校验。

分镜脚本是「文章 → 场景树画面 → 视频」链路中的内容真源：
- 共享 React composition 读取同一份 JSON，按场景树逐节点绘制画面；
- 渲染脚本依据它推导总帧数并驱动逐帧截图。

本模块只负责解析与结构校验，不做任何 I/O 之外的事情，
保证校验逻辑可以在纯 Python 单元测试中复用。

当前只支持场景树 v2（version=2 + schemaVersion=2）。旧版整页组件分镜
（version=1，data.figure.kind）必须先经 scripts/migrate_storyboard.py
显式迁移，任何入口都不会静默回退到旧渲染路径。
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import catalog
from . import code_scenes
from . import beats as beat_mod
from . import visual_narrative as vn
from .errors import A2VError

# 当前支持的版本：场景树 v2。字段结构变化时必须递增，并在校验时给出明确提示。
SCENE_TREE_VERSION = 2

# 动效配方全集。单个原语允许哪些配方由原语注册表（catalog.PRIMITIVE_CATALOG）声明，
# 这里只负责拦截完全未知的配方名。
_MOTION_RECIPES = frozenset({"reveal", "fade", "rise", "count", "draw"})

# 场景树节点禁止的可执行/逃生口字段：自由坐标与样式脚本会让安全区、
# 响应式布局和契约检查全部失效。
_BLOCKED_NODE_FIELDS = frozenset({"html", "css", "script", "javascript", "style", "x", "y", "transform", "package"})

# 结构性字段：按原语校验属性时豁免（属性清单见原语注册表）。
_STRUCTURAL_NODE_FIELDS = frozenset({"id", "type", "children"})

# 场景 ID / 节点 ID 允许的字符：字母、数字、下划线、连字符。用于网页 DOM 与日志定位。
_SCENE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")

# 设计语言预设：在既有令牌之外启用一套完整的版式系统（字号阶、间距网格、
# 对比度下限、观感闸门）。未声明时画面与既有作品逐帧一致，详见
# references/keynote-design-system.md。
_VISUAL_PRESETS = ("keynote",)
_VISUAL_THEMES = ("dark", "light")

#: 幕角标（`visual.kicker`）的字数上限。角标是一个词，不是一个句子；
#: 它是读者第一眼看到的定位词，长了就变成第二行副标题。
_KICKER_MAX_CHARS = 8

# 单行字数上限：依据 references/visual-spec.md 的字号下限与行数约定，
# 超过上限时应拆场景，而不是缩小字号。分镜里的换行符是硬换行，因此逐行判断。
_MAX_LINE_CHARS = 20

# 低于该帧数的场景来不及完成一次入场动效（30fps 下 0.8 秒）。
_MIN_SCENE_FRAMES = 24

#: 图表数据点标签的字数上限：与图形标注同一量级，过长会挤掉图形本身。
_CHART_LABEL_MAX_CHARS = 12

#: 单幕场景树的节点总数上限。与树深、单节点子数一起控制渲染成本，
#: 并让「往一幕里塞整个故事」的构图在开渲前暴露。
_MAX_NODES_PER_SCENE = 48

#: 节点属性的受控枚举（与 web/src/schema/storyboard.ts 的 zod 声明一致）。
#: direction 的取值按原语拆开：group 用横竖，connector 用箭头方向。
_NODE_PROP_ENUMS: dict[str, set[str]] = {
    "align": {"start", "center", "end", "stretch"},
    "gap": {"none", "xs", "sm", "md", "lg", "xl"},
    "role": {"hero", "headline", "title", "body", "label", "caption"},
    "shape": {"circle", "rect", "line", "spotlight", "ring"},
    "state": {"rest", "focus", "muted", "done"},
    "icon": set(catalog.ICON_NAMES),
    "chart": {"bar", "line", "pie"},
    "ratio": {"1:1", "1:2", "2:1", "2:3", "3:2"},
}
_NODE_DIRECTION_ENUMS: dict[str, set[str]] = {
    "group": {"horizontal", "vertical"},
    "connector": {"ltr", "rtl", "ttb", "btt"},
    # 中层原语用同一组方向：流程与时间轴按它排列，循环按它决定绕行方向。
    "flow": {"ltr", "rtl", "ttb", "btt"},
    "timeline": {"ltr", "rtl", "ttb", "btt"},
    "cycle": {"cw", "ccw"},
}


@dataclass(frozen=True)
class Issue:
    """一条校验结果。path 指向 JSON 内的层级位置，便于 AI 定位修正。"""

    level: str  # "error" 或 "warning"
    path: str  # 例如 "scenes[2].sceneTree.children[0].contentRef"
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


def validate(data: Any, strict: bool = False) -> Report:
    """校验分镜脚本 dict，返回结构化报告。data 不是 dict 时直接判错。

    ``strict``（对应 CLI 的 ``--strict``）额外执行视觉叙事契约：
    逐幕缺少视觉论证字段时不再只是兼容警告，而是错误，并执行版本化的
    全片视觉叙事预算（文字幕占比、连续文字幕、非文字模式覆盖与
    声明/结构矛盾）。普通校验保持兼容：旧分镜只收到警告，预览与
    渲染仍可继续。
    """
    report = Report()
    if not isinstance(data, dict):
        report.error("$", "脚本根节点必须是 JSON 对象")
        return report

    if data.get("version") == SCENE_TREE_VERSION:
        return _validate_v2(data, strict=strict)
    if data.get("version") == 1:
        report.error(
            "version",
            "旧版整页组件分镜不能进入新版入口；请先运行 migrate_storyboard.py 显式迁移到场景树 v2",
        )
        return report
    report.error("version", f"不支持的脚本版本 {data.get('version')!r}，当前支持场景树 v2（version=2）")
    return report


def _validate_v2(data: dict[str, Any], strict: bool = False) -> Report:
    report = Report()
    _reject_unknown(data, {"version", "schemaVersion", "fps", "width", "height", "title", "visualDirection", "directingVersion", "directingBrief", "scenes", "visual"}, "", report)
    if data.get("schemaVersion") != SCENE_TREE_VERSION:
        report.error("schemaVersion", f"场景树版本必须是 {SCENE_TREE_VERSION}")
    _validate_framerate(data, report)
    _validate_dimensions(data, report)
    _validate_root_visual(data.get("visual"), report)
    direction = data.get("visualDirection")
    if not isinstance(direction, dict):
        report.error("visualDirection", "visualDirection 必须是对象")
    else:
        _validate_visual_direction(direction, report)
    directing_version = data.get("directingVersion")
    if directing_version is not None and directing_version != 1:
        report.error("directingVersion", "directingVersion 当前只支持 1")
    brief = data.get("directingBrief")
    if directing_version == 1 and brief is None:
        report.error("directingBrief", "directingVersion=1 必须同时提供 directingBrief")
    if brief is not None:
        if not isinstance(brief, dict):
            report.error("directingBrief", "directingBrief 必须是对象")
        else:
            _reject_unknown(brief, {"thesis", "audienceShift", "emotionalArc", "visualMotif", "stylePack", "avoid"}, "directingBrief", report)
            for key in ("thesis", "audienceShift", "visualMotif"):
                if not isinstance(brief.get(key), str) or not brief[key].strip():
                    report.error(f"directingBrief.{key}", "必须是非空字符串")
            if not isinstance(brief.get("emotionalArc"), list) or len(brief["emotionalArc"]) < 2:
                report.error("directingBrief.emotionalArc", "必须是至少两个情绪阶段")
            if brief.get("stylePack") not in {"editorial", "cinematic", "technical", "poetic"}:
                report.error("directingBrief.stylePack", "必须是 editorial/cinematic/technical/poetic 之一")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        report.error("scenes", "scenes 必须是非空数组")
        return report
    seen_scenes: set[str] = set()
    total_frames = 0
    for index, scene in enumerate(scenes):
        path = f"scenes[{index}]"
        if not isinstance(scene, dict):
            report.error(path, "场景必须是对象")
            continue
        _reject_unknown(scene, {"id", "type", "durationInFrames", "narration", "narrationSegments", "beats", "data", "visualIntent", "camera", "transition", "sceneTree", "motions", "visual", "renderer"}, path, report)
        _validate_directing_scene(scene, path, report)
        scene_id = scene.get("id")
        if not isinstance(scene_id, str) or not _SCENE_ID_RE.match(scene_id):
            report.error(f"{path}.id", "场景 id 必须是非空安全标识符")
        elif scene_id in seen_scenes:
            report.error(f"{path}.id", f"场景 id {scene_id} 重复")
        else:
            seen_scenes.add(scene_id)
        _validate_duration(scene, f"{path}.durationInFrames", report, _safe_fps(data))
        if "narration" in scene and not isinstance(scene["narration"], str):
            report.error(f"{path}.narration", "narration 必须是字符串；静音场景请省略或使用空字符串")
        if not isinstance(scene.get("data"), dict):
            report.error(f"{path}.data", "data 必须是对象")
        _validate_visual_intent(scene.get("visualIntent"), f"{path}.visualIntent", report, strict=strict)
        _validate_scene_visual(scene.get("visual"), scene.get("type"), f"{path}.visual", report)
        kind = _validate_renderer(scene, path, report)
        node_types: dict[str, str] | None = None
        if kind == "tree":
            _validate_scene_tree(scene.get("sceneTree"), scene, path, report)
            _validate_motions(scene.get("motions"), f"{path}.motions", report, scene, path)
            node_types = _scene_node_types(scene.get("sceneTree"))
        _validate_beats(scene, path, report, node_types=node_types, strict=strict)
        _warn_on_scene_copy(scene, path, report)
        duration = scene.get("durationInFrames")
        if isinstance(duration, int) and not isinstance(duration, bool) and duration > 0:
            total_frames += duration
    if total_frames > 0:
        seconds = total_frames / _safe_fps(data)
        if seconds > 180:
            report.warn(
                "scenes",
                f"总时长约 {seconds:.0f} 秒，超过竖屏短视频的常见上限，请确认是有意为之",
            )
    _validate_visual_narrative(data, report, strict=strict)
    return report


def _validate_visual_narrative(data: dict[str, Any], report: Report, *, strict: bool) -> None:
    """全片视觉叙事预算（版本化规则，阈值见 visual_narrative.RULE_VERSION）。

    预算规则只在严格校验执行：文字幕占比与连续文字幕是硬门槛，
    报告始终列出场景 id、实际值与允许上限。普通校验保持沉默——
    它的兼容契约是「旧分镜可预览、可渲染」，预算问题留给严格验收。
    """
    if not strict:
        return
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return
    analysis = vn.analyze(data)
    scene_index = {
        str(scene.get("id")): index for index, scene in enumerate(scenes) if isinstance(scene, dict)
    }
    for finding in analysis["findings"]:
        rule = finding["rule"]
        detail = finding["detail"]
        scene_list = "、".join(str(scene_id) for scene_id in finding["scenes"]) or "（无）"
        if rule == "text-scene-budget":
            report.error(
                "scenes",
                f"文字幕 {detail['actual']}/{detail['sceneCount']} 幕，超过允许上限 "
                f"{detail['limit']}（{vn.TEXT_SCENE_RATIO:.0%} 向上取整）：涉及 {scene_list}",
            )
        elif rule == "adjacent-text-scenes":
            report.error(
                "scenes",
                f"相邻两幕均为文字幕：{scene_list}；文字幕之间必须隔开论证型图形场景",
            )
        elif rule == "non-text-mode-coverage":
            report.error(
                "scenes",
                f"非文字视觉模式只有 {detail['actual']} 种（{'、'.join(detail['modes']) or '无'}），"
                f"少于 {detail['sceneCount']} 幕作品要求的 {detail['required']} 种",
            )
        elif rule == "declaration-structure-conflict":
            position = scene_index.get(str(finding["scenes"][0]), 0)
            report.error(
                f"scenes[{position}].visualIntent.mode",
                f"声明为 {detail['declaredMode']}，但场景树只有文字、数值、符号图标、"
                "装饰形状或包裹它们的表面，拿不出论证型结构证据；请改声明为 "
                "typography，或用 chart/image/connector/radial 承担论证",
            )


def _validate_visual_direction(direction: dict[str, Any], report: Report) -> None:
    """视频级视觉策略：字段齐全、取值受控。它是全片编排的约束输入。"""
    required = {"motif", "compositionBias", "density", "rhythm", "avoid"}
    _reject_unknown(direction, required, "visualDirection", report)
    for key in required:
        if key not in direction:
            report.error(f"visualDirection.{key}", "缺少必填字段")
    if "motif" in direction and (not isinstance(direction["motif"], str) or not direction["motif"].strip()):
        report.error("visualDirection.motif", "motif 必须是非空字符串")
    enums = {
        "compositionBias": {"centered", "asymmetric", "mixed"},
        "density": {"sparse", "balanced", "dense"},
        "rhythm": {"restrained", "steady", "dynamic"},
    }
    for key, choices in enums.items():
        if key in direction and direction[key] not in choices:
            report.error(f"visualDirection.{key}", f"必须是 {'/'.join(sorted(choices))} 之一")
    avoid = direction.get("avoid")
    if "avoid" in direction and (not isinstance(avoid, list) or not all(isinstance(item, str) for item in avoid)):
        report.error("visualDirection.avoid", "avoid 必须是字符串数组")


def _validate_directing_scene(scene: dict[str, Any], path: str, report: Report) -> None:
    camera = scene.get("camera")
    if camera is not None:
        if not isinstance(camera, dict):
            report.error(f"{path}.camera", "camera 必须是对象")
        else:
            _reject_unknown(camera, {"shot", "composition", "depth", "focus", "movement"}, f"{path}.camera", report)
            choices = {"shot": {"macro", "close", "medium", "wide"}, "composition": {"center", "left", "right", "split", "full"}, "depth": {"flat", "layered"}, "movement": {"static", "push-in", "pull-out", "pan-left", "pan-right", "orbit"}}
            for key, allowed in choices.items():
                if camera.get(key) not in allowed:
                    report.error(f"{path}.camera.{key}", f"必须是 {'/'.join(sorted(allowed))} 之一")
            if not isinstance(camera.get("focus"), str) or not _SCENE_ID_RE.match(camera.get("focus", "")):
                report.error(f"{path}.camera.focus", "必须是节点 id")
    transition = scene.get("transition")
    if transition is not None:
        if not isinstance(transition, dict):
            report.error(f"{path}.transition", "transition 必须是对象")
        else:
            _reject_unknown(transition, {"kind", "source", "target", "meaning"}, f"{path}.transition", report)
            if transition.get("kind") not in {"inherit", "transform", "dissolve", "break"}:
                report.error(f"{path}.transition.kind", "必须是 inherit/transform/dissolve/break 之一")
            if not isinstance(transition.get("meaning"), str) or not transition["meaning"].strip():
                report.error(f"{path}.transition.meaning", "必须说明转场解释了什么")


#: 逐幕视觉论证字段：导演意图声明，不参与 React 渲染。
#: ``mode`` 用受控枚举（见 visual_narrative.VISUAL_MODES）；
#: 其余四项是非空文本，``showWithoutText`` 不得机械复述 ``claim``。
_INTENT_MODE_FIELD = "mode"
_INTENT_TEXT_FIELDS = ("claim", "showWithoutText", "primaryObject", "motionMeaning")


def _validate_visual_intent(value: Any, path: str, report: Report, strict: bool = False) -> None:
    fields = {
        "relation": {"focus", "contrast", "sequence", "cause", "cycle", "collection"},
        "focus": {"text", "number", "shape", "chart", "path"},
        "composition": {"center", "offset", "split", "radial", "full"},
        "density": {"sparse", "balanced", "dense"},
        "tone": {"calm", "tense", "neutral", "uplifting", "decisive"},
    }
    if not isinstance(value, dict):
        report.error(path, "visualIntent 必须是对象")
        return
    _reject_unknown(value, set(fields) | {_INTENT_MODE_FIELD, *_INTENT_TEXT_FIELDS}, path, report)
    for key, choices in fields.items():
        if value.get(key) not in choices:
            report.error(f"{path}.{key}", f"必须是 {'/'.join(sorted(choices))} 之一")
    mode = value.get(_INTENT_MODE_FIELD)
    if _INTENT_MODE_FIELD in value and mode not in vn.VISUAL_MODES:
        report.error(
            f"{path}.{_INTENT_MODE_FIELD}",
            f"必须是 {'/'.join(vn.VISUAL_MODES)} 之一",
        )
    for key in _INTENT_TEXT_FIELDS:
        if key not in value:
            continue
        text = value[key]
        if not isinstance(text, str) or not text.strip():
            report.error(f"{path}.{key}", "必须是非空字符串：这是逐幕视觉论证的声明字段")
    claim = value.get("claim")
    show = value.get("showWithoutText")
    if isinstance(claim, str) and claim.strip() and isinstance(show, str) and show.strip():
        if vn.is_restatement(show, claim):
            report.error(
                f"{path}.showWithoutText",
                "只是复述 claim（逐字重复或「显示/呈现 + 论点」式包装）："
                "请描述移除标题与正文后仍能看见的关系或变化",
            )
    missing = [key for key in (_INTENT_MODE_FIELD, *_INTENT_TEXT_FIELDS) if key not in value]
    if missing:
        message = (
            f"缺少视觉论证字段 {('、'.join(missing))}：逐幕须声明受控视觉模式、核心论点、"
            "无正文视觉表达、主要视觉对象与动效语义"
        )
        if strict:
            report.error(f"{path}", message)
        else:
            report.warn(
                f"{path}",
                message + "（旧版分镜兼容模式：可预览可渲染，--strict 校验与新的交付闭环会拒绝）",
            )


def _validate_root_visual(value: Any, report: Report) -> None:
    """根级 visual 只允许主题与设计语言预设。"""
    if value is None:
        return
    if not isinstance(value, dict):
        report.error("visual", "visual 必须是对象")
        return
    _reject_unknown(value, {"theme", "preset"}, "visual", report)
    if "theme" in value and value["theme"] not in _VISUAL_THEMES:
        report.error("visual.theme", f"必须是 {'/'.join(_VISUAL_THEMES)} 之一")
    if "preset" in value and value["preset"] not in _VISUAL_PRESETS:
        report.error("visual.preset", f"必须是 {'/'.join(_VISUAL_PRESETS)} 之一")


def _validate_scene_visual(value: Any, scene_type: Any, path: str, report: Report) -> None:
    """幕级 visual 只允许角标；角标是读者可见的文案，必须短、单行、非空。"""
    if value is None:
        return
    if not isinstance(value, dict):
        report.error(path, "visual 必须是对象")
        return
    _reject_unknown(value, {"kicker"}, path, report)
    if "kicker" not in value:
        return
    kicker = value["kicker"]
    if not isinstance(kicker, str):
        report.error(f"{path}.kicker", "角标必须是字符串")
        return
    text = kicker.strip()
    if not text:
        report.error(f"{path}.kicker", "角标不能是空白")
    elif "\n" in text:
        report.error(f"{path}.kicker", "角标必须单行")
    elif len(text) > _KICKER_MAX_CHARS:
        report.error(
            f"{path}.kicker",
            f"角标最多 {_KICKER_MAX_CHARS} 个字——角标是一个词，不是一句话；要说的更多请放进正文",
        )
    if isinstance(scene_type, str) and text and text.lower() == scene_type.strip().lower():
        report.error(
            f"{path}.kicker",
            f"角标不能就是场景类型名（{scene_type}）——那是 schema 字段，不是给读者看的文案",
        )


def _validate_renderer(scene: dict[str, Any], path: str, report: Report) -> str:
    """校验每幕的渲染模式，返回生效的 kind（"tree" 或 "code"）。

    缺省 ``renderer`` 的既有分镜按 ``tree`` 解释（向后兼容，不批量迁移）；
    ``code`` 场景必须给模块标识且不能同时声明 ``sceneTree``——两条画面路径
    每幕二选一，互斥字段在这里拦住，而不是让画面出现两套来源。
    """
    renderer = scene.get("renderer")
    if renderer is None:
        return "tree"
    if not isinstance(renderer, dict):
        report.error(f"{path}.renderer", "renderer 必须是对象：{kind: 'tree'} 或 {kind: 'code', module: '...'}")
        return "tree"
    kind = renderer.get("kind")
    if kind not in ("tree", "code"):
        report.error(f"{path}.renderer.kind", f"无效渲染模式 {kind!r}：必须是 'tree' 或 'code'")
        return "tree"
    allowed = {"kind", "module"} if kind == "code" else {"kind"}
    for key in sorted(set(renderer) - allowed):
        report.error(f"{path}.renderer.{key}", f"renderer.kind={kind} 不支持字段 {key!r}")
    if kind == "code":
        message = code_scenes.validate_module_id(renderer.get("module"))
        if message:
            report.error(f"{path}.renderer.module", message)
        if "sceneTree" in scene:
            report.error(
                f"{path}.sceneTree",
                "code 场景不能声明 sceneTree：渲染模式每幕二选一，画面代码写在模块里",
            )
        motions = scene.get("motions")
        if isinstance(motions, list) and motions:
            report.error(f"{path}.motions", "code 场景不支持 motions：动效由场景代码按帧号实现")
    return kind


def _validate_scene_tree(root: Any, scene: dict[str, Any], scene_path: str, report: Report) -> None:
    """校验单幕场景树：结构、容量、属性、内容引用与数据合法性。"""
    path = f"{scene_path}.sceneTree"
    if not isinstance(root, dict):
        report.error(path, "每幕必须包含一棵场景树（sceneTree）")
        return
    ids: dict[str, str] = {}
    types: dict[str, str] = {}
    counter = [0]
    data_field = scene.get("data") if isinstance(scene.get("data"), dict) else {}
    _validate_scene_node(root, path, report, ids, types, counter, data_field, depth=1)
    if counter[0] > _MAX_NODES_PER_SCENE:
        report.error(path, f"场景树最多 {_MAX_NODES_PER_SCENE} 个节点，当前 {counter[0]} 个")


def _validate_scene_node(
    value: dict[str, Any],
    path: str,
    report: Report,
    ids: dict[str, str],
    types: dict[str, str],
    counter: list[int],
    data_field: dict[str, Any],
    *,
    depth: int,
) -> None:
    counter[0] += 1
    if depth > 8:
        report.error(path, "场景树深度不能超过 8")
    blocked = sorted(set(value) & _BLOCKED_NODE_FIELDS)
    for key in blocked:
        report.error(f"{path}.{key}", "场景树禁止可执行样式、自由坐标或第三方包字段")
    node_id = value.get("id")
    if not isinstance(node_id, str) or not _SCENE_ID_RE.match(node_id):
        report.error(f"{path}.id", "节点 id 必须是非空安全标识符")
    elif node_id in ids:
        report.error(f"{path}.id", f"节点 id {node_id} 与 {ids[node_id]} 重复")
    else:
        ids[node_id] = f"{path}.id"
    node_type = value.get("type")
    entry = catalog.primitive(node_type) if isinstance(node_type, str) else None
    if entry is None:
        report.error(f"{path}.type", f"未知视觉原语 {node_type!r}")
    elif isinstance(node_id, str):
        types[node_id] = node_type
    if entry is not None:
        _validate_node_props(value, entry, path, report)
        _validate_node_content(node_type, value, f"{path}", data_field, report)
    children = value.get("children", [])
    if not isinstance(children, list):
        report.error(f"{path}.children", "children 必须是数组")
        return
    if entry is not None:
        low, high = entry.children
        if len(children) < low or len(children) > high:
            report.error(
                f"{path}.children",
                f"原语 {node_type} 允许 {low}–{high} 个子节点，当前 {len(children)} 个",
            )
    for index, child in enumerate(children):
        if not isinstance(child, dict):
            report.error(f"{path}.children[{index}]", "子节点必须是对象")
            continue
        _validate_scene_node(child, f"{path}.children[{index}]", report, ids, types, counter, data_field, depth=depth + 1)


def _validate_node_props(value: dict[str, Any], entry: Any, path: str, report: Report) -> None:
    """属性必须在该原语注册的清单内，且取值落在受控枚举里。"""
    node_type = entry.type
    unknown = sorted(set(value) - _STRUCTURAL_NODE_FIELDS - set(entry.props))
    for key in unknown:
        report.error(
            f"{path}.{key}",
            f"原语 {node_type} 不支持属性 {key!r}（允许：{'、'.join(sorted(entry.props)) or '无'}）",
        )
    for key, choices in _NODE_PROP_ENUMS.items():
        if key in value and key in entry.props and value[key] not in choices:
            report.error(f"{path}.{key}", f"必须是 {'/'.join(sorted(choices))} 之一")
    direction_choices = _NODE_DIRECTION_ENUMS.get(node_type)
    if direction_choices is not None and "direction" in value and value["direction"] not in direction_choices:
        report.error(f"{path}.direction", f"原语 {node_type} 的 direction 必须是 {'/'.join(sorted(direction_choices))} 之一")
    if "schematic" in value and not isinstance(value["schematic"], bool):
        report.error(f"{path}.schematic", "schematic 必须是布尔值：true 表示这组数值没有来源，画面要出现「示意」标")


def _validate_node_content(node_type: Any, value: dict[str, Any], path: str, data_field: dict[str, Any], report: Report) -> None:
    """内容引用必须解析到 data 中真实存在的字段，数值类内容还要合法。"""
    if node_type == "image":
        source_ref = value.get("sourceRef")
        if not isinstance(source_ref, str) or not source_ref.startswith("data."):
            report.error(f"{path}.sourceRef", "image 原语必须用 sourceRef 指向 data 中的媒体路径")
        elif _resolve_ref(data_field, source_ref) is None:
            report.error(f"{path}.sourceRef", f"媒体引用 {source_ref} 指向不存在的字段")
        return
    ref = value.get("contentRef")
    if ref is None:
        # 量级类原语没有内容引用就只会画一个空盘：这是静默错误，直接报出来。
        if node_type in {"gauge", "pictogram"}:
            report.error(f"{path}.contentRef", f"{node_type} 必须用 contentRef 指向 data 中的数值（0–100）")
        return
    resolved = _resolve_ref(data_field, ref)
    if resolved is None:
        report.error(f"{path}.contentRef", f"内容引用 {ref} 指向不存在的字段")
        return
    if node_type == "text" and not isinstance(resolved, (str, int, float, list)):
        report.error(f"{path}.contentRef", f"文字原语的内容必须是文本或列表，{ref} 指向 {type(resolved).__name__}")
    if node_type == "number":
        if isinstance(resolved, bool) or not isinstance(resolved, (int, float)):
            report.error(f"{path}.contentRef", f"数字原语的内容必须是数值，{ref} 指向 {type(resolved).__name__}")
        elif not math.isfinite(resolved):
            report.error(f"{path}.contentRef", f"数字原语的内容必须是有限数值，{ref} 指向 {resolved!r}")
    if node_type == "chart":
        _validate_chart_values(resolved, f"{path}.contentRef", report)
    if node_type in {"gauge", "pictogram"}:
        # 量级类原语只显示比例：内容必须是一个 0–100 的数值，量纲由幕的文字说明。
        if isinstance(resolved, bool) or not isinstance(resolved, (int, float)) or not math.isfinite(resolved):
            report.error(
                f"{path}.contentRef",
                f"{node_type} 的内容必须是 0–100 的数值，{ref} 指向 {type(resolved).__name__}",
            )
        elif not 0 <= resolved <= 100:
            report.error(f"{path}.contentRef", f"{node_type} 的内容必须落在 0–100，当前 {resolved!r}")


def _validate_chart_values(value: Any, path: str, report: Report) -> None:
    """图表数据必须全部来自分镜：缺失、空数组、缺标签或数值非法都直接报错。"""
    if not isinstance(value, list) or not value:
        report.error(path, "图表内容必须是非空数组，每项形如 {\"label\": \"四月\", \"value\": 12}")
        return
    seen: dict[str, int] = {}
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(item, dict):
            report.error(item_path, "数据点必须是 {\"label\", \"value\"} 对象")
            continue
        label = item.get("label")
        if not isinstance(label, str) or not label.strip():
            report.error(f"{item_path}.label", "数据点标签必须是非空字符串")
        else:
            previous = seen.get(label)
            if previous is None:
                seen[label] = index
            else:
                report.warn(
                    f"{item_path}.label",
                    f"标签「{label}」与第 {previous} 项重复：同一份序列里两根柱子同名，读不出谁是谁",
                )
            if len(label.strip()) > _CHART_LABEL_MAX_CHARS:
                report.warn(
                    f"{item_path}.label",
                    f"数据点标签 {len(label.strip())} 个字符，超过 {_CHART_LABEL_MAX_CHARS} 字上限，会挤压图形本身",
                )
        point_value = item.get("value")
        if isinstance(point_value, bool) or not isinstance(point_value, (int, float)) or not math.isfinite(point_value):
            report.error(f"{item_path}.value", "数据点数值必须是有限数字")


def _resolve_ref(data_field: dict[str, Any], ref: str) -> Any:
    """把 "data.a.b"、"data.list[0]" 解析到分镜数据里；任何一段缺失都返回 None。"""
    current: Any = data_field
    for key in ref[len("data.") :].split("."):
        match = re.fullmatch(r"([^\[\]]+)(?:\[(\d+)\])?", key)
        if not match:
            return None
        name, index = match.group(1), match.group(2)
        if not isinstance(current, dict) or name not in current:
            return None
        current = current[name]
        if index is not None:
            position = int(index)
            if not isinstance(current, list) or position >= len(current):
                return None
            current = current[position]
    return current


def _validate_motions(value: Any, path: str, report: Report, scene: dict[str, Any], scene_path: str) -> None:
    """动效目标用稳定节点 id 定位；配方、时间范围与原语支持度都在开渲前确认。"""
    if not isinstance(value, list):
        report.error(path, "motions 必须是数组")
        return
    ids: dict[str, str] = {}
    types: dict[str, str] = {}

    def collect(node: Any) -> None:
        if not isinstance(node, dict):
            return
        node_id = node.get("id")
        if isinstance(node_id, str):
            ids[node_id] = f"{scene_path}.sceneTree"
            if isinstance(node.get("type"), str):
                types[node_id] = node["type"]
        for child in node.get("children", []) or []:
            collect(child)

    collect(scene.get("sceneTree"))
    duration = scene.get("durationInFrames")
    for index, motion in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(motion, dict):
            report.error(item_path, "动效必须是对象")
            continue
        _reject_unknown(motion, {"target", "recipe", "startFrame", "durationFrames"}, item_path, report)
        target, recipe = motion.get("target"), motion.get("recipe")
        if target not in ids:
            report.error(f"{item_path}.target", f"动效目标 {target!r} 不存在")
        if recipe not in _MOTION_RECIPES:
            report.error(f"{item_path}.recipe", f"未知动效配方 {recipe!r}")
        elif target in ids:
            entry = catalog.primitive(types.get(target, ""))
            if entry is not None and recipe not in entry.motions:
                report.error(
                    f"{item_path}.recipe",
                    f"原语 {types.get(target)} 不支持动效 {recipe!r}（允许：{'、'.join(sorted(entry.motions))}）",
                )
        start = motion.get("startFrame", 0); length = motion.get("durationFrames", 1)
        if not isinstance(start, int) or isinstance(start, bool) or start < 0:
            report.error(f"{item_path}.startFrame", "startFrame 必须是非负整数")
        if not isinstance(length, int) or isinstance(length, bool) or length <= 0:
            report.error(f"{item_path}.durationFrames", "durationFrames 必须是正整数")
        if isinstance(start, int) and isinstance(length, int) and isinstance(duration, int) and start + length > duration:
            report.error(item_path, "动效时间范围超出场景")


def _scene_node_types(root: Any) -> dict[str, str]:
    """场景树里「节点 id → 原语类型」的索引；非 dict 根返回空表。"""
    types: dict[str, str] = {}

    def walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        node_id, node_type = node.get("id"), node.get("type")
        if isinstance(node_id, str) and isinstance(node_type, str):
            types.setdefault(node_id, node_type)
        for child in node.get("children", []) or []:
            walk(child)

    walk(root)
    return types


def _validate_beats(
    scene: dict[str, Any],
    path: str,
    report: Report,
    *,
    node_types: dict[str, str] | None,
    strict: bool,
) -> None:
    """校验分段口播与语义节拍。

    结构问题（互斥字段、重复 id、未知动作、空 meaning、悬空引用、无效目标、
    不连续引用）在**所有**校验模式下都是错误：它们让时间轴无法解析，
    画面与字幕必然对不上。质量规则（非文字幕至少两个 beat 且包含状态/
    关系动作）只在严格校验报错，普通校验给兼容提醒——旧字符串口播的
    预览与渲染必须继续可用。

    ``node_types`` 为 None 表示这一幕是代码场景：节点由作品模块在运行期
    用探针 id 声明，静态核验不了，因此只校验目标的标识符形状。
    """
    if "resolvedBeats" in scene:
        report.error(f"{path}.resolvedBeats", "resolvedBeats 是媒体准备派生的字段，源分镜不能声明")
    has_segments = "narrationSegments" in scene
    has_beats = "beats" in scene
    if has_segments and "narration" in scene:
        report.error(
            f"{path}.narrationSegments",
            "narration 与 narrationSegments 互斥：每幕二选一，分段口播的完整文本由各段按顺序拼接",
        )
    narration = scene.get("narration")
    spoken = bool(isinstance(narration, str) and narration.strip())
    if not has_segments and not has_beats:
        _require_beats_for_new_work(scene, path, report, spoken=spoken, strict=strict)
        return

    beats_value = scene.get("beats")
    if not isinstance(beats_value, list) or not beats_value:
        report.error(f"{path}.beats", "beats 必须是非空数组：分段口播必须绑定语义节拍")
        return
    index_by_id: dict[str, int] = {}
    for index, beat in enumerate(beats_value):
        item_path = f"{path}.beats[{index}]"
        if not isinstance(beat, dict):
            report.error(item_path, "beat 必须是对象")
            continue
        _reject_unknown(beat, {"id", "action", "targets", "meaning", "before", "after", "relation"}, item_path, report)
        beat_id = beat.get("id")
        if not isinstance(beat_id, str) or not _SCENE_ID_RE.match(beat_id):
            report.error(f"{item_path}.id", "beat id 必须是非空安全标识符")
        elif beat_id in index_by_id:
            report.error(f"{item_path}.id", f"beat id {beat_id} 与 beats[{index_by_id[beat_id]}] 重复")
        else:
            index_by_id[beat_id] = index
        action = beat.get("action")
        if action not in beat_mod.ACTIONS:
            report.error(
                f"{item_path}.action",
                f"未知语义动作 {action!r}（受控动作：{'、'.join(beat_mod.ACTIONS)}）",
            )
        _validate_beat_targets(beat.get("targets"), f"{item_path}.targets", report, action, node_types)
        meaning = beat.get("meaning")
        if not isinstance(meaning, str) or not meaning.strip():
            report.error(f"{item_path}.meaning", "meaning 必须是非空字符串：写清这一步让观众多看懂什么")
        for state_key in ("before", "after", "relation"):
            if state_key in beat and (not isinstance(beat[state_key], str) or not beat[state_key].strip()):
                report.error(f"{item_path}.{state_key}", "必须是非空字符串")

    segments = scene.get("narrationSegments")
    if not isinstance(segments, list) or not segments:
        report.error(f"{path}.narrationSegments", "beats 必须由分段口播驱动：narrationSegments 必须是非空数组")
        return
    duration = scene.get("durationInFrames")
    if isinstance(duration, int) and not isinstance(duration, bool) and len(segments) > duration:
        report.error(
            f"{path}.narrationSegments",
            f"场景只有 {duration} 帧，装不下 {len(segments)} 段口播：每段至少需要 1 帧",
        )
    segment_ids: dict[str, int] = {}
    referenced: list[str] = []
    for index, segment in enumerate(segments):
        item_path = f"{path}.narrationSegments[{index}]"
        if not isinstance(segment, dict):
            report.error(item_path, "口播段必须是对象")
            continue
        _reject_unknown(segment, {"id", "text", "beatId"}, item_path, report)
        segment_id = segment.get("id")
        if not isinstance(segment_id, str) or not _SCENE_ID_RE.match(segment_id):
            report.error(f"{item_path}.id", "口播段 id 必须是非空安全标识符")
        elif segment_id in segment_ids:
            report.error(
                f"{item_path}.id",
                f"口播段 id {segment_id} 与 narrationSegments[{segment_ids[segment_id]}] 重复",
            )
        else:
            segment_ids[segment_id] = index
        text = segment.get("text")
        if not isinstance(text, str) or not text.strip():
            report.error(f"{item_path}.text", "口播段文本不能为空")
        beat_id = segment.get("beatId")
        if not isinstance(beat_id, str) or beat_id not in index_by_id:
            report.error(f"{item_path}.beatId", f"口播段引用了不存在的 beat {beat_id!r}（悬空引用）")
        else:
            referenced.append(beat_id)
    for beat_id, index in sorted(index_by_id.items(), key=lambda item: item[1]):
        if beat_id not in referenced:
            report.error(
                f"{path}.beats[{index}]",
                f"beat {beat_id} 没有被任何口播段引用：没有可解析的时间，画面不知道该在哪一帧动",
            )
    runs = [
        beat_id
        for position, beat_id in enumerate(referenced)
        if position == 0 or referenced[position - 1] != beat_id
    ]
    for beat_id in sorted({item for item in runs if runs.count(item) > 1}):
        report.error(
            f"{path}.narrationSegments",
            f"beat {beat_id} 的口播段不连续：同一 beat 的引用必须相邻，否则时间轴会倒退或重叠",
        )
    _check_beat_rules(scene, path, report, beats_value, strict=strict)


def _validate_beat_targets(
    targets: Any,
    path: str,
    report: Report,
    action: Any,
    node_types: dict[str, str] | None,
) -> None:
    """beat 目标必须是本幕可定位的节点，且目标原语支持该语义动作。"""
    if not isinstance(targets, list) or not targets:
        report.error(path, "beat 至少要有一个目标节点")
        return
    for position, target in enumerate(targets):
        item_path = f"{path}[{position}]"
        if not isinstance(target, str) or not _SCENE_ID_RE.match(target):
            report.error(item_path, "目标必须是非空安全标识符")
            continue
        if node_types is None:
            continue  # 代码场景：节点是运行期探针 id，静态核验不了
        primitive_type = node_types.get(target)
        if primitive_type is None:
            report.error(item_path, f"beat 目标 {target} 不存在")
            continue
        entry = catalog.primitive(primitive_type)
        if action in beat_mod.ACTIONS and entry is not None and action not in entry.actions:
            allowed = "、".join(sorted(entry.actions)) or "无"
            report.error(
                item_path,
                f"原语 {primitive_type} 不支持语义动作 {action!r}（允许：{allowed}）",
            )


def _require_beats_for_new_work(
    scene: dict[str, Any], path: str, report: Report, *, spoken: bool, strict: bool
) -> None:
    """没有节拍的幕：非文字幕带口播时必须改用分段口播 + beats。

    纯文字幕（``typography``）与静音场景豁免——它们本来就不靠画面变化
    解释推理。旧字符串口播在普通校验下只收到兼容提醒，预览与渲染照常。
    """
    if not spoken or vn.analyze_scene(scene)["isTextScene"]:
        return
    message = (
        f"非文字幕带口播却没有语义节拍：请改用 narrationSegments 绑定至少 "
        f"{beat_mod.MIN_BEATS_PER_SCENE} 个 beat，并让其中至少一个改变对象状态或关系"
        f"（{'、'.join(sorted(beat_mod.CHANGE_ACTIONS))}）；纯文字幕与静音场景可以不使用该结构"
    )
    if strict:
        report.error(f"{path}.beats", message)
    else:
        report.warn(
            f"{path}.beats",
            message + "（旧版字符串口播兼容模式：可预览可渲染，--strict 校验与新的交付闭环会拒绝）",
        )


def _check_beat_rules(
    scene: dict[str, Any], path: str, report: Report, beats_value: list[Any], *, strict: bool
) -> None:
    """新作品的节拍质量规则：至少两个 beat，且至少一个改变状态或关系。

    只有「非文字幕 + 有口播」的场景受约束；纯文字幕与静音场景豁免。
    普通校验给提醒而不是错误，是为了让旧字符串口播继续可预览可渲染。
    """
    if vn.analyze_scene(scene)["isTextScene"]:
        return
    actions = [beat.get("action") for beat in beats_value if isinstance(beat, dict)]
    problems: list[str] = []
    if len(beats_value) < beat_mod.MIN_BEATS_PER_SCENE:
        problems.append(f"至少需要 {beat_mod.MIN_BEATS_PER_SCENE} 个 beat，当前 {len(beats_value)} 个")
    if not any(action in beat_mod.CHANGE_ACTIONS for action in actions):
        shown = "、".join(sorted({str(action) for action in actions})) or "无"
        problems.append(
            f"至少一个 beat 要改变对象状态或关系（当前动作：{shown}）；"
            "只有 establish/highlight 的画面是依次出现的卡片，不是一次推理"
        )
    if not problems:
        return
    message = "；".join(problems)
    if strict:
        report.error(f"{path}.beats", message)
    else:
        report.warn(
            f"{path}.beats",
            message + "（旧版字符串口播兼容模式：可预览可渲染，--strict 校验与新的交付闭环会拒绝）",
        )


def _warn_on_scene_copy(scene: dict[str, Any], path: str, report: Report) -> None:
    """场景级文案检查：单行上限、emphasis 命中与示意数值提醒。

    v2 的 data 是自由字段，因此检查遍历整个 data：可见文案写在哪个键里，
    规则都一样。硬换行是语义换行，所以逐行判断而不是判断整段长度。
    """
    data_field = scene.get("data")
    if not isinstance(data_field, dict):
        return
    _warn_on_long_text(data_field, f"{path}.data", report)
    if "emphasis" in data_field:
        _validate_emphasis(data_field["emphasis"], f"{path}.data.emphasis", report)
        _warn_on_unmatched_emphasis(data_field, f"{path}.data.emphasis", report)
    _warn_on_unsourced_numbers(scene, path, report)


def _warn_on_long_text(data_field: dict[str, Any], path: str, report: Report) -> None:
    """对 data 里的每个字符串值做单行字数检查（含嵌套对象与数组）。"""
    def walk(value: Any, item_path: str) -> None:
        if isinstance(value, str):
            _warn_on_long_line(value, item_path, report)
        elif isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{item_path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{item_path}[{index}]")

    for key, value in data_field.items():
        walk(value, f"{path}.{key}")


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


def _validate_emphasis(value: Any, path: str, report: Report) -> None:
    """emphasis 是要高亮的短语列表，画面据此在文本中标记重点。"""
    if not isinstance(value, list) or not value:
        report.error(path, "emphasis 必须是非空数组")
        return
    for i, phrase in enumerate(value):
        if not isinstance(phrase, str) or not phrase.strip():
            report.error(f"{path}[{i}]", "emphasis 的每一项必须是非空字符串")


def _warn_on_unmatched_emphasis(data_field: dict[str, Any], path: str, report: Report) -> None:
    """强调短语必须能在该场景的可见文本里原样命中，否则高亮会静默失效。"""
    phrases = data_field.get("emphasis")
    if not isinstance(phrases, list):
        return
    haystack = _visible_text(data_field)
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


def _visible_text(data_field: dict[str, Any]) -> str:
    """把分镜数据里所有字符串值拼起来（含嵌套对象与数组）。"""
    parts: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for value in data_field.values():
        walk(value)
    return "".join(parts)


def _warn_on_unsourced_numbers(scene: dict[str, Any], path: str, report: Report) -> None:
    """示意数值提醒：数字/图表原语没有声明 schematic 且文案无来源字样时提醒。

    「这个数值有没有来源」是内容判断，校验器做不了；这里只保证无来源数值
    不会无标记地混进画面——要么声明节点 schematic: true（画面自动出现
    「示意」标），要么在文案里写明来源（出处 / 来源字样）。
    """
    tree = scene.get("sceneTree")
    marked = False
    has_numbers = False

    def walk(node: Any) -> None:
        nonlocal marked, has_numbers
        if not isinstance(node, dict):
            return
        if node.get("type") in {"number", "chart"}:
            has_numbers = True
            if node.get("schematic") is True:
                marked = True
        for child in node.get("children", []) or []:
            walk(child)

    walk(tree)
    if not has_numbers or marked:
        return
    data_field = scene.get("data") if isinstance(scene.get("data"), dict) else {}
    visible = _visible_text(data_field)
    if "示意" not in visible and "来源" not in visible and "出处" not in visible:
        report.warn(
            f"{path}.sceneTree",
            "数字/图表数值没有标记来源：确认每个数值都有出处，并在文案里写明来源；"
            "确属示意数据时请把节点声明为 schematic: true，画面会自动出现「示意」标",
        )


def _reject_unknown(value: dict[str, Any], allowed: set[str], path: str, report: Report) -> None:
    for key in sorted(set(value) - allowed):
        report.error(f"{path}.{key}" if path else key, "声明式路径不支持此字段")


def _safe_fps(data: dict[str, Any]) -> int:
    """取出可安全参与算术的 fps，非法时回退 30。

    校验器的职责是「报告问题」而不是「自己抛异常」，因此所有用于计算的
    字段都要先做类型收敛。
    """
    fps = data.get("fps")
    if isinstance(fps, int) and not isinstance(fps, bool) and fps > 0:
        return fps
    return 30


def _validate_framerate(data: dict[str, Any], report: Report) -> None:
    fps = data.get("fps")
    if not isinstance(fps, int) or isinstance(fps, bool) or not 1 <= fps <= 120:
        report.error("fps", "fps 必须是 1..120 之间的整数")
        return
    if fps not in (24, 25, 30, 60):
        report.warn("fps", f"fps={fps} 不是常见值（24/25/30/60），请确认渲染目标")


def _validate_dimensions(data: dict[str, Any], report: Report) -> None:
    for key, default in (("width", 1080), ("height", 1920)):
        value = data.get(key, default)
        if not isinstance(value, int) or isinstance(value, bool):
            report.error(key, f"{key} 必须是整数像素")
        elif value <= 0:
            report.error(key, f"{key}={value} 必须大于 0")


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
            f"仅 {duration} 帧（{duration / fps:.1f} 秒 @{fps}fps），入场动效会被压缩到看不清，建议并入相邻场景",
        )


@dataclass(frozen=True)
class Scene:
    """解析后的单个场景。start_frame 由前一场景的时长累加得到。"""

    id: str
    type: str
    duration_in_frames: int
    start_frame: int
    data: dict[str, Any]
    #: 完整口播文本：分段口播按段拼接，字符串口播原样保留；静音为 None。
    narration: str | None
    #: 源声明的分段口播与语义节拍；字符串口播的幕里为空。
    narration_segments: tuple[dict[str, Any], ...] = ()
    beats: tuple[dict[str, Any], ...] = ()
    #: 已解析到帧区间的 beat 时间轴：有效分镜携带 resolvedBeats 时来自媒体准备
    #: （estimated=False），否则按声明时长等比例估算（estimated=True）。
    beat_timeline: beat_mod.BeatTimeline = beat_mod.BeatTimeline()

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


def load(path: str | Path, strict: bool = False) -> tuple[Storyboard | None, Report]:
    """从 JSON 文件加载并校验分镜脚本。

    返回 (storyboard, report)：解析失败或存在 error 时 storyboard 为 None，
    便于调用方在报告与模型之间二选一使用。``strict`` 透传给
    :func:`validate`——只有交付闭环的校验入口（validate.py --strict）
    传 True；预览、渲染、体检与配音准备保持兼容模式。
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

    report = validate(data, strict=strict)
    if not report.ok:
        return None, report
    return _build(data, report), report


def _scene_timeline(item: dict[str, Any]) -> beat_mod.BeatTimeline:
    """一幕的 beat 时间轴。

    有效分镜（媒体清单派生）携带 ``resolvedBeats`` 时以它为准——那是 TTS
    词边界解析出来的真实时间；源分镜没有该字段，按声明时长等比例估算，
    并标记 ``estimated=True``，画面据此知道这是估算时间轴。
    """
    if "resolvedBeats" in item:
        return beat_mod.BeatTimeline.from_json(item["resolvedBeats"], estimated=False)
    if not item.get("narrationSegments"):
        return beat_mod.BeatTimeline()
    return beat_mod.resolve_silent(item)


def _build(data: dict[str, Any], report: Report) -> Storyboard:
    """把已通过校验的 dict 构造为 Storyboard。"""
    scenes: list[Scene] = []
    cursor = 0
    for index, item in enumerate(data.get("scenes", [])):
        duration = item["durationInFrames"]
        try:
            timeline = _scene_timeline(item)
        except A2VError:
            # 走到这里说明校验漏了一处（例如手工构造的 dict）：时间轴退化为
            # 空表，画面按静态分镜渲染，而不是让整个加载过程崩掉。
            timeline = beat_mod.BeatTimeline()
        narration = beat_mod.scene_narration(item)
        scenes.append(
            Scene(
                id=item["id"],
                type=item["type"],
                duration_in_frames=duration,
                start_frame=cursor,
                data=item.get("data", {}),
                narration=narration or None,
                narration_segments=tuple(
                    segment
                    for segment in (item.get("narrationSegments") or [])
                    if isinstance(segment, dict)
                ),
                beats=tuple(
                    beat for beat in (item.get("beats") or []) if isinstance(beat, dict)
                ),
                beat_timeline=timeline,
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
