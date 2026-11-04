"""通用双帧率：配置、时间账本、缓存与真实逐帧运动。"""
from __future__ import annotations

import copy
import json
import subprocess
import time
import wave

import pytest
from imageio_ffmpeg import get_ffmpeg_exe
from playwright.sync_api import sync_playwright

from m2v.cli import main
from m2v.core.errors import M2VError
from m2v.core.project import load_current_prepared, load_project, save_prepared
from m2v.core.video_config import general_fps
from m2v.core import frames
from m2v.engine import lookdev
from m2v.types.general import adapter, code_scenes, explainer, reading_pace, soundtrack
from helpers.general import board, fake_record, fake_tts, project, scene, scene_root
from helpers.general import prepare_build, requires_node



@pytest.mark.parametrize("output,story,expected", [
    ({}, {}, 30), ({"fps": 30}, {}, 30), ({"fps": 60}, {}, 60),
    ({}, {"fps": 30}, 30), ({}, {"fps": 60}, 60),
    ({"fps": 30}, {"fps": 30}, 30), ({"fps": 60}, {"fps": 60}, 60),
])
def test_declarations(output, story, expected):
    assert general_fps({"output": output}, story) == expected


@pytest.mark.parametrize("value", [True, False, 30.0, 60.0, 25, 120, 0, None, "30"])
@pytest.mark.parametrize("where", ["project", "storyboard"])
def test_invalid_declarations(value, where):
    manifest = {"output": {"fps": value}} if where == "project" else {}
    data = {"fps": value} if where == "storyboard" else {}
    with pytest.raises(M2VError, match="整数30或60"):
        general_fps(manifest, data)


def test_conflict():
    with pytest.raises(M2VError, match="必须一致"):
        general_fps({"output": {"fps": 30}}, {"fps": 60})


@pytest.mark.parametrize("kind,expected,bad", [
    ("general", 30, None), ("financial-timeseries", 30, 60), ("driving-route", 30, 60)])
def test_init_type_defaults(tmp_path, kind, expected, bad):
    root = tmp_path / kind
    assert main(["init", "--type", kind, "--project", str(root)]) == 0
    _, manifest = load_project(root)
    assert manifest["output"]["fps"] == expected
    if kind == "general":
        assert json.loads((root / "storyboard.json").read_text(encoding="utf-8"))["fps"] == 30
    else:
        manifest["output"]["fps"] = bad
        (root / "project.json").write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(M2VError, match=f"必须为 {expected}"):
            load_project(root)


@pytest.mark.media
@pytest.mark.parametrize("fps", [30, 60])
def test_timeline_audio_cues_and_seconds(tmp_path, monkeypatch, fps):
    first = scene(leadInFrames=fps, tailFrames=fps // 2,
                  narrationSegments=[{"id": "a1", "text": "观察结果。", "holdFrames": fps // 2},
                                     {"id": "a2", "text": "继续改进。"}])
    second = scene("b", transition="crossfade")
    data = board(fps=fps, scenes=[first, second])
    root, manifest = project(tmp_path, data)
    fake_tts(monkeypatch)
    fake_record(monkeypatch)
    prepared = adapter.prepare(root, manifest)
    assert prepared["fps"] == prepared["props"]["fps"] == fps
    a, b = prepared["props"]["compiledScenes"]
    assert a["segmentWindows"] == {"a1": {"startFrame": fps, "endFrame": 2 * fps},
                                    "a2": {"startFrame": 5 * fps // 2, "endFrame": 7 * fps // 2}}
    assert a["durationInFrames"] == round(4.4 * fps)
    assert b["transitionFrames"] == round(8 / 30 * fps)
    assert prepared["durationInFrames"] == round(5.8 * fps)
    assert prepared["subtitles"][0]["startFrame"] == fps
    assert reading_pace.report(prepared)["cues"][0]["seconds"] == 1
    with wave.open(str(root / prepared["audio"]["segments"][0]["path"]), "rb") as audio:
        assert audio.getnframes() / audio.getframerate() == pytest.approx(5.8, abs=1 / fps)
    assert lookdev.sample_window(prepared, seconds=1) == (0, fps - 1)


@pytest.mark.parametrize("fps", [30, 60])
def test_frame_limits_preserve_seconds(tmp_path, fps):
    data = board(fps=fps, scenes=[scene(leadInFrames=30 * fps, tailFrames=30 * fps,
                                      readingHoldFrames=6 * fps, durationFrames=600 * fps)])
    root = scene_root(tmp_path)
    explainer.validate(data, root)
    for field in ("leadInFrames", "tailFrames", "readingHoldFrames", "durationFrames"):
        bad = copy.deepcopy(data)
        bad["scenes"][0][field] += 1
        with pytest.raises(M2VError, match=field):
            explainer.validate(bad, root)
    data["scenes"][0]["content"]["props"]["shots"] = [{"id": "shot", "target": "main", "tier": "major",
        "startFrame": 0, "endFrame": 600 * fps + 1}]
    with pytest.raises(M2VError, match="endFrame"):
        explainer.validate(data, root)


@pytest.mark.parametrize("fps", [30, 60])
def test_soundtrack_offsets_use_actual_fps(tmp_path, monkeypatch, fps):
    observed = []
    monkeypatch.setattr(soundtrack.audio, "mix", lambda *args, **kwargs: observed.append((args, kwargs)))
    source = {"fps": fps, "soundtrack": {"effects": [{"builtin": "click", "sceneId": "a",
              "segmentId": "line", "offsetMs": 250}]}}
    compiled = [{"id": "a", "startFrame": fps, "segmentWindows": {"line": {"startFrame": 2 * fps}}}]
    soundtrack.mix(tmp_path, source, compiled, tmp_path / "raw.wav", tmp_path / "mix.wav",
                   [{"startFrame": 2 * fps, "endFrame": 3 * fps}], 4, tmp_path, {})
    assert observed[0][0][3] == [{"start": 2, "end": 3}]
    assert observed[0][0][5][0].start == 2.25
    assert observed[0][1]["fps"] == fps


def test_prepared_invalid_after_frame_rate_change(tmp_path):
    root, manifest = project(tmp_path, board(fps=60))
    save_prepared(root, project=manifest, composition_id="ArticleExplainer", props={}, width=1920, height=1080,
                  fps=60, duration_in_frames=60, inputs={})
    manifest["output"]["fps"] = 30
    data = board(fps=30)
    (root / "storyboard.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(M2VError, match="帧率.*重新 prepare"):
        load_current_prepared(root, manifest)


MOTION = """
import {useEffect} from 'react';
import {useSceneContext} from 'm2v/code-scene';
export default function Demo() {
  const {ready, elapsedSeconds} = useSceneContext();
  useEffect(() => {ready();}, []);
  return <div style={{width:320,height:240,background:'#000',position:'relative'}}>
    <div style={{position:'absolute',left:20+elapsedSeconds*120,top:100,width:20,height:20,background:'#fff'}}/>
  </div>;
}
"""


@requires_node
@pytest.mark.slow
def test_real_capture_encode_motion_and_cache(tmp_path, chromium_ready, capsys):
    """一秒短片：全帧运动、共同时间点画面一致、同fps复用缓存及跨fps隔离。"""
    root, work, built = prepare_build(tmp_path, MOTION)
    assert built.returncode == 0, built.stderr
    target = {"id": "a", "startFrame": 0, "endFrame": 60, "durationInFrames": 60,
              "segmentWindows": {}, "content": {"entry": "scenes/demo.tsx", "props": {}}}
    frame = {"width": 320, "height": 240, "subtitle": {"safeArea": {"x": 0, "y": 200, "width": 320, "height": 40}}}
    shared = {}
    reports = []
    with sync_playwright() as pw:
        for fps in (30, 60):
            directory = tmp_path / f"capture-{fps}"
            directory.mkdir()
            (directory / "scene.js").write_bytes((work / "scene.js").read_bytes())
            target["durationInFrames"] = fps
            config = code_scenes.scene_config(target, frame, {}, fps=fps)
            start = time.monotonic()
            code_scenes._capture(pw, root, directory, config)
            capture_seconds = time.monotonic() - start
            pictures = [(directory / f"frame-{n:06d}.png").read_bytes() for n in range(fps)]
            assert len(set(pictures)) == fps, "连续移动主体不应有重复采集帧"
            shared[fps] = pictures
            video = directory / "clip.mp4"
            code_scenes._encode(directory, video, fps, 320, 240, fps=fps)
            decoded = subprocess.run([get_ffmpeg_exe(), "-v", "error", "-i", str(video),
                "-f", "framehash", "-"], capture_output=True, text=True, check=True).stdout
            hashes = [line.rsplit(",", 1)[-1].strip() for line in decoded.splitlines() if line and not line.startswith("#")]
            assert len(hashes) == len(set(hashes)) == fps
            assert f"#tb 0: 1/{fps}" in decoded
            reports.append({"fps": fps, "frames": len(hashes), "seconds": 1, "captureSeconds": round(capture_seconds, 3)})
    assert shared[30] == shared[60][::2], "相同时间点画面应相同，不能改变运动速度"
    # 同一作品同一帧预算，只改变fps也必须改变缓存路径。
    target["durationInFrames"] = 4
    paths = [code_scenes.capture.record(root, target, {}, frame=frame, media={}, media_digest="empty", fps=fps)
             for fps in (30, 60, 30)]
    assert paths[0] == paths[2] and paths[0] != paths[1]
    report = tmp_path / "frame-rate-benchmark.json"
    report.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    with capsys.disabled():
        print("\n双帧率逐帧采集量测：", json.dumps(reports), "报告：", report)
