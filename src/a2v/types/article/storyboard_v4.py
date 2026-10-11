"""V4 单场景分镜的纯结构契约。运行时切换由全局迁移任务完成。"""
from __future__ import annotations

import re
from typing import Any

import a2v.core.catalog as catalog
from a2v.types.article.article_text import count_characters
from a2v.types.article.storyboard import Report, _validate_node_content, _validate_node_props, _validate_visual_intent

_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_ROOT = {"version", "schemaVersion", "directingVersion", "fps", "width", "height", "title",
         "visualDirection", "directingBrief", "visual", "soundtrack", "world", "stages"}
_WORLD = {"id", "claim", "metaphor", "objects", "renderer", "data", "sceneTree", "stateTracks", "motions", "camera"}
_STAGE = {"id", "durationInFrames", "data", "visualIntent", "narrationSegments", "beats"}
_PHASES = {"establish", "change", "result", "settle"}


def _fields(value: Any, allowed: set[str], path: str, report: Report) -> None:
    if isinstance(value, dict):
        for key in value.keys() - allowed:
            report.error(f"{path}.{key}" if path else key, "未知字段")


def _id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ID.fullmatch(value))


def _one(value: Any, allowed: set[str]) -> bool:
    return isinstance(value, str) and value in allowed


def _bounded_int(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _sound_asset(item: dict, path: str, allowed: set[str], report: Report) -> None:
    """声音素材的路径与增益规则与 v3 契约一致：本地相对路径，增益 −60–0 dB。"""
    import a2v.engine.sound as sound

    _fields(item, allowed, path, report)
    if not sound.local_ref(item.get("sourceRef")):
        report.error(path + ".sourceRef", "必须是分镜目录内本地相对路径")
    gain = item.get("gainDb")
    if "gainDb" in item and (type(gain) not in (int, float) or isinstance(gain, bool)
                             or not -60 <= gain <= 0):
        report.error(path + ".gainDb", "增益必须为 −60 至 0 dB")


def _binding(value: Any, path: str, report: Report, stages: set[str], beats: set[str]) -> None:
    if not isinstance(value, dict):
        report.error(path, "binding 必须是对象")
    elif set(value) == {"beatId"}:
        if value["beatId"] not in beats:
            report.error(path + ".beatId", "引用未知全局 beat")
    elif set(value) == {"stageId", "phase"}:
        if value["stageId"] not in stages:
            report.error(path + ".stageId", "引用未知 stage")
        if not _one(value["phase"], _PHASES):
            report.error(path + ".phase", "phase 必须是 establish/change/result/settle")
    else:
        report.error(path, "必须是 {beatId} 或 {stageId, phase} 绑定")


_TREE_FIELDS = {"id", "type", "children", "contentRef", "role", "align", "gap", "direction", "ratio",
                "columns", "shape", "state", "icon", "chart", "sourceRef", "schematic"}


def _walk_tree(node: Any, path: str, ids: set[str], nodes: dict[str, dict[str, Any]], count: list[int],
               data: dict[str, Any], report: Report, depth: int = 1) -> None:
    if not isinstance(node, dict):
        report.error(path, "sceneTree 节点必须是对象")
        return
    node_id = node.get("id")
    if not _id(node_id):
        report.error(path + ".id", "节点 id 必须是安全标识符")
    elif node_id in ids:
        report.error(path + ".id", f"全局节点 id 重复：{node_id}")
    else:
        ids.add(node_id)
    count[0] += 1
    if depth > 8:
        report.error(path, "场景树深度不能超过 8")
    _fields(node, _TREE_FIELDS, path, report)
    primitive_type = node.get("type")
    entry = catalog.primitive(primitive_type) if isinstance(primitive_type, str) else None
    if entry is None:
        report.error(path + ".type", f"未知视觉原语 {primitive_type!r}")
    else:
        _validate_node_props(node, entry, path, report)
        _validate_node_content(primitive_type, node, path, data, report)
    if isinstance(node_id, str) and node_id not in nodes:
        nodes[node_id] = node
    children = node.get("children", [])
    if not isinstance(children, list):
        report.error(path + ".children", "children 必须是数组")
        return
    if entry is not None and not entry.children[0] <= len(children) <= entry.children[1]:
        report.error(path + ".children", f"原语 {entry.type} 允许 {entry.children[0]}～{entry.children[1]} 个子节点")
    for index, child in enumerate(children):
        _walk_tree(child, f"{path}.children[{index}]", ids, nodes, count, data, report, depth + 1)


def _data_ref(data: dict[str, Any], reference: Any) -> tuple[bool, Any]:
    if not isinstance(reference, str) or not reference:
        return False, None
    value: Any = data
    for part in reference.split("."):
        if not isinstance(value, dict) or part not in value:
            return False, None
        value = value[part]
    return True, value


def _numeric_shape(value: Any) -> Any:
    """Return a shape with numeric leaves, or None for non-numeric data."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"
    if isinstance(value, list):
        children = [_numeric_shape(item) for item in value]
        return children if all(item is not None for item in children) else None
    if isinstance(value, dict):
        children = {key: _numeric_shape(item) for key, item in value.items()}
        return children if all(item is not None for item in children.values()) else None
    return None


def _track_base_value(prop: Any, target: Any, data: Any, renderer_kind: Any) -> tuple[bool, Any]:
    if prop == "visible":
        return True, target.get("visible", True) if isinstance(target, dict) else True
    if not isinstance(target, dict):
        return False, None
    if prop in {"state", "contentRef", "sourceRef"}:
        return (prop in target, target.get(prop))
    if prop == "value":
        if renderer_kind == "tree":
            exists, value = _data_ref(data if isinstance(data, dict) else {}, target.get("contentRef"))
            return exists, value
        return ("value" in target, target.get("value"))
    return False, None


def _validate_track_value(prop: Any, before: Any, after: Any, interpolation: Any,
                          path: str, report: Report) -> None:
    if prop == "visible":
        if not isinstance(before, bool) or not isinstance(after, bool):
            report.error(path + ".to", "visible 轨道只能使用布尔值")
        if interpolation != "step-end":
            report.error(path + ".interpolation", "visible 是离散属性，只允许 step-end")
        return
    if prop == "state":
        states = {"rest", "focus", "muted", "done"}
        if not _one(before, states) or not _one(after, states):
            report.error(path + ".to", "state 轨道必须使用受控 state 值")
        if interpolation != "step-end":
            report.error(path + ".interpolation", "state 是离散属性，只允许 step-end")
        return
    if prop in {"contentRef", "sourceRef"}:
        if not isinstance(before, str) or not isinstance(after, str) or not after.strip():
            report.error(path + ".to", f"{prop} 轨道的目标必须是非空引用")
        if interpolation != "step-end":
            report.error(path + ".interpolation", f"{prop} 是离散属性，只允许 step-end")
        return
    if prop == "value":
        before_shape, after_shape = _numeric_shape(before), _numeric_shape(after)
        if before_shape is None or after_shape is None:
            report.error(path + ".to", "value 轨道必须在既有数值或数值结构上变化")
            return
        if before_shape != after_shape:
            if interpolation != "step-end":
                report.error(path + ".interpolation", "数值结构改变时只允许 step-end")
        elif interpolation == "step-end":
            return
        elif interpolation not in {"linear", "ease-in", "ease-out", "ease-in-out"}:
            report.error(path + ".interpolation", "数值属性需要 linear 或受控 ease 插值")


def validate(data: Any) -> Report:
    """校验 v4 的全片根、world/stages 边界与全局唯一标识。"""
    report = Report()
    if not isinstance(data, dict):
        report.error("$", "脚本根节点必须是 JSON 对象")
        return report
    if data.get("version") != 4 or data.get("schemaVersion") != 4:
        # 旧分镜只回一条可执行的诊断：入口不迁移、不补齐，也不继续按 v4 逐字段报错。
        report.error("version", "不支持 v4 之前分镜；请按分镜 v4 契约重新编排")
        return report
    if data.get("directingVersion") != 2:
        report.error("directingVersion", "v4 必须声明 directingVersion: 2")
    _fields(data, _ROOT, "", report)
    fps = data.get("fps")
    if type(fps) is not int or not 1 <= fps <= 120:
        report.error("fps", "必须是 1～120 的整数")
    for key in ("width", "height"):
        if type(data.get(key)) is not int or data[key] <= 0:
            report.error(key, "必须是正整数")
    visual = data.get("visual")
    if not isinstance(visual, dict) or set(visual) - {"theme", "preset"} or not _one(visual.get("theme"), {"dark", "light"}) or visual.get("preset") != "keynote":
        report.error("visual", '必须声明 theme: dark/light 与 preset: "keynote"')
    direction = data.get("visualDirection")
    if not isinstance(direction, dict):
        report.error("visualDirection", "必须是对象")
    else:
        _fields(direction, {"motif", "compositionBias", "density", "rhythm", "avoid"}, "visualDirection", report)
        for key in ("motif",):
            if not isinstance(direction.get(key), str) or not direction[key].strip():
                report.error(f"visualDirection.{key}", "必须是非空字符串")
        enums = {"compositionBias": {"centered", "asymmetric", "mixed"}, "density": {"sparse", "balanced", "dense"},
                 "rhythm": {"restrained", "steady", "dynamic"}}
        for key, allowed in enums.items():
            if not _one(direction.get(key), allowed):
                report.error(f"visualDirection.{key}", "值不在受控枚举中")
        if not isinstance(direction.get("avoid"), list) or not all(isinstance(item, str) and item.strip() for item in direction.get("avoid", [])):
            report.error("visualDirection.avoid", "必须是字符串数组")
    brief = data.get("directingBrief")
    if not isinstance(brief, dict):
        report.error("directingBrief", "必须提供导演简报")
    else:
        _fields(brief, {"thesis", "audienceShift", "emotionalArc", "visualMotif", "stylePack", "avoid"}, "directingBrief", report)
        if not all(isinstance(brief.get(key), str) and brief[key].strip() for key in ("thesis", "audienceShift", "visualMotif")):
            report.error("directingBrief", "thesis、audienceShift 与 visualMotif 必填")
        if not isinstance(brief.get("emotionalArc"), list) or len(brief["emotionalArc"]) < 2 or not all(isinstance(item, str) and item.strip() for item in brief.get("emotionalArc", [])):
            report.error("directingBrief.emotionalArc", "必须是至少两个情绪阶段")
        if not _one(brief.get("stylePack"), {"editorial", "cinematic", "technical", "poetic"}):
            report.error("directingBrief.stylePack", "stylePack 值无效")
        if not isinstance(brief.get("avoid"), list) or not all(isinstance(item, str) and item.strip() for item in brief.get("avoid", [])):
            report.error("directingBrief.avoid", "必须是字符串数组")

    world = data.get("world")
    if not isinstance(world, dict):
        report.error("world", "必须声明唯一全片 world")
        world = {}
    _fields(world, _WORLD, "world", report)
    for key in ("id",):
        if not _id(world.get(key)):
            report.error(f"world.{key}", "必须是安全标识符")
    for key in ("claim", "metaphor"):
        if not isinstance(world.get(key), str) or not world[key].strip():
            report.error(f"world.{key}", "必须是非空字符串")
    if not isinstance(world.get("data"), dict):
        report.error("world.data", "必须是对象")

    renderer = world.get("renderer")
    if not isinstance(renderer, dict) or not _one(renderer.get("kind"), {"tree", "code"}):
        report.error("world.renderer", "必须选择唯一 tree 或 code renderer")
        renderer_kind = None
    else:
        renderer_kind = renderer["kind"]
        _fields(renderer, {"kind", "module"} if renderer_kind == "code" else {"kind"}, "world.renderer", report)
        if renderer_kind == "code" and (not isinstance(renderer.get("module"), str)
                or not re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", renderer["module"])):
            report.error("world.renderer.module", "code renderer 必须声明安全模块标识")
    objects = world.get("objects")
    object_ids: set[str] = set()
    primary_count = 0
    if not isinstance(objects, list) or not objects:
        report.error("world.objects", "必须声明持续对象")
    else:
        for index, item in enumerate(objects):
            path = f"world.objects[{index}]"
            if not isinstance(item, dict):
                report.error(path, "对象必须是对象值")
                continue
            _fields(item, {"id", "role", "description"}, path, report)
            object_id = item.get("id")
            if not _id(object_id):
                report.error(path + ".id", "必须是安全标识符")
            elif object_id in object_ids:
                report.error(path + ".id", f"全局 object id 重复：{object_id}")
            else:
                object_ids.add(object_id)
            if not _one(item.get("role"), {"primary", "supporting", "annotation"}):
                report.error(path + ".role", "角色必须是 primary/supporting/annotation")
            primary_count += item.get("role") == "primary"
            if not isinstance(item.get("description"), str) or not item["description"].strip():
                report.error(path + ".description", "必须说明持续对象")
    if objects and not primary_count:
        report.error("world.objects", "至少需要一个 primary 对象")

    node_ids: set[str] = set()
    tree_nodes: dict[str, dict[str, Any]] = {}
    if renderer_kind == "tree":
        if "sceneTree" not in world:
            report.error("world.sceneTree", "tree renderer 必须声明唯一全局 sceneTree")
        else:
            count = [0]
            world_data = world.get("data") if isinstance(world.get("data"), dict) else {}
            _walk_tree(world["sceneTree"], "world.sceneTree", node_ids, tree_nodes, count, world_data, report)
            if count[0] > 48:
                report.error("world.sceneTree", f"全片节点数 {count[0]} 超出上限 48")
    elif renderer_kind == "code" and "sceneTree" in world:
        report.error("world.sceneTree", "code renderer 不得同时声明场景树")
    if renderer_kind == "tree" and node_ids:
        missing_nodes = object_ids - node_ids
        if missing_nodes:
            report.error("world.objects", "对象缺少同 id 全局树节点：" + "、".join(sorted(missing_nodes)))

    stages_value = data.get("stages")
    stages: set[str] = set()
    beats: set[str] = set()
    beat_targets: dict[str, set[str]] = {}
    if not isinstance(stages_value, list) or not stages_value:
        report.error("stages", "必须声明非空叙事阶段数组")
        stages_value = []
    total_frames = 0
    narration_parts: list[str] = []
    for index, stage in enumerate(stages_value):
        path = f"stages[{index}]"
        if not isinstance(stage, dict):
            report.error(path, "stage 必须是对象")
            continue
        _fields(stage, _STAGE, path, report)
        stage_id = stage.get("id")
        if not _id(stage_id):
            report.error(path + ".id", "stage id 必须是安全标识符")
        elif stage_id in stages:
            report.error(path + ".id", f"全局 stage id 重复：{stage_id}")
        else:
            stages.add(stage_id)
        if type(stage.get("durationInFrames")) is not int or stage["durationInFrames"] <= 0:
            report.error(path + ".durationInFrames", "必须是正整数")
        else:
            total_frames += stage["durationInFrames"]
        if not isinstance(stage.get("data"), dict):
            report.error(path + ".data", "必须是对象")
        if "visualIntent" not in stage or not isinstance(stage.get("visualIntent"), dict):
            report.error(path + ".visualIntent", "每个 stage 必须声明 visualIntent")
        else:
            # 与 v3 同一套受控词汇：Python 校验通过的分镜不能在契约页被 zod 拒绝，
            # 否则预览、评审与渲染会在挂载前失败，且错误信息不指向分镜字段。
            _validate_visual_intent(stage["visualIntent"], path + ".visualIntent", report)
        if "narration" in stage:
            report.error(path + ".narration", "v4 使用 narrationSegments")
        segments = stage.get("narrationSegments", [])
        stage_beats = stage.get("beats", [])
        if not isinstance(segments, list) or not isinstance(stage_beats, list):
            report.error(path, "narrationSegments 与 beats 必须是数组")
            continue
        for segment in segments:
            if isinstance(segment, dict) and isinstance(segment.get("text"), str):
                narration_parts.append(segment["text"])
        local_beats: set[str] = set()
        for beat_index, beat in enumerate(stage_beats):
            beat_path = f"{path}.beats[{beat_index}]"
            if not isinstance(beat, dict):
                report.error(beat_path, "beat 必须是对象")
                continue
            beat_id = beat.get("id")
            if not _id(beat_id):
                report.error(beat_path + ".id", "beat id 必须是安全标识符")
            elif beat_id in beats:
                report.error(beat_path + ".id", f"全局 beat id 重复：{beat_id}")
            else:
                beats.add(beat_id)
                local_beats.add(beat_id)
                beat_targets[beat_id] = {target for target in beat.get("targets", []) if isinstance(target, str)} if isinstance(beat.get("targets"), list) else set()
            if not isinstance(beat.get("targets"), list) or not beat["targets"]:
                report.error(beat_path + ".targets", "beat 必须有目标对象")
            else:
                for target_index, target in enumerate(beat["targets"]):
                    if not isinstance(target, str) or target not in object_ids:
                        report.error(f"{beat_path}.targets[{target_index}]", f"未知全局对象：{target}")
            if not _one(beat.get("action"), {"establish", "connect", "transfer", "accumulate", "deplete", "transform", "compare", "highlight", "loop", "break", "restore"}):
                report.error(beat_path + ".action", "action 不在受控语义动作集合中")
        for segment_index, segment in enumerate(segments):
            segment_path = f"{path}.narrationSegments[{segment_index}]"
            if not isinstance(segment, dict):
                report.error(segment_path, "口播段必须是对象")
                continue
            _fields(segment, {"id", "text", "beatId", "speech"}, segment_path, report)
            if "speech" in segment:
                # 整段口播一次合成：逐段语速与停顿没有参与时间轴的计算，
                # 静默忽略会让作者以为参数生效，这里直接拒绝。
                report.error(segment_path + ".speech",
                             "v4 按整段口播统一语速合成，不再支持逐段 speech")
            if not _id(segment.get("id")):
                report.error(segment_path + ".id", "口播段 id 必须是安全标识符")
            if not isinstance(segment.get("text"), str) or not segment["text"].strip():
                report.error(segment_path + ".text", "口播段必须声明文本")
            beat_id = segment.get("beatId")
            if not isinstance(beat_id, str) or beat_id not in local_beats:
                report.error(segment_path + ".beatId", "口播段必须引用本 stage 中存在的 beat")

    if isinstance(fps, int) and not isinstance(fps, bool) and fps > 0:
        if total_frames < 35 * fps or total_frames > 45 * fps:
            report.error("stages", f"声明全片时长 {total_frames / fps:.2f} 秒，必须在 35～45 秒（含边界）")
    narration_count = count_characters("".join(narration_parts))
    if narration_count == 0:
        report.error("stages", "标准作品必须有完整口播，静音不能豁免篇幅要求")
    elif not 130 <= narration_count <= 170:
        report.error("stages", f"最终口播为 {narration_count} 字，必须在 130～170 字")

    camera = world.get("camera")
    if not isinstance(camera, dict):
        report.error("world.camera", "必须声明全片 camera")
    else:
        _fields(camera, {"shot", "composition", "depth", "focus", "segments"}, "world.camera", report)
        if not _one(camera.get("shot"), {"macro", "close", "medium", "wide"}):
            report.error("world.camera.shot", "shot 值无效")
        if not _one(camera.get("composition"), {"center", "left", "right", "split", "full"}):
            report.error("world.camera.composition", "composition 值无效")
        if not _one(camera.get("depth"), {"flat", "layered"}):
            report.error("world.camera.depth", "depth 值无效")
        if not isinstance(camera.get("focus"), str) or camera.get("focus") not in object_ids:
            report.error("world.camera.focus", "focus 必须引用已声明全局对象")
        if not isinstance(camera.get("segments"), list) or not camera["segments"]:
            report.error("world.camera.segments", "全片镜头段不能为空")
        else:
            for index, segment in enumerate(camera["segments"]):
                if not isinstance(segment, dict):
                    report.error(f"world.camera.segments[{index}]", "镜头段必须是对象")
                    continue
                _fields(segment, {"id", "kind", "binding", "focus", "direction", "intensity"}, f"world.camera.segments[{index}]", report)
                if not _id(segment.get("id")):
                    report.error(f"world.camera.segments[{index}].id", "镜头段 id 必须是安全标识符")
                if not _one(segment.get("kind"), {"hold", "push-in", "pull-out", "pan", "reframe", "settle"}):
                    report.error(f"world.camera.segments[{index}].kind", "镜头动作无效")
                if segment.get("focus") is not None and (not isinstance(segment.get("focus"), str) or segment.get("focus") not in object_ids):
                    report.error(f"world.camera.segments[{index}].focus", "必须引用已声明全局对象")
                if segment.get("kind") == "pan" and not _one(segment.get("direction"), {"left", "right", "up", "down"}):
                    report.error(f"world.camera.segments[{index}].direction", "pan 必须声明方向")
                _binding(segment.get("binding"), f"world.camera.segments[{index}].binding", report, stages, beats)

    tracks = world.get("stateTracks")
    if not isinstance(tracks, list):
        report.error("world.stateTracks", "必须是数组")
    else:
        track_ids: set[str] = set()
        track_bindings: set[tuple[Any, Any, Any]] = set()
        for index, track in enumerate(tracks):
            path = f"world.stateTracks[{index}]"
            if not isinstance(track, dict):
                report.error(path, "轨道必须是对象")
                continue
            _fields(track, {"id", "target", "property", "binding", "to", "interpolation"}, path, report)
            track_id = track.get("id")
            if not _id(track_id) or track_id in track_ids:
                report.error(path + ".id", "轨道 id 必须是唯一安全标识符")
            track_ids.add(track_id) if _id(track_id) else None
            if not isinstance(track.get("target"), str) or track.get("target") not in object_ids:
                report.error(path + ".target", "必须引用已声明全局对象")
            if not _one(track.get("property"), {"visible", "state", "value", "contentRef", "sourceRef"}):
                report.error(path + ".property", "属性不在受控集合中")
            if not _one(track.get("interpolation"), {"step-end", "linear", "ease-in", "ease-out", "ease-in-out"}):
                report.error(path + ".interpolation", "插值方式无效")
            _binding(track.get("binding"), path + ".binding", report, stages, beats)
            target_id, prop = track.get("target"), track.get("property")
            target_node = tree_nodes.get(target_id) if isinstance(target_id, str) else None
            target_type = target_node.get("type") if isinstance(target_node, dict) else None
            entry = catalog.primitive(target_type) if isinstance(target_type, str) else None
            if renderer_kind == "tree" and entry is not None:
                if prop != "visible" and prop not in entry.props:
                    report.error(path + ".property", f"原语 {entry.type} 不支持属性 {prop!r}")
            if renderer_kind == "code":
                code_objects = world.get("data", {}).get("objects", {}) if isinstance(world.get("data"), dict) else {}
                target_node = code_objects.get(target_id) if isinstance(code_objects, dict) else None
            base_found, base_value = _track_base_value(prop, target_node, world.get("data", {}), renderer_kind)
            to_value = track.get("to")
            if not base_found:
                report.error(path + ".target", f"对象 {target_id!r} 的属性 {prop!r} 缺少基础值")
            else:
                _validate_track_value(prop, base_value, to_value, track.get("interpolation"), path, report)
            binding = track.get("binding")
            if isinstance(binding, dict):
                bound_beat = binding.get("beatId")
                if isinstance(bound_beat, str) and isinstance(target_id, str) and bound_beat in beat_targets and target_id not in beat_targets[bound_beat]:
                    report.error(path + ".target", "轨道目标不在绑定 beat 的 targets 中")
                token = (binding.get("beatId") if "beatId" in binding else
                         f"{binding.get('stageId')}:{binding.get('phase')}")
                if isinstance(target_id, str) and isinstance(prop, str):
                    key = (target_id, prop, token)
                    if key in track_bindings:
                        report.error(path + ".binding", "同一对象属性存在重叠轨道绑定")
                    track_bindings.add(key)

    motions = world.get("motions")
    if not isinstance(motions, list):
        report.error("world.motions", "必须是数组")
    else:
        for index, motion in enumerate(motions):
            path = f"world.motions[{index}]"
            if not isinstance(motion, dict):
                report.error(path, "motion 必须是对象")
                continue
            _fields(motion, {"target", "targets", "recipe", "binding", "stagger"}, path, report)
            has_target, has_targets = isinstance(motion.get("target"), str), isinstance(motion.get("targets"), list)
            if has_target == has_targets:
                report.error(path, "target 与 targets 必须二选一")
            targets = [motion["target"]] if has_target else motion.get("targets", [])
            available_targets = node_ids if renderer_kind == "tree" else object_ids
            if not targets or any(not isinstance(target, str) or target not in available_targets for target in targets):
                report.error(path + ".target", "必须引用存在的全局节点")
            if not _one(motion.get("recipe"), {"reveal", "fade", "rise", "count", "draw"}):
                report.error(path + ".recipe", "动效配方无效")
            _binding(motion.get("binding"), path + ".binding", report, stages, beats)

    soundtrack = data.get("soundtrack")
    if soundtrack is not None:
        if not isinstance(soundtrack, dict):
            report.error("soundtrack", "必须是对象")
        else:
            _fields(soundtrack, {"music", "effects"}, "soundtrack", report)
            music = soundtrack.get("music")
            if music is not None:
                _sound_asset(music, "soundtrack.music",
                             {"sourceRef", "gainDb", "loop", "fadeInMs", "fadeOutMs"}, report)
                if "loop" in music and not isinstance(music["loop"], bool):
                    report.error("soundtrack.music.loop", "必须是布尔值")
                for key in ("fadeInMs", "fadeOutMs"):
                    if key in music and not _bounded_int(music[key], 0, 60000):
                        report.error("soundtrack.music." + key, "淡入淡出必须为 0–60000ms 整数")
            effects = soundtrack.get("effects", [])
            if not isinstance(effects, list):
                report.error("soundtrack.effects", "必须是数组")
            elif len(effects) > 128:
                report.error("soundtrack.effects", "音效最多 128 项")
            else:
                for index, effect in enumerate(effects):
                    path = f"soundtrack.effects[{index}]"
                    if not isinstance(effect, dict):
                        report.error(path, "效果声明必须是对象")
                        continue
                    _sound_asset(effect, path, {"sourceRef", "stageId", "beatId", "offsetMs", "gainDb"}, report)
                    if (not isinstance(effect.get("stageId"), str) or effect.get("stageId") not in stages
                            or not isinstance(effect.get("beatId"), str) or effect.get("beatId") not in beats):
                        report.error(path, "必须引用有效的全局 stage 与 beat")
                    if "offsetMs" in effect and not _bounded_int(effect["offsetMs"], -60000, 60000):
                        report.error(path + ".offsetMs", "偏移必须为 ±60000ms 内整数")
    return report
