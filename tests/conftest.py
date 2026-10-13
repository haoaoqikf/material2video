"""测试夹具：导入位于 src/ 的 m2v 包。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))
SCRIPT_TOOLS_DIR = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "material2video" / "scripts"
sys.path.insert(0, str(SCRIPT_TOOLS_DIR))

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples" / "buffer-smoothing"

# 项目根标记的相对路径，与 m2v.paths.PROJECT_MARKER 保持一致
SKILL_MARKER = Path(".agents/skills/material2video/SKILL.md")


def make_project(
    tmp_path: Path, kind: str, slug: str, script: dict | None = None,
    video_type: str = "article-narrative",
) -> Path:
    """在 tmp_path 下搭一个最小的规范项目，返回文章目录。

    kind 取 "videos" 或 "examples"；script 提供时写入 storyboard.json。
    路径规则依赖项目根标记，因此每个用例都必须先有标记文件。
    """
    marker = tmp_path / SKILL_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("# material2video skill", encoding="utf-8")

    article = (tmp_path / kind / video_type / slug) if kind == "videos" else (tmp_path / kind / slug)
    article.mkdir(parents=True, exist_ok=True)
    (article / "index.html").write_text("<!doctype html><html></html>", encoding="utf-8")
    if script is not None:
        (article / "storyboard.json").write_text(
            json.dumps(script, ensure_ascii=False), encoding="utf-8"
        )
    return article


def approve_production_record(storyboard_path: str | Path, media_path: str | Path | None = None,
                             content_root: str | Path | None = None) -> Path:
    """为渲染路径测试创建当前指纹绑定的通过记录，不运行人工评审工具。"""
    import m2v.types.article.article_text as article_text
    import m2v.types.article.paths as paths
    import m2v.types.article.production as production

    source = Path(storyboard_path)
    raw = json.loads(source.read_text(encoding="utf-8"))
    article = paths.for_storyboard(source, content_root)
    input_path = article.source_dir / "article.md"
    input_path.write_text("测" * 140, encoding="utf-8")
    input_review = article_text.review_for_file(input_path, article.workspace_root)
    input_review.update({"status": "pass", "singleScene": {
        "status": "pass", "claim": "测试观点", "metaphor": "持续系统",
        "problemSpans": [], "rationale": "测试夹具使用持续视觉世界"},
        "assessment": {"reviewer": "ai", "model": "test", "session": "test-session"}})
    current = production.current_fingerprints(source, media_path, article)
    record = production.initialize_template(raw, current, input_review)
    record["materialRoot"] = os.path.relpath(article.workspace_root.resolve(), production.record_path(article).parent.resolve())
    material_digests = {}
    for name in ("keyframes", "samples", "rehearsal"):
        material = article.workspace_root / "outputs" / name
        material.parent.mkdir(parents=True, exist_ok=True)
        material.write_bytes(f"test {name}".encode())
        import hashlib
        material_digests[name] = hashlib.sha256(material.read_bytes()).hexdigest()
    record["materials"] = {
        name: {"path": f"outputs/{name}", "sha256": material_digests[name],
               "fingerprints": current}
        for name in ("keyframes", "samples", "rehearsal")
    }
    scenes = raw.get("stages") or raw.get("scenes") or []
    ids = [str(scene.get("id", "")) for scene in scenes]
    if not ids:
        raise AssertionError("渲染路径测试需要至少一个阶段")
    record["direction"]["keyScenes"] = {
        "opening": ids[0], "core": ids[min(1, len(ids) - 1)], "climax": ids[-1]
    }
    record["direction"]["pace"] = "测试用关键幕与全片节奏说明"
    record["direction"]["scenePlans"] = {
        scene_id: {"start": "测试起点", "change": "测试变化", "result": "测试结果"}
        for scene_id in ids
    }

    def passing(kind: str, full: bool = False) -> dict:
        material = "keyframes" if kind == "static" else ("rehearsal" if full else "samples")
        return {
            "status": "pass",
            "dimensions": {name: {"status": "pass", "evidence": "渲染测试夹具", **({"score": 4} if kind == "content" else {})}
                           for name in production.REVIEW_DIMENSIONS[kind]},
            "evidence": "渲染测试夹具",
            "assessment": {"reviewer": "ai", "model": "test", "session": "test-session",
                           "materials": {material: material_digests[material]}},
        }

    record["reviews"]["keyScenes"] = {
        scene_id: {"static": passing("static"), "dynamic": passing("dynamic")}
        for scene_id in set(record["direction"]["keyScenes"].values())
    }
    record["reviews"]["full"] = {kind: passing(kind, full=True) for kind in ("static", "dynamic", "content")}
    # v4 正式渲染门禁要求全片连续性五项都有结论：未填的 pending 会阻断渲染，
    # 这里按「已看过 samples 动态材料」的通过结论绑定材料摘要。
    record["continuity"] = {
        name: {
            "status": "pass", "stageId": ids[0], "frameRange": [0, 0], "timeRange": [0.0, 0.0],
            "evidence": "渲染测试夹具：五项连续性已核对", "material": "samples",
            "materialSha256": material_digests["samples"],
            "assessment": {"reviewer": "ai", "model": "test", "session": "test-session"},
        }
        for name in production.CONTINUITY_DIMENSIONS
    }
    target = production.record_path(article)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def approve_input_review(storyboard_path: str | Path, content_root: str | Path | None = None) -> Path:
    """准备通过的最小输入审查，供 prepare CLI 路径测试使用。"""
    import m2v.types.article.article_text as article_text
    import m2v.types.article.paths as paths
    import m2v.types.article.production as production

    source = Path(storyboard_path)
    article = paths.for_storyboard(source, content_root)
    input_path = article.source_dir / "article.md"
    input_path.write_text("测" * 140, encoding="utf-8")
    review = article_text.review_for_file(input_path, article.workspace_root)
    review.update({"status": "pass", "singleScene": {
        "status": "pass", "claim": "测试观点", "metaphor": "持续系统",
        "problemSpans": [], "rationale": "测试夹具使用持续视觉世界"},
        "assessment": {"reviewer": "ai", "model": "test", "session": "test-session"}})
    record = {"inputReview": review,
              "materialRoot": os.path.relpath(article.workspace_root.resolve(), article.source_dir.resolve())}
    target = production.record_path(article)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


@pytest.fixture(scope="session")
def chromium_ready():
    """浏览器不可用时跳过，而不是让整个测试套件失败。"""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            playwright.chromium.launch(headless=True).close()
    except Exception as exc:  # noqa: BLE001 - 任何启动失败都应降级为跳过
        pytest.skip(f"未安装可用的 Playwright Chromium: {exc}")


def write_tone(path: Path, duration: float = 1.0) -> None:
    """写一段可解码的 440Hz WAV，作为 TTS 替身的音频。"""
    import math
    import struct
    import wave

    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        frames = (
            struct.pack("<h", int(2000 * math.sin(2 * math.pi * 440 * n / 24000)))
            for n in range(round(duration * 24000))
        )
        stream.writeframes(b"".join(frames))


def make_jpeg(width: int = 64, height: int = 96, color: str = "gray") -> bytes:
    """用 ffmpeg 生成一张 JPEG，用来在没有浏览器的前提下驱动编码器。"""
    import subprocess

    from imageio_ffmpeg import get_ffmpeg_exe

    completed = subprocess.run(
        [
            get_ffmpeg_exe(),
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s={width}x{height}",
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-c:v",
            "mjpeg",
            "-",
        ],
        capture_output=True,
    )
    assert completed.returncode == 0 and completed.stdout, "生成测试 JPEG 失败"
    return completed.stdout


@pytest.fixture
def speech(monkeypatch):
    """替换 edge-tts，让需要真实媒体清单的用例不访问网络。

    语速按中文标准口播的常见节奏（每字约 0.25 秒）折算：v4 的 prepare
    用**实际语音时长**派生阶段，太快会让合规的 130～170 字口播落进
    35 秒以下的实际时长不合格。
    """
    import re

    import m2v.types.article.prepare as prep

    async def fake(text, voice, rate, output):
        tokens = re.findall(r"[\w\u4e00-\u9fff]", text)
        # 音轨长度按字数放大，并让字词时间戳严格落在音轨内且单调递增：
        # 字幕校验会同时检查这两点，示例口播比单元测试长得多。
        write_tone(output, 0.3 + len(tokens) * 0.25)
        return [
            {"text": token, "start": 0.1 + i * 0.25, "end": 0.2 + i * 0.25}
            for i, token in enumerate(tokens)
        ]

    monkeypatch.setattr(prep, "synthesize", fake)


@pytest.fixture
def valid_script() -> dict:
    """一份结构完整的最小分镜脚本，测试中按需局部改动。"""
    return {
        "version": 3, "schemaVersion": 3, "directingVersion": 1,
        "directingBrief": {"thesis": "投入方向决定成长", "audienceShift": "由努力转向反馈", "emotionalArc": ["疑问", "理解"], "visualMotif": "路径", "stylePack": "editorial", "avoid": []},
        "fps": 30, "width": 1080, "height": 1920, "title": "测试视频",
        "visual": {"theme": "dark", "preset": "keynote"},
        "visualDirection": {"motif": "路径", "compositionBias": "mixed", "density": "balanced", "rhythm": "steady", "avoid": []},
        "scenes": [
            {
                "id": "opening", "type": "title", "durationInFrames": 90,
                "data": {"text": "开场"}, "renderer": {"kind": "tree"},
                "visualIntent": {"relation": "focus", "focus": "text", "composition": "offset", "density": "sparse", "tone": "neutral", "mode": "typography", "claim": "方向影响努力效果", "showWithoutText": "一条路径偏向单侧，前方留有空间", "primaryObject": "偏置路径", "motionMeaning": "镜头把注意力推向路径出口"},
                "camera": {"shot": "medium", "composition": "left", "depth": "layered", "focus": "copy", "segments": [{"kind": "hold", "phase": "establish", "intensity": 0}, {"kind": "push-in", "phase": "change", "focus": "copy", "intensity": 0.5}]},
                "narrationSegments": [{"id": "n1", "text": "先看开场。", "beatId": "b1"}, {"id": "n2", "text": "再看路径。", "beatId": "b2"}],
                "beats": [{"id": "b1", "action": "establish", "targets": ["copy"], "meaning": "建立判断焦点"}, {"id": "b2", "action": "transform", "targets": ["copy"], "meaning": "强调判断的方向变化"}],
                "sceneTree": {"id": "root", "type": "stack", "children": [{"id": "copy", "type": "text", "contentRef": "data.text", "role": "headline"}]},
                "motions": [{"target": "copy", "recipe": "reveal", "phase": "establish", "durationFrames": 24}],
            },
            {
                "id": "closing", "type": "conclusion", "durationInFrames": 90,
                "data": {"text": "结论"}, "renderer": {"kind": "tree"},
                "visualIntent": {"relation": "focus", "focus": "text", "composition": "full", "density": "sparse", "tone": "decisive", "mode": "typography", "claim": "结论需要稳定阅读", "showWithoutText": "一个物体停在画面中轴，外围充分留白", "primaryObject": "结论文字", "motionMeaning": "收束动作让结论停定"},
                "camera": {"shot": "wide", "composition": "center", "depth": "flat", "focus": "copy", "segments": [{"kind": "hold", "phase": "establish", "intensity": 0}, {"kind": "reframe", "phase": "result", "focus": "copy", "intensity": 0.25}, {"kind": "settle", "phase": "settle", "intensity": 0}]},
                "transition": {"kind": "inherit", "source": "copy", "target": "copy", "meaning": "将判断焦点带入结论"},
                "narrationSegments": [{"id": "n1", "text": "现在收束。", "beatId": "b1"}, {"id": "n2", "text": "留下结论。", "beatId": "b2"}],
                "beats": [{"id": "b1", "action": "establish", "targets": ["copy"], "meaning": "建立结论焦点"}, {"id": "b2", "action": "transform", "targets": ["copy"], "meaning": "完成结论收束"}],
                "sceneTree": {"id": "root", "type": "overlay", "children": [{"id": "copy", "type": "text", "contentRef": "data.text", "role": "headline"}]},
                "motions": [{"target": "copy", "recipe": "fade", "beatId": "b2", "durationFrames": 24}],
            },
        ],
    }


# ---------------------------------------------------------------------------
# v4 契约夹具：入口只接受 v4，因此新的路径/媒体用例都以它为基础
# ---------------------------------------------------------------------------

#: 三段式 v4 分镜的骨架：全片 1200 帧（40 秒）、tree renderer、全局对象与镜头。
_STAGE_TEXT = {
    "opening": [
        ("open-1", "先看一次成本很低的投掷，落点马上就能看见。", "beat-open"),
        ("open-2", "偏差落在同一张靶上，不需要任何解释。", "beat-aim"),
        ("open-3", "画面里的人物没有停手，他在继续试。", "beat-aim"),
    ],
    "core": [
        ("core-1", "每次记录落点，也要顺手记录修正的方向。", "beat-adjust"),
        ("core-2", "信息一点点累加，慢慢浮出可用的模式。", "beat-mark"),
        ("core-3", "同一张靶上，落点之间的距离开始收窄。", "beat-mark"),
    ],
    "closing": [
        ("close-1", "于是失败不再是判决，而是下一次的输入。", "beat-settle"),
        ("close-2", "行动越快，反馈就越清晰，调整也越准确。", "beat-hold"),
        ("close-3", "把试错成本压低，反馈周期自然就变短。", "beat-hold"),
    ],
}

_STAGE_BEATS = {
    "opening": [
        ("beat-open", "establish", ["player"], "建立持续投掷的人物"),
        ("beat-aim", "transform", ["dart", "target"], "把注意力移向落点与靶"),
    ],
    "core": [
        ("beat-adjust", "transform", ["player", "dart"], "记录修正方向"),
        ("beat-mark", "accumulate", ["target"], "同一张靶上累积落点"),
    ],
    "closing": [
        ("beat-settle", "restore", ["player"], "收束人物的行动"),
        ("beat-hold", "highlight", ["target"], "停在已经收窄的落点"),
    ],
}


def v4_storyboard() -> dict:
    """一份通过 v4 严格校验的最小分镜：三段各 400 帧，全片 40 秒。"""
    stages = []
    for stage_id, duration in (("opening", 400), ("core", 400), ("closing", 400)):
        stages.append({
            "id": stage_id,
            "durationInFrames": duration,
            "data": {"stageId": stage_id},
            "visualIntent": {
                "relation": "cause", "focus": "shape", "composition": "center",
                "density": "balanced", "tone": "neutral", "mode": "process",
                "claim": "低成本试错缩短反馈周期",
                "showWithoutText": "同一张靶上的落点逐步收窄",
                "primaryObject": "靶", "motionMeaning": "镜头停在落点上",
            },
            "beats": [
                {"id": beat_id, "action": action, "targets": targets, "meaning": meaning}
                for beat_id, action, targets, meaning in _STAGE_BEATS[stage_id]
            ],
            "narrationSegments": [
                {"id": segment_id, "text": text, "beatId": beat_id}
                for segment_id, text, beat_id in _STAGE_TEXT[stage_id]
            ],
        })
    return {
        "version": 4, "schemaVersion": 4, "directingVersion": 2,
        "fps": 30, "width": 1080, "height": 1920, "title": "测试视频",
        "visualDirection": {"motif": "落点收窄", "compositionBias": "centered",
                            "density": "balanced", "rhythm": "steady", "avoid": []},
        "directingBrief": {"thesis": "低成本试错缩短反馈周期", "audienceShift": "由害怕失败转向关注反馈",
                           "emotionalArc": ["犹豫", "观察", "确信"], "visualMotif": "同一张靶上的落点",
                           "stylePack": "editorial", "avoid": []},
        "visual": {"theme": "dark", "preset": "keynote"},
        "world": {
            "id": "test-world",
            "claim": "低成本试错缩短反馈周期",
            "metaphor": "人物在同一张靶上连续投掷",
            "data": {"headline": "快速反馈"},
            "renderer": {"kind": "tree"},
            "objects": [
                {"id": "player", "role": "primary", "description": "持续投掷的人物"},
                {"id": "dart", "role": "supporting", "description": "每次试错的飞镖"},
                {"id": "target", "role": "supporting", "description": "接受反馈的靶"},
            ],
            "sceneTree": {
                "id": "root", "type": "group",
                "children": [
                    {"id": "player", "type": "shape", "shape": "circle"},
                    {"id": "dart", "type": "shape", "shape": "line"},
                    {"id": "target", "type": "shape", "shape": "ring"},
                    {"id": "caption", "type": "text", "contentRef": "data.headline", "role": "headline"},
                ],
            },
            "stateTracks": [],
            "motions": [],
            "camera": {
                "shot": "medium", "composition": "center", "depth": "layered", "focus": "target",
                "segments": [
                    {"id": "cam-open", "kind": "hold", "focus": "player",
                     "binding": {"stageId": "opening", "phase": "establish"}},
                    {"id": "cam-core", "kind": "push-in", "focus": "target",
                     "binding": {"beatId": "beat-mark"}},
                    {"id": "cam-close", "kind": "settle", "focus": "target",
                     "binding": {"stageId": "closing", "phase": "settle"}},
                ],
            },
        },
        "stages": stages,
    }


@pytest.fixture
def valid_script_v4() -> dict:
    """v4 分镜夹具：按需局部改动，入口只接受这一版契约。"""
    return v4_storyboard()


def create_typed_project(directory: str | Path, video_type: str) -> Path:
    """按类型目录创建作品，替代测试里另写一份材料映射的旧用法。

    材料入口的唯一来源是 ``m2v.types.catalog``；测试也走同一条路径，因此目录里
    的文件名一旦变化，用例会跟着失败，而不是悄悄与实现错位。
    """
    from m2v.core.project import create_project
    from m2v.types import catalog

    return create_project(directory, video_type, catalog.catalog().get(video_type).material_map())


def register_synthetic_type(monkeypatch, name: str, description: str = "合成类型") -> None:
    """为测试用的合成类型补一份类型目录登记项。

    类型身份只在类型目录里维护，因此走统一入口的合成类型同样需要登记；这里只替换
    进程内缓存，不写仓库文件。
    """
    from m2v.types import catalog

    entry = catalog.Entry(
        name=name,
        description=description,
        summary=description,
        plan=description,
        skill_guide=description,
        materials=(
            catalog.Material(name="material", file="material.json", template={"schemaVersion": 1}),
        ),
    )
    current = catalog.catalog()
    monkeypatch.setattr(catalog, "_cached", catalog.Catalog(current.entries() + (entry,)))
