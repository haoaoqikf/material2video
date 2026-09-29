"""动画论证评审（A 系列）：动画到底有没有解释论点。

**为什么需要这一层。** C/K/M/V 系列量的是「画面是否成立」——溢出、对比度、
留白、文字幕预算。它们都能通过，而动画仍然只是一堆元素依次入场：观众看到
的是卡片出现，不是一次推理。A 系列把「动画是否解释论点」拆成八条可分别
裁决的闸门，其中七条从分镜与解析时间轴确定性量测，一条（A6）必须由人或
视觉模型裁决。

**八条闸门。**

* A1 节拍覆盖：每个口播段绑定到存在的 beat，每个 beat 至少被一段引用，
  且同一 beat 的引用连续（时间轴不倒退、不重叠）。
* A2 含义声明：每个 beat 的 ``meaning`` 非空，且不是把该 beat 的口播原文
  抄一遍——抄一遍等于没有声明它解释了什么。
* A3 状态或关系变化：非文字幕至少两条 beat，且至少一条动作真正改变对象
  状态或关系（``CHANGE_ACTIONS``）；全是 establish/highlight 就是「依次入场」。
* A4 字幕同步：有声时字幕 cue 边界与 beat 边界共用同一份时间轴
  （逐帧允许 ±1 帧的取整差）；cue 跨过口播段边界说明两者没有共用边界。
* A5 结尾停留：最后一条 beat 完成后至少留 :data:`STABLE_READING_FRAMES`
  帧稳定阅读时间，让观众读完结论。
* A6 装饰动画人工裁决：评分与依据来自 ``review.md``，缺失即「待评审」。
* A7 单一焦点：任一帧最多一个对象处于焦点（显式 ``state: 'focus'`` 或
  关系容器里被标为当前阶段），同时点亮多处等于没有焦点。
* A8 稳定结束：所有入场配方在结尾稳定段之前结束，画面不会在最后一帧还在动。

**适用范围。** A1–A5、A7、A8 只约束**声明了分段口播的幕**：
没有分段口播的静音场景不适用口播同步闸门；所有含口播场景必须使用 narrationSegments 与 beats。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Sequence

from . import beats as beat_mod
from . import visual_narrative as vn
from .errors import A2VError

#: 规则版本：口径变化时递增，测试据此固定行为。
RULE_VERSION = 2

#: 结尾稳定阅读帧数：与无声解析、A5/A8 共用同一常量，避免两处口径漂移。
STABLE_READING_FRAMES = beat_mod.STABLE_READING_FRAMES

#: 有声时间轴与字幕 cue 之间允许的取整差（帧）。两边各自向外取整，
#: 衔接处最多差一帧，属于同一份边界的正常表现。
SYNC_TOLERANCE_FRAMES = 1

#: A 系列的固定顺序与人读标题。报告、终端摘要与文档共用。
A_GATES: tuple[tuple[str, str], ...] = (
    ("A1", "节拍覆盖"),
    ("A2", "含义声明"),
    ("A3", "状态或关系变化"),
    ("A4", "字幕同步"),
    ("A5", "结尾停留"),
    ("A6", "装饰动画人工裁决"),
    ("A7", "单一焦点"),
    ("A8", "稳定结束"),
)

#: 机检闸门（进错误数与退出码）与人工闸门分开声明，避免把 A6 误当成机检。
MACHINE_GATES: tuple[str, ...] = ("A1", "A2", "A3", "A4", "A5", "A7", "A8")

#: 关系容器：内部子节点按 beat 标记「当前阶段」，被标记的那个就是焦点。
STAGE_CONTAINERS: frozenset[str] = frozenset({"flow", "cycle", "timeline"})


def _segments(scene: dict[str, Any]) -> list[dict[str, Any]]:
    raw = scene.get("narrationSegments")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _nodes(tree: Any):
    """深度优先遍历场景树节点（与 ``visual_narrative`` 同一口径）。"""
    if not isinstance(tree, dict):
        return
    yield tree
    children = tree.get("children")
    if isinstance(children, list):
        for child in children:
            yield from _nodes(child)


def _declared_focus(scene: dict[str, Any]) -> list[str]:
    """显式声明 ``state: 'focus'`` 的节点 id。"""
    return [
        str(node.get("id"))
        for node in _nodes(scene.get("sceneTree"))
        if node.get("state") == "focus"
    ]


def _stage_children(scene: dict[str, Any]) -> dict[str, list[str]]:
    """关系容器 id → 子节点 id 列表（用于「当前阶段即焦点」判定）。"""
    stages: dict[str, list[str]] = {}
    for node in _nodes(scene.get("sceneTree")):
        if node.get("type") in STAGE_CONTAINERS:
            children = node.get("children")
            if isinstance(children, list):
                stages[str(node.get("id"))] = [
                    str(child.get("id")) for child in children if isinstance(child, dict)
                ]
    return stages


def timeline_for(scene: dict[str, Any], resolved: Any = None) -> beat_mod.BeatTimeline:
    """一幕的 beat 时间轴：有声用 ``resolvedBeats``，无声按声明时长估算。

    ``resolved`` 可以是媒体清单里的 ``resolvedBeats`` 列表（优先），
    为空时退回无声估算。没有分段口播的幕得到空时间轴。
    """
    if not _segments(scene):
        return beat_mod.BeatTimeline((), True)
    if resolved:
        return beat_mod.BeatTimeline.from_json(resolved, estimated=False)
    return beat_mod.resolve_silent(scene)


def _sample_frames(scene: dict[str, Any], timeline: beat_mod.BeatTimeline, duration: Any) -> list[int]:
    """焦点判定的采样帧。

    焦点集合只在 beat 边界处变化（显式状态与当前阶段都是分段常量），
    因此取幕首、每条 beat 的起止与幕尾即可覆盖所有**不同**状态，
    不必逐帧扫全片。幕尾取**实际**时长（有声时是媒体清单里的派生时长）。
    """
    last = duration - 1 if isinstance(duration, int) and not isinstance(duration, bool) and duration > 0 else 0
    frames = {0, last}
    for beat in timeline.beats:
        frames.add(beat.start_frame)
        frames.add(beat.end_frame)
    return sorted(frame for frame in frames if frame >= 0)


def _focus_counts(
    scene: dict[str, Any], timeline: beat_mod.BeatTimeline, duration: Any
) -> list[dict[str, Any]]:
    """逐采样帧的焦点对象清单；只列出数量 > 1 的帧。

    焦点有两个来源：节点显式声明 ``state: 'focus'``，以及关系容器里被当前
    beat 点亮的阶段。后者与运行时 ``stageState`` 同一口径——当前 beat 的
    目标命中的子节点就是当前阶段。
    """
    declared = _declared_focus(scene)
    stages = _stage_children(scene)
    beats = beat_mod.beats_by_id(scene)
    offenders: list[dict[str, Any]] = []
    for frame in _sample_frames(scene, timeline, duration):
        state = timeline.state_at(frame)
        current = state["current"]
        targets = {str(target) for target in (beats.get(current) or {}).get("targets") or []} if current else set()
        focused = list(declared)
        for children in stages.values():
            focused.extend(child for child in children if child in targets)
        if len(focused) > 1:
            offenders.append({"frame": frame, "current": current, "focus": focused})
    return offenders


def _cue_windows(
    narration: str, texts: Sequence[str], cues: Sequence[dict[str, Any]]
) -> list[tuple[float, float]] | None:
    """把字幕 cue 归到各口播段，返回逐段秒区间；归不上时返回 ``None``。

    cue 文本是原文按标点切片后 ``strip()`` 的结果，因此对齐时跳过空白；
    一段的区间取它第一个 cue 的起点与最后一个 cue 的终点。cue 跨过段边界
    说明字幕与口播段没有共用边界，如实返回 ``None`` 交给 A4 报告。
    """
    bounds: list[tuple[int, int]] = []
    cursor = 0
    for text in texts:
        bounds.append((cursor, cursor + len(text)))
        cursor += len(text)
    if cursor != len(narration):
        return None
    windows: list[list[float | None]] = [[None, None] for _ in texts]
    position, index = 0, 0
    for cue in cues:
        text = str(cue.get("text") or "")
        for char in text:
            while position < len(narration) and narration[position].isspace():
                position += 1
            if position >= len(narration) or narration[position] != char:
                return None
            position += 1
        while index < len(bounds) - 1 and position > bounds[index][1]:
            index += 1
        if position > bounds[index][1]:
            return None
        start, end = cue.get("start"), cue.get("end")
        if any(isinstance(t, bool) or not isinstance(t, (int, float)) for t in (start, end)):
            return None
        window = windows[index]
        if window[0] is None:
            window[0] = float(start)
        window[1] = float(end)
    if any(window[0] is None for window in windows):
        return None
    return [(float(window[0]), float(window[1])) for window in windows]


def _a4_scene(
    scene: dict[str, Any],
    cues: Sequence[dict[str, Any]],
    timeline: beat_mod.BeatTimeline,
    fps: Any,
    duration: Any,
) -> list[str]:
    """一幕的字幕同步问题；无 cue 时由调用方跳过。

    ``duration`` 是这一幕的**实际**帧数（有声时取媒体清单里的派生时长）：
    场景可能被 TTS 拉长，拿源分镜的声明时长去解析会把合法区间报成越界。
    """
    scene_id = str(scene.get("id"))
    if timeline.estimated:
        return [f"{scene_id}: 有媒体时 beat 必须来自真实词边界，当前是无声估算时间轴"]
    texts = [str(item.get("text", "")) for item in _segments(scene)]
    windows = _cue_windows(beat_mod.scene_narration(scene), texts, cues)
    if windows is None:
        return [f"{scene_id}: 字幕 cue 与口播段切法不一致（cue 跨过段边界或文本对不上）"]
    if isinstance(fps, bool) or not isinstance(fps, int) or isinstance(duration, bool) or not isinstance(duration, int):
        return [f"{scene_id}: 缺少 fps 或 durationInFrames，无法核对字幕同步"]
    try:
        from_cues = beat_mod.resolve_from_windows(scene, windows, fps, duration)
    except A2VError as exc:
        return [f"{scene_id}: 字幕边界无法解析为节拍区间（{exc}）"]
    if len(from_cues.beats) != len(timeline.beats):
        return [
            f"{scene_id}: 字幕解析出 {len(from_cues.beats)} 条 beat，画面时间轴有 {len(timeline.beats)} 条"
        ]
    issues: list[str] = []
    for expected, actual in zip(from_cues.beats, timeline.beats):
        if any("speech" in item for item in _segments(scene)):
            # 段级合成的 beat 包含前后停顿及 WAV 中的边界静音；字幕只覆盖讲话。
            # 仍检查文本、顺序和讲话区间包含关系，不能用旧的边界相等判据。
            if expected.start_frame < actual.start_frame - SYNC_TOLERANCE_FRAMES or expected.end_frame > actual.end_frame + SYNC_TOLERANCE_FRAMES:
                issues.append(f"{scene_id}: beat {actual.id} 的字幕越出含停顿的画面区间")
            continue
        if (
            abs(expected.start_frame - actual.start_frame) > SYNC_TOLERANCE_FRAMES
            or abs(expected.end_frame - actual.end_frame) > SYNC_TOLERANCE_FRAMES
        ):
            issues.append(
                f"{scene_id}: beat {actual.id} 的字幕区间 [{expected.start_frame},{expected.end_frame}) "
                f"与画面区间 [{actual.start_frame},{actual.end_frame}) 相差超过 {SYNC_TOLERANCE_FRAMES} 帧"
            )
    return issues


def _decorations(
    scene_id: str, scene: dict[str, Any], declared: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """一幕里「不服务于任何 beat」的入场配方——纯装饰，需要人工裁决。

    这类配方不是错的：节奏感和画面稳定常常需要它们。但「这条动效是否恰当」
    是审美判断，机检给不出结论，因此只列出来交给 A6。
    """
    targets = {
        str(target)
        for beat in declared.values()
        for target in (beat.get("targets") or [])
    }
    decorations: list[dict[str, Any]] = []
    for motion in scene.get("motions") or []:
        if not isinstance(motion, dict):
            continue
        motion_targets = motion.get("targets") if isinstance(motion.get("targets"), list) else [motion.get("target")]
        for raw_target in motion_targets:
            target = str(raw_target)
            if target in targets:
                continue
            decorations.append(
                {
                    "id": f"{scene_id}:{target}",
                    "scene": scene_id,
                    "target": target,
                    "recipe": str(motion.get("recipe")),
                }
            )
    return decorations


def scene_cues(
    cues: Sequence[dict[str, Any]],
    scene_start_frame: int,
    scene_frames: int,
    fps: int,
) -> list[dict[str, Any]]:
    """切出属于某一幕的字幕 cue，并把时间换算成**幕内**秒。

    媒体清单里的字幕是整片时间轴上的一个列表，而 ``resolvedBeats`` 是幕内
    帧区间；两者要对齐，必须先把 cue 按幕切开再换算，否则第二幕的 cue 会被
    拿去和第一幕的节拍比。
    """
    start_seconds = scene_start_frame / fps
    end_seconds = (scene_start_frame + scene_frames) / fps
    local: list[dict[str, Any]] = []
    for cue in cues:
        if not isinstance(cue, dict):
            continue
        start, end = cue.get("start"), cue.get("end")
        if any(isinstance(t, bool) or not isinstance(t, (int, float)) for t in (start, end)):
            continue
        if not (start_seconds <= float(start) < end_seconds):
            continue
        local.append(
            {
                "text": str(cue.get("text") or ""),
                "start": float(start) - start_seconds,
                "end": float(end) - start_seconds,
            }
        )
    return local


def analyze(storyboard: dict[str, Any], media: dict[str, Any] | None = None) -> dict[str, Any]:
    """跑完 A1–A5、A7、A8 的确定性判定，返回逐幕事实与闸门结构。

    ``media`` 是已读取的媒体清单（``None`` 表示无声预览）：有声时 A4 才有
    可核对的字幕边界，无声时 A4 如实写成「跳过（无媒体）」。有媒体时逐幕
    时长取**清单里的派生时长**——场景可能被 TTS 拉长，结尾余量要按实际
    长度算，否则 A5 会把「派生后其实很宽裕」的幕报成余量不足。
    """
    if storyboard.get("version") != 3 or storyboard.get("schemaVersion") != 3 or (
        isinstance(storyboard.get("scenes"), list)
        and any(isinstance(scene, dict) and "narration" in scene for scene in storyboard["scenes"])
    ):
        raise ValueError("不支持 v3 之前分镜或字符串口播；请按分镜 v3 契约重新编排")
    scenes = storyboard.get("scenes")
    scenes = scenes if isinstance(scenes, list) else []
    fps = storyboard.get("fps")
    fps = fps if isinstance(fps, int) and not isinstance(fps, bool) and fps > 0 else 30
    media_scenes: dict[str, dict[str, Any]] = {}
    all_cues: list[dict[str, Any]] = []
    if isinstance(media, dict):
        raw = media.get("scenes")
        if isinstance(raw, list):
            media_scenes = {str(item.get("id")): item for item in raw if isinstance(item, dict)}
        if isinstance(media.get("cues"), list):
            all_cues = [cue for cue in media["cues"] if isinstance(cue, dict)]

    facts: list[dict[str, Any]] = []
    cursor = 0
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        scene_id = str(scene.get("id"))
        segments = _segments(scene)
        declared = beat_mod.beats_by_id(scene)
        media_scene = media_scenes.get(scene_id) or {}
        duration = media_scene.get("durationInFrames", scene.get("durationInFrames"))
        if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
            duration = scene.get("durationInFrames") if isinstance(scene.get("durationInFrames"), int) else 0
        resolved = media_scene.get("resolvedBeats") or scene.get("resolvedBeats")
        try:
            timeline = timeline_for(scene, resolved)
        except A2VError as exc:
            facts.append({"id": scene_id, "error": str(exc), "hasSegments": bool(segments)})
            cursor += duration
            continue
        facts.append(
            {
                "id": scene_id,
                "hasSegments": bool(segments),
                "segmentCount": len(segments),
                "beatCount": len(declared),
                "estimated": timeline.estimated,
                "resolved": [beat.to_json() for beat in timeline.beats],
                "durationInFrames": duration,
                "declaredDurationInFrames": scene.get("durationInFrames"),
                "cues": scene_cues(all_cues, cursor, duration, fps),
                "motions": scene.get("motions") or [],
                "narrationSegments": scene.get("narrationSegments") or [],
                "beats": scene.get("beats") or [],
                "decorations": _decorations(scene_id, scene, declared),
                "focus": _focus_counts(scene, timeline, duration),
            }
        )
        cursor += duration
    return {
        "ruleVersion": RULE_VERSION,
        "stableReadingFrames": STABLE_READING_FRAMES,
        "syncToleranceFrames": SYNC_TOLERANCE_FRAMES,
        "fps": fps,
        "hasMedia": isinstance(media, dict),
        "scenes": facts,
        "storyboard": storyboard,
    }


def _gate(gate_id: str, status: str, *, scenes: Any = None, detail: str = "", **extra: Any) -> dict[str, Any]:
    title = dict(A_GATES)[gate_id]
    payload: dict[str, Any] = {"id": gate_id, "title": title, "status": status, "detail": detail}
    if scenes is not None:
        payload["scenes"] = scenes
    payload.update(extra)
    return payload


def review_gates(analysis: dict[str, Any]) -> dict[str, Any]:
    """把全片分析整理成 A1–A5、A7、A8 的闸门结论。

    状态只有三种：``pass``（量测通过）、``fail``（机检失败，进错误数与
    退出码）、``skipped``（不适用，例如无声时无法核对字幕同步）。跳过永远不写成通过。
    """
    storyboard = analysis["storyboard"]
    scenes_by_id = {
        str(scene.get("id")): scene
        for scene in (storyboard.get("scenes") or [])
        if isinstance(scene, dict)
    }
    new_work = [item for item in analysis["scenes"] if item.get("hasSegments")]

    # ---- A1 节拍覆盖 -------------------------------------------------------
    a1_issues: list[str] = []
    a1_scenes: list[str] = []
    for item in new_work:
        scene_id = item["id"]
        scene = scenes_by_id.get(scene_id) or {}
        segments = _segments(scene)
        declared = beat_mod.beats_by_id(scene)
        before = len(a1_issues)
        if item.get("error"):
            a1_issues.append(f"{scene_id}: {item['error']}")
            a1_scenes.append(scene_id)
            continue
        if not declared:
            a1_issues.append(f"{scene_id}: 分段口播没有声明任何 beat")
        referenced = [str(segment.get("beatId")) for segment in segments]
        for position, beat_id in enumerate(referenced):
            if beat_id not in declared:
                a1_issues.append(f"{scene_id}: 第 {position + 1} 段引用了不存在的 beat {beat_id}")
        for beat_id in declared:
            if beat_id not in referenced:
                a1_issues.append(f"{scene_id}: beat {beat_id} 没有被任何口播段引用")
        runs = [
            beat_id
            for position, beat_id in enumerate(referenced)
            if position == 0 or referenced[position - 1] != beat_id
        ]
        for beat_id in sorted({beat_id for beat_id in runs if runs.count(beat_id) > 1}):
            a1_issues.append(f"{scene_id}: beat {beat_id} 的口播段不连续，时间轴会倒退或重叠")
        if len(item["resolved"]) != len(declared):
            a1_issues.append(
                f"{scene_id}: 声明了 {len(declared)} 条 beat，只解析出 {len(item['resolved'])} 条帧区间"
            )
        if len(a1_issues) > before:
            a1_scenes.append(scene_id)
    a1 = _gate(
        "A1",
        "skipped" if not new_work else ("fail" if a1_issues else "pass"),
        detail="没有声明分段口播的幕" if not new_work else ("；".join(a1_issues) or "每段口播都绑定到有帧区间的 beat"),
        issues=a1_issues,
        scenes=a1_scenes or None,
        checkedScenes=[item["id"] for item in new_work] if new_work else None,
    )

    # ---- A2 含义声明 -------------------------------------------------------
    a2_issues: list[str] = []
    for item in new_work:
        scene = scenes_by_id.get(item["id"]) or {}
        for beat_id, beat in beat_mod.beats_by_id(scene).items():
            meaning = str(beat.get("meaning") or "").strip()
            if not meaning:
                a2_issues.append(f"{item['id']}: beat {beat_id} 没有声明 meaning")
                continue
            texts = "".join(
                str(segment.get("text", ""))
                for segment in _segments(scene)
                if str(segment.get("beatId")) == beat_id
            ).strip()
            if texts and meaning == texts:
                a2_issues.append(
                    f"{item['id']}: beat {beat_id} 的 meaning 是口播原文的复述，没有说明它解释了什么"
                )
            elif meaning == beat_mod.ACTION_LABELS.get(str(beat.get("action")), ""):
                a2_issues.append(
                    f"{item['id']}: beat {beat_id} 的 meaning 只重复了动作名「{meaning}」"
                )
    a2 = _gate(
        "A2",
        "skipped" if not new_work else ("fail" if a2_issues else "pass"),
        detail="没有声明分段口播的幕" if not new_work else ("；".join(a2_issues) or "每条 beat 都声明了它解释的内容"),
        issues=a2_issues,
    )

    # ---- A3 状态或关系变化 -------------------------------------------------
    a3_issues: list[str] = []
    a3_scenes: list[dict[str, Any]] = []
    checked = 0
    for item in new_work:
        scene = scenes_by_id.get(item["id"]) or {}
        if vn.analyze_scene(scene)["isTextScene"]:
            continue
        checked += 1
        beats = beat_mod.beats_by_id(scene)
        actions = [str(beat.get("action")) for beat in beats.values()]
        changes = [action for action in actions if action in beat_mod.CHANGE_ACTIONS]
        neutral = [action for action in actions if action in beat_mod.NEUTRAL_ACTIONS]
        if len(beats) < beat_mod.MIN_BEATS_PER_SCENE:
            a3_issues.append(
                f"{item['id']}: 非文字幕只有 {len(beats)} 条 beat，至少需要 {beat_mod.MIN_BEATS_PER_SCENE} 条"
            )
        if not changes:
            a3_issues.append(
                f"{item['id']}: 没有任何 beat 改变对象状态或关系"
                + (f"（只有 {'、'.join(sorted(set(neutral)))}）" if neutral else "")
            )
            a3_scenes.append({"id": item["id"], "actions": actions, "neutral": neutral})
    a3 = _gate(
        "A3",
        "skipped" if not checked else ("fail" if a3_issues else "pass"),
        detail="没有声明分段口播的非文字幕" if not checked else ("；".join(a3_issues) or "每条非文字幕都有改变状态或关系的 beat"),
        issues=a3_issues,
        scenes=a3_scenes or None,
    )

    # ---- A4 字幕同步 -------------------------------------------------------
    a4_issues: list[str] = []
    a4_checked = 0
    for item in new_work:
        cues = item.get("cues") or []
        if not cues:
            continue
        a4_checked += 1
        scene = scenes_by_id.get(item["id"]) or {}
        timeline = beat_mod.BeatTimeline.from_json(item["resolved"], estimated=bool(item["estimated"]))
        a4_issues.extend(_a4_scene(scene, cues, timeline, analysis.get("fps"), item.get("durationInFrames")))
    if not analysis["hasMedia"]:
        a4 = _gate("A4", "skipped", detail="无声预览没有字幕边界可核对")
    elif not a4_checked:
        a4 = _gate("A4", "skipped", detail="媒体清单里没有声明分段口播的幕")
    else:
        a4 = _gate(
            "A4",
            "fail" if a4_issues else "pass",
            detail="；".join(a4_issues) or f"{a4_checked} 幕字幕讲话区间与对应节拍匹配（段级含停顿；旧路径边界容差 {SYNC_TOLERANCE_FRAMES} 帧）",
            issues=a4_issues,
        )

    # ---- A5 结尾停留 -------------------------------------------------------
    a5_issues: list[str] = []
    a5_scenes: list[dict[str, Any]] = []
    for item in new_work:
        duration = item.get("durationInFrames")
        if not isinstance(duration, int) or not item["resolved"]:
            continue
        last_end = int(item["resolved"][-1]["endFrame"])
        remaining = duration - last_end
        if remaining < STABLE_READING_FRAMES:
            a5_issues.append(
                f"{item['id']}: 最后一条 beat 在第 {last_end} 帧完成，距幕尾只有 {remaining} 帧，"
                f"少于 {STABLE_READING_FRAMES} 帧稳定阅读"
            )
            a5_scenes.append(
                {"id": item["id"], "completedFrame": last_end, "durationInFrames": duration, "remainingFrames": remaining}
            )
    a5 = _gate(
        "A5",
        "skipped" if not new_work else ("fail" if a5_issues else "pass"),
        detail="没有声明分段口播的幕" if not new_work else ("；".join(a5_issues) or f"每幕都留足 {STABLE_READING_FRAMES} 帧稳定阅读"),
        issues=a5_issues,
        scenes=a5_scenes or None,
    )

    # ---- A7 单一焦点 -------------------------------------------------------
    a7_issues: list[str] = []
    a7_scenes: list[dict[str, Any]] = []
    for item in new_work:
        if not item.get("focus"):
            continue
        for offender in item["focus"]:
            a7_issues.append(
                f"{item['id']}: 第 {offender['frame']} 帧有 {len(offender['focus'])} 个焦点"
                f"（{'、'.join(offender['focus'])}）"
            )
        a7_scenes.append({"id": item["id"], "frames": item["focus"]})
    a7 = _gate(
        "A7",
        "skipped" if not new_work else ("fail" if a7_issues else "pass"),
        detail="没有声明分段口播的幕" if not new_work else ("；".join(a7_issues) or "任一帧最多一个焦点对象"),
        issues=a7_issues,
        scenes=a7_scenes or None,
    )

    # ---- A8 稳定结束 -------------------------------------------------------
    a8_issues: list[str] = []
    a8_scenes: list[dict[str, Any]] = []
    for item in new_work:
        duration = item.get("durationInFrames")
        if not isinstance(duration, int):
            continue
        deadline = duration - STABLE_READING_FRAMES
        for motion in item.get("motions") or []:
            if not isinstance(motion, dict):
                continue
            phase = str(motion.get("phase") or "")
            beat = next((resolved for resolved in item["resolved"] if resolved.get("id") == motion.get("beatId")), None)
            if beat:
                start = int(beat["startFrame"])
                end = start + int(motion.get("durationFrames") or 1)
            else:
                from .motion_plan import phase_spans
                phases = phase_spans({"durationInFrames": duration, "narrationSegments": item.get("narrationSegments"), "beats": item.get("beats")})
                span = phases.get(phase)
                if span is None:
                    continue
                start = span.start_frame
                end = min(span.end_frame, start + int(motion.get("durationFrames") or span.end_frame - span.start_frame))
            if end > deadline:
                a8_issues.append(f"{item['id']}: 配方 {motion.get('recipe')} 作用于 {motion.get('target') or motion.get('targets')}，到第 {end} 帧才结束，距幕尾不足 {STABLE_READING_FRAMES} 帧")
                a8_scenes.append({"id": item["id"], "target": motion.get("target") or motion.get("targets"), "recipe": motion.get("recipe"), "endFrame": end, "deadlineFrame": deadline})
    a8 = _gate(
        "A8",
        "skipped" if not new_work else ("fail" if a8_issues else "pass"),
        detail="没有声明分段口播的幕" if not new_work else ("；".join(a8_issues) or f"所有配方在幕尾前 {STABLE_READING_FRAMES} 帧结束"),
        issues=a8_issues,
        scenes=a8_scenes or None,
    )

    return {
        "ruleVersion": RULE_VERSION,
        "stableReadingFrames": STABLE_READING_FRAMES,
        "syncToleranceFrames": SYNC_TOLERANCE_FRAMES,
        "hasMedia": analysis["hasMedia"],
        "a1": a1,
        "a2": a2,
        "a3": a3,
        "a4": a4,
        "a5": a5,
        "a7": a7,
        "a8": a8,
    }


def gate_issues(gates: dict[str, Any]) -> list[tuple[str, str]]:
    """机检失败项：``(闸门标题, 问题描述)``，供调用方并入错误数。"""
    issues: list[tuple[str, str]] = []
    for gate_id in MACHINE_GATES:
        gate = gates.get(gate_id.lower()) or {}
        if gate.get("status") != "fail":
            continue
        for message in gate.get("issues") or [gate.get("detail") or ""]:
            issues.append((f"动画论证 {gate_id}", str(message)))
    return issues


#: A6 的人工结论必须达到的最低分（满分 5）。
A6_MIN_SCORE = 4


def decorations(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """全片需要人工裁决的装饰配方（A6 的候选清单）。"""
    return [
        item
        for scene in analysis["scenes"]
        for item in (scene.get("decorations") or [])
    ]


def review_a6(path: str | Path, analysis: dict[str, Any]) -> dict[str, Any]:
    """解析 ``review.md`` 里的人工「装饰动画」结论（A6）。

    分数取自六项评分表的「动效服务」行（这一项的机检部分正是 A1–A5、A7、A8，
    人工部分正是 A6），也接受 ``| 装饰动画 | N |`` 或 A6 小节里的 ``评分：N/5``。
    候选配方在 ``候选裁决`` 小节逐条写 ``- <场景>:<目标>：结论`` 视为已裁决。
    未填写结论时状态为「待评审」；评分低于 4/5 或存在未裁决候选时
    ``publishable`` 为 False——缺失或跳过永远不会被记成通过。
    """
    candidates = decorations(analysis)
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError:
        text = ""
    score: int | None = None
    resolved: set[str] = set()
    if text:
        # 「装饰动画」「动效服务理解」都被接受：前者是量表里的别名，
        # 后者是早期模板用的标签，旧记录不该因为措辞不同就退回「待评审」。
        row = re.search(r"^\s*\|\s*(?:动效服务|动效服务理解|装饰动画)\s*\|\s*([0-5])\s*\|", text, re.MULTILINE)
        if row:
            score = int(row.group(1))
        else:
            inline = re.search(r"评分[:：]\s*([0-5])\s*(?:/\s*5)?(?!\d)", text)
            if not inline:
                inline = re.search(r"(?:装饰动画|动效服务|A6)[^\n]*?([0-5])\s*/\s*5", text)
            if inline:
                score = int(inline.group(1))
        # 优先取显式 A6 小节；否则会误把前面的 V5「候选裁决」当成 A6。
        section = re.search(
            r"^\s*#{2,6}\s*A6[^\n]*?候选裁决[^\n]*\n(.*?)(?=^\s*#{2,6}\s|\Z)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        if not section:
            section = re.search(
                r"^\s*#{2,6}\s*候选裁决[^\n]*\n(.*?)(?=^\s*#{2,6}\s|\Z)",
                text,
                re.MULTILINE | re.DOTALL,
            )
        if section:
            resolved = set(
                re.findall(r"^\s*[-*]\s*([A-Za-z0-9_:-]+)\s*[:：]", section.group(1), re.MULTILINE)
            )
    unresolved = [item["id"] for item in candidates if item["id"] not in resolved]
    if score is None:
        status = "待评审"
    elif score < A6_MIN_SCORE:
        status = "不通过"
    elif unresolved:
        status = "候选未裁决"
    else:
        status = "通过"
    return {
        "id": "A6",
        "title": "装饰动画人工裁决",
        "status": status,
        "score": score,
        "minScore": A6_MIN_SCORE,
        "candidates": candidates,
        "unresolvedCandidates": unresolved,
        "publishable": status == "通过",
    }
