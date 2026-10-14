"""v5 讲解分镜的唯一材料契约；与旧世界动画模型隔离。"""
from __future__ import annotations

import json
from pathlib import Path
from m2v.core.errors import M2VError
from m2v.types.article.article_text import active_source, extract_body, count_characters

FPS, WIDTH, HEIGHT = 30, 1080, 1920
MAX_FRAMES, READING_TAIL, FADE_FRAMES = 1800, 12, 8
TEMPLATES = {"point", "compare", "steps", "cause", "image"}


def fail(path: str, message: str) -> None:
    raise M2VError(f"{path}: {message}")


def obj(value, path: str, allowed: set[str]) -> dict:
    if not isinstance(value, dict):
        fail(path, "必须是对象")
    unknown = set(value) - allowed
    if unknown:
        fail(path, f"未知字段：{'、'.join(sorted(unknown))}")
    return value


def text(value, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(path, "必须是非空文本")
    return value


def items(value, path: str, maximum: int) -> list:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        fail(path, f"必须包含 1～{maximum} 项")
    return value


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


def elements(scene: dict) -> list[dict]:
    """各模板展示元素共用绑定契约，供准备和渲染使用。"""
    content = scene["content"]
    if scene["template"] == "point":
        return [content["summary"]]
    if scene["template"] == "compare":
        return [item for column in content["columns"] for item in column["items"]]
    if scene["template"] == "steps":
        return content["items"]
    if scene["template"] == "cause":
        return content["nodes"] + content["links"]
    return [content["caption"]]


def graph_levels(content: dict) -> dict[str, int]:
    nodes = content["nodes"]
    pending = {node["id"]: 0 for node in nodes}
    levels = dict(pending)
    edges = {key: [] for key in pending}
    for link in content["links"]:
        edges[link["from"]].append(link["to"])
        pending[link["to"]] += 1
    queue = [key for key, degree in pending.items() if degree == 0]
    for key in queue:
        for target in edges[key]:
            levels[target] = max(levels[target], levels[key] + 1)
            pending[target] -= 1
            if pending[target] == 0:
                queue.append(target)
    if len(queue) != len(nodes):
        fail("cause.links", "因果图不得包含循环")
    return levels


def validate(data: dict, root: Path) -> dict:
    if not isinstance(data, dict) or data.get("version") != 5 or data.get("schemaVersion") != 5:
        fail("version", "文章只接受 v5 讲解分镜；v4 及更早作品须重新编排，不自动迁移")
    obj(data, "storyboard", {"version", "schemaVersion", "fps", "width", "height", "title", "visual", "scenes"})
    for key, expected in (("fps", FPS), ("width", WIDTH), ("height", HEIGHT)):
        if type(data.get(key)) is not int or data[key] != expected:
            fail(key, f"必须为 {expected}")
    text(data.get("title"), "title")
    visual = obj(data.get("visual", {}), "visual", {"theme"})
    if visual.get("theme", "dark") not in {"dark", "light"}:
        fail("visual.theme", "只支持 dark/light")
    scenes = items(data.get("scenes"), "scenes", 30)
    all_ids: set[str] = set()
    for index, scene in enumerate(scenes):
        path = f"scenes[{index}]"
        obj(scene, path, {"id", "template", "content", "narrationSegments", "transition"})
        sid = text(scene.get("id"), f"{path}.id")
        if sid in all_ids:
            fail(path, f"重复 ID：{sid}")
        all_ids.add(sid)
        kind = scene.get("template")
        if kind not in TEMPLATES:
            fail(path, "template 必须是 point/compare/steps/cause/image")
        if scene.get("transition", "cut") not in {"cut", "fade"} or (index == 0 and scene.get("transition", "cut") != "cut"):
            fail(path, "转场仅支持 cut/fade，首幕必须 cut")
        parts = items(scene.get("narrationSegments"), f"{path}.narrationSegments", 30)
        part_ids = set()
        for part in parts:
            obj(part, path + ".narrationSegments", {"id", "text"})
            pid = text(part.get("id"), path + ".narrationSegments.id")
            text(part.get("text"), path + ".narrationSegments.text")
            if not count_characters(part["text"]):
                fail(path, "旁白不能仅包含标点或空白")
            if pid in all_ids:
                fail(path, f"重复 ID：{pid}")
            all_ids.add(pid)
            part_ids.add(pid)
        allowed = {"point": {"title", "summary"}, "compare": {"title", "columns"},
                   "steps": {"title", "items"}, "cause": {"title", "nodes", "links"},
                   "image": {"title", "src", "fit", "caption"}}[kind]
        content = obj(scene.get("content"), path + ".content", allowed)
        text(content.get("title"), path + ".content.title")
        if kind == "point":
            obj(content.get("summary"), path + ".summary", {"text", "segmentId", "keywords"})
        elif kind == "compare":
            columns = items(content.get("columns"), path + ".columns", 2)
            if len(columns) != 2:
                fail(path, "compare 必须恰好两列")
            for column in columns:
                obj(column, path + ".columns", {"title", "items"})
                text(column.get("title"), path + ".columns.title")
                items(column.get("items"), path + ".columns.items", 4)
        elif kind == "steps":
            items(content.get("items"), path + ".items", 6)
        elif kind == "cause":
            nodes = items(content.get("nodes"), path + ".nodes", 6)
            node_ids = [text(obj(n, path + ".nodes", {"id", "text", "segmentId", "keywords"}).get("id"), path + ".nodes.id") for n in nodes]
            if len(set(node_ids)) != len(node_ids):
                fail(path, "因果节点 ID 重复")
            links = items(content.get("links"), path + ".links", 8)
            pairs = set()
            for link in links:
                obj(link, path + ".links", {"from", "to", "text", "segmentId", "keywords"})
                if link.get("from") not in node_ids or link.get("to") not in node_ids:
                    fail(path, "因果连线引用未知节点")
                pair = (link["from"], link["to"])
                if pair in pairs:
                    fail(path, "因果连线重复")
                pairs.add(pair)
            graph_levels(content)
        elif kind == "image":
            image = local_file(root, content.get("src"), path + ".src")
            if image.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                fail(path, "图片仅支持 PNG/JPEG/WebP")
            if content.get("fit", "contain") not in {"contain", "cover"}:
                fail(path, "图片 fit 仅支持 contain/cover")
        for number, element in enumerate(elements(scene)):
            ep = f"{path}.elements[{number}]"
            extras = {"id"} if kind == "cause" and "id" in element else {"from", "to"} if kind == "cause" else set()
            obj(element, ep, {"text", "segmentId", "keywords"} | extras)
            label = text(element.get("text"), ep + ".text")
            if element.get("segmentId") not in part_ids:
                fail(ep, "segmentId 必须引用本幕旁白")
            keywords = element.get("keywords", [])
            if not isinstance(keywords, list) or any(not isinstance(word, str) or not word or word not in label for word in keywords):
                fail(ep, "keywords 必须为画面文字中存在的非空词语数组")
        if kind == "steps":
            order = [next(i for i, p in enumerate(parts) if p["id"] == item["segmentId"]) for item in content["items"]]
            if order != sorted(order) or len(set(order)) != len(order):
                fail(path, "步骤须按不同旁白分段的先后顺序绑定")
        if kind == "cause":
            order = {part["id"]: i for i, part in enumerate(parts)}
            node_order = {node["id"]: order[node["segmentId"]] for node in content["nodes"]}
            if any(order[link["segmentId"]] < max(node_order[link["from"]], node_order[link["to"]]) for link in content["links"]):
                fail(path, "因果连线的旁白绑定不能早于两端节点")
    return data


def load(root: Path, project: dict) -> dict:
    file = local_file(root, project["materials"].get("storyboard"), "materials.storyboard")
    try:
        data = json.loads(file.read_text(encoding="utf-8-sig"))
    except (ValueError, OSError) as exc:
        raise M2VError(f"无法读取讲解分镜：{exc}") from exc
    return validate(data, root)
