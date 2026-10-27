"""v8 全画布代码场景分镜的唯一材料契约。

通用作品只接受本地 React `code` 场景：画幅、配色、构图与动效都由作品代码决定，
契约里不再有模板、主题与展示元素。旧分镜明确拒绝，不提供迁移工具。
"""
from __future__ import annotations

import json
from pathlib import Path
from m2v.core.errors import M2VError
from m2v.core.validate import fail, items, number, obj, text
from m2v.core import frames
from m2v.types.general.article_text import active_source, extract_body, count_characters

from m2v.core.video_config import general_fps
VERSION = 8
TEMPLATE = "code"
MAX_SCENES, MAX_SEGMENTS = 300, 30
TRANSITIONS = ("cut", "fade", "crossfade")


def topic_input(data: dict) -> bool:
    return data.get("version") == VERSION and data.get("input", {}).get("kind") == "topic"


def local_file(root: Path, ref, path: str) -> Path:
    text(ref, path)
    file = (root / ref).resolve()
    if Path(ref).is_absolute() or not file.is_relative_to(root.resolve()) or not file.is_file():
        fail(path, "必须引用作品目录内存在的本地文件")
    return file


def source_file(root: Path, project: dict) -> Path:
    ref = project["materials"].get("article")
    source = local_file(root, ref, "materials.article") if ref else active_source(root)
    if not source.is_file() or not count_characters(extract_body(source.read_text(encoding="utf-8-sig"))):
        fail("article", "缺少非空源文；请提供 article.md")
    return source


def validate(data: dict, root: Path, project: dict | None = None) -> dict:
    if not isinstance(data, dict) or data.get("version") != VERSION or data.get("schemaVersion") != data.get("version"):
        fail("version", "通用分镜只接受 v8；v7 及更早作品须重新编排，不自动迁移")
    obj(data, "storyboard", {"version", "schemaVersion", "fps", "width", "height", "title",
                             "input", "targetSeconds", "soundtrack", "scenes"})
    # 返回规范化副本，不修改作者材料；下游只读取已解析的实际帧率。
    data = {**data, "fps": general_fps(project or {}, data)}
    fps = data["fps"]
    max_frames, max_pad, max_hold = 600 * fps, 30 * fps, 6 * fps
    frames.normalize(data.get("width"), data.get("height"))
    text(data.get("title"), "title")
    from . import soundtrack
    entry = obj(data.get("input", {"kind": "article"}), "input", {"kind", "topic"})
    if entry.get("kind") not in {"article", "topic"}:
        fail("input.kind", "必须为 article/topic")
    if topic_input(data):
        text(entry.get("topic"), "input.topic")
    number(data.get("targetSeconds", 60), 1, 600, "targetSeconds")
    from m2v.engine import rhythm
    from .code_scenes import validate_entry
    from . import cinematic
    scenes = items(data.get("scenes"), "scenes", MAX_SCENES)
    all_ids: set[str] = set()
    all_shots: list[dict] = []
    shot_ids: set[str] = set()
    for index, scene in enumerate(scenes):
        path = f"scenes[{index}]"
        obj(scene, path, {"id", "template", "content", "narrationSegments", "keywords",
                          "durationFrames", "transition", "transitionFrames", "speech",
                          "leadInFrames", "tailFrames", "readingHoldFrames"})
        sid = text(scene.get("id"), f"{path}.id")
        if sid in all_ids:
            fail(path, f"重复 ID：{sid}")
        all_ids.add(sid)
        if scene.get("template") != TEMPLATE:
            fail(path, f"template 必须是 {TEMPLATE}：通用画面由作品代码决定，不再有受控模板")
        if scene.get("transition", "cut") not in TRANSITIONS or (index == 0 and scene.get("transition", "cut") != "cut"):
            fail(path, "转场仅支持 cut/fade/crossfade，首幕必须 cut")
        for name, high in (("leadInFrames", max_pad), ("tailFrames", max_pad),
                           ("readingHoldFrames", max_hold)):
            if name not in scene:
                continue
            value = scene[name]
            if type(value) is not int or not 0 <= value <= high:
                fail(f"{path}.{name}", f"必须为 0～{high} 的整数")
        if topic_input(data) or "keywords" in scene:
            words = items(scene.get("keywords"), path + ".keywords", MAX_SEGMENTS)
            for word in words:
                text(word, path + ".keywords")
        if "durationFrames" in scene and (type(scene["durationFrames"]) is not int
                                          or not 1 <= scene["durationFrames"] <= max_frames):
            fail(path + ".durationFrames", f"必须为 1～{max_frames} 整数")
        overlap = scene.get("transitionFrames", round(8 / 30 * fps))
        if type(overlap) is not int or not 1 <= overlap <= 60 * fps:
            fail(path + ".transitionFrames", f"必须为 1～{60 * fps} 整数")
        if "speech" in scene:
            rhythm.configure(scene["speech"])
        parts = scene.get("narrationSegments")
        if not isinstance(parts, list) or len(parts) > MAX_SEGMENTS:
            fail(path + ".narrationSegments", f"必须包含 0～{MAX_SEGMENTS} 项")
        for part_index, part in enumerate(parts):
            obj(part, path + ".narrationSegments", {"id", "text", "claims", "holdFrames"})
            pid = text(part.get("id"), path + ".narrationSegments.id")
            text(part.get("text"), path + ".narrationSegments.text")
            if not count_characters(part["text"]):
                fail(path, "旁白不能仅包含标点或空白")
            cinematic.validate_claims(part, path + ".narrationSegments")
            if pid in all_ids:
                fail(path, f"重复 ID：{pid}")
            all_ids.add(pid)
            if "holdFrames" in part:
                hold = part["holdFrames"]
                if type(hold) is not int or not 0 <= hold <= max_pad:
                    fail(f"{path}.narrationSegments[{part_index}].holdFrames",
                         f"必须为 0～{max_pad} 的整数")
                if part_index == len(parts) - 1 and hold:
                    fail(f"{path}.narrationSegments[{part_index}].holdFrames",
                         "最后一段不能声明段间留白；收尾请使用 tailFrames")
        content = obj(scene.get("content"), path + ".content", {"title", "entry", "props"})
        if "title" in content:
            text(content.get("title"), path + ".content.title")
        props = content.get("props", {})
        validate_entry(root, content.get("entry"), props)
        shots = cinematic.validate_shots(props, path + ".content.props", fps=fps)
        ordered = sorted(shots, key=lambda item: item["startFrame"])
        for previous, current in zip(ordered, ordered[1:]):
            if previous["endFrame"] > current["startFrame"]:
                fail(path + ".content.props.shots",
                     f"镜头时间窗重叠：{previous['id']} 结束于 {previous['endFrame']}，"
                     f"{current['id']} 开始于 {current['startFrame']}")
        if "look" in props:
            cinematic.validate_look(props["look"], path + ".content.props.look")
        for shot in shots:
            if shot["id"] in shot_ids:
                fail(path + ".content.props.shots", f"重复镜头 ID：{shot['id']}")
            shot_ids.add(shot["id"])
            all_shots.append(shot)
    soundtrack.validate(data, root)
    return data


def load(root: Path, project: dict) -> dict:
    file = local_file(root, project["materials"].get("storyboard"), "materials.storyboard")
    try:
        data = json.loads(file.read_text(encoding="utf-8-sig"))
    except (ValueError, OSError) as exc:
        raise M2VError(f"无法读取讲解分镜：{exc}") from exc
    return validate(data, root, project)
