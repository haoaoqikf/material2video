"""cinematic 的 QA 与资产审计：用自造的小媒体验证判定逻辑。"""
import hashlib
import json
import subprocess

import pytest
from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError
from m2v.engine import assets_audit, qa
from m2v.types.general.explainer_render import visual_provenance


def make_video(path, *, seconds=2, fps=60, pattern="testsrc", size="192x104"):
    subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"{pattern}=size={size}:rate={fps}:duration={seconds}",
                    "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
                    "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def make_audio(path, *, seconds=2, frequency=440):
    subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"sine=frequency={frequency}:duration={seconds}",
                    "-af", "loudnorm=I=-16:TP=-1:LRA=11:linear=true", str(path)], check=True)
    return path


def prepared_stub(**overrides):
    prepared = {"preparedFingerprint": "x" * 8, "fps": 60, "durationInFrames": 120,
                "props": {"subtitle": {"textColor": "#ffffff", "plateColor": "#0b0d12"},
                          "compiledScenes": []},
                "audio": {"segments": [{"path": "outputs/media/master.wav"}]}}
    prepared.update(overrides)
    return prepared


def test_subtitle_contrast_flags_low_contrast():
    assert qa.subtitle_contrast({"textColor": "#ffffff", "plateColor": "#0b0d12"})["status"] == "pass"
    weak = qa.subtitle_contrast({"textColor": "#ffffff", "plateColor": "#f0f0f0"})
    assert weak["status"] == "fail" and weak["ratio"] < 4.5


def test_subtitle_contrast_rejects_bad_color():
    with pytest.raises(M2VError):
        qa.subtitle_contrast({"textColor": "white", "plateColor": "#000000"})


def test_frozen_frames_detects_still_run():
    still = [bytes([10] * (192 * 104))] * 8
    report = qa.frozen_frames(still, 60, 30)
    assert report["status"] == "fail" and report["longestStillSeconds"] > 3
    moving = [bytes([(index * 40) % 255] * (192 * 104)) for index in range(8)]
    assert qa.frozen_frames(moving, 60, 30)["status"] == "pass"


def test_picture_metrics_report_dark_levels():
    flat = [bytes([5] * (192 * 104)) for _ in range(2)]
    metrics = qa.picture_metrics(flat)
    assert metrics["darkLevels"]["max"] == 1 and metrics["darkMaxStep"] == 0


def test_claims_require_covering_shot():
    scene = {"id": "home", "narrationSegments": [{"id": "home-0", "text": "地球", "claims": ["夜面灯光"]}],
             "segmentWindows": {"home-0": {"startFrame": 120, "endFrame": 480}},
             "content": {"props": {"shots": [{"id": "earth", "tier": "hero", "target": "earth",
                                              "startFrame": 120, "endFrame": 480}]}}}
    report = qa.claims_check({"props": {"compiledScenes": [scene]}})
    assert report["status"] == "pass" and report["segments"][0]["shots"] == ["earth"]
    # 即使目标朝向或画面未知，也只承诺时间窗覆盖，不能冒充可见性验收。
    assert report["scope"] == "shot-window-coverage"
    assert report["visibility"] == "not-evaluated"
    scene["content"]["props"]["shots"] = []
    assert qa.claims_check({"props": {"compiledScenes": [scene]}})["status"] == "fail"


def test_sample_frames_and_contact_sheet(tmp_path):
    video = make_video(tmp_path / "clip.mp4")
    frames = qa.sample_frames(video, 60, 30)
    assert len(frames) == 4 and all(len(frame) == 192 * 104 for frame in frames)
    sheet = qa.contact_sheet(video, tmp_path / "sheet.png", columns=2, rows=2, every=1)
    assert sheet.is_file() and sheet.stat().st_size > 0


def test_loudness_and_audio_sync_on_generated_media(tmp_path):
    video = make_video(tmp_path / "clip.mp4")
    audio = make_audio(tmp_path / "master.wav")
    report = qa.loudness(audio)
    assert -18 <= report["integratedLufs"] <= -14 and report["truePeakDbfs"] <= -1
    sync = qa.audio_sync(video, audio, 2.0)
    assert sync["status"] == "pass"
    assert qa.audio_sync(video, make_audio(tmp_path / "short.wav", seconds=1), 2.0)["status"] == "fail"


def test_qa_run_writes_report(tmp_path):
    root = tmp_path / "work"
    (root / "outputs/media").mkdir(parents=True)
    video = make_video(root / "outputs/video.mp4")
    make_audio(root / "outputs/media/master.wav")
    report = qa.run(root, prepared_stub(), video=video, step=30)
    assert (root / "outputs/qa.json").is_file()
    assert report["status"] in {"pass", "fail"} and "frozenFrames" in report["checks"]
    assert report["scope"] == "technical-only"
    assert report["observation"]["status"] == "not-evaluated"
    assert report["checks"]["picture"]["kind"] == "measurement"
    assert "status" not in report["checks"]["picture"]
    assert report["checks"]["audioSync"]["scope"] == "track-duration-difference"


def test_qa_writes_report_to_example_content_root(tmp_path):
    root = tmp_path / "examples" / "clip"
    base = tmp_path / "videos/examples/clip/outputs"
    (base / "media").mkdir(parents=True)
    video = make_video(base / "video.mp4")
    make_audio(base / "media/master.wav")
    qa.run(root, prepared_stub(), video=video, step=30)
    assert (base / "qa.json").is_file()
    assert not (root / "outputs/qa.json").exists()


def test_qa_records_report_digest_in_delivery_sidecar(tmp_path):
    root = tmp_path / "work"
    (root / "outputs/media").mkdir(parents=True)
    video = make_video(root / "outputs/video.mp4")
    make_audio(root / "outputs/media/master.wav")
    sidecar = root / "outputs/video.provenance.json"
    sidecar.write_text(json.dumps({"schemaVersion": 1, "productionProfile": "cinematic"}),
                       encoding="utf-8")
    qa.run(root, prepared_stub(), video=video, step=30)
    saved = json.loads(sidecar.read_text(encoding="utf-8"))
    digest = hashlib.sha256((root / "outputs/qa.json").read_bytes()).hexdigest()
    assert saved["qa"] == {"report": "outputs/qa.json", "sha256": digest}


def test_assets_audit_does_not_impose_surface_map_or_4k_quotas(tmp_path):
    root = tmp_path / "work"
    (root / "assets/media").mkdir(parents=True)
    png = root / "assets/media/color.png"
    subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                    "-i", "color=c=red:size=64x32", "-frames:v", "1", str(png)], check=True)
    record = {"schemaVersion": 1, "assets": [
        {"id": "earth", "path": "assets/media/color.png", "kind": "image", "width": 2048, "height": 1024,
         "durationSeconds": None, "sha256": "x", "license": "CC BY 4.0"},
        {"id": "rings", "path": "assets/media/color.png", "kind": "image", "width": 2048, "height": 125,
         "durationSeconds": None, "sha256": "x", "license": "CC BY 4.0", "role": "ring"},
    ]}
    prepared = prepared_stub()
    prepared["props"]["compiledScenes"] = [{"id": "s", "narrationSegments": [], "segmentWindows": {},
                                            "content": {"props": {"shots": [
                                                {"id": "earth", "tier": "hero", "target": "earth",
                                                 "startFrame": 0, "endFrame": 480}]}}}]
    report = assets_audit.audit(root, prepared, record)
    reasons = " ".join(item["reason"] for item in report["problems"])
    assert report["status"] == "pass"
    assert not reasons and report["resolutionScope"].endswith("not-evaluated")
    assert assets_audit.audit(root, prepared, record)["status"] == "pass"
    assert (root / "outputs/asset-audit.json").is_file()


def test_assets_audit_reports_alpha_and_colour_space(tmp_path):
    root = tmp_path / "work"
    (root / "assets/media").mkdir(parents=True)
    png = root / "assets/media/ring.png"
    subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                    "-i", "color=c=red@0.5:size=64x32", "-frames:v", "1", "-pix_fmt", "rgba", str(png)], check=True)
    info = assets_audit.describe(png)
    assert info["alpha"] is True and info["colorSpace"] == "srgb"


def test_media_resolution_reports_colour_space_alpha_and_license(tmp_path):
    """作品拿到的素材信息包含实测色彩空间、alpha 与登记许可，且不需要重新导入。"""
    from _helpers import project
    from test_article_media import entry, importer, make_image
    from m2v.types.general import media_assets

    root, _manifest = project(tmp_path)
    make_image(root / "assets/incoming.png")
    importer(root, [entry("photo", "image", localPath="assets/incoming.png",
                          sourceUrl="https://example.com/a", author="作者甲", license="CC0")])
    resolved = media_assets.resolve(root)["media"]["photo"]
    assert resolved["colorSpace"] in {"srgb", "unknown"}
    assert isinstance(resolved["alpha"], bool)
    assert resolved["license"] == "CC0"


def test_media_resolution_rejects_unknown_license(tmp_path):
    from _helpers import project
    from test_article_media import entry, importer, make_image
    from m2v.types.general import media_assets

    root, _manifest = project(tmp_path)
    make_image(root / "assets/incoming.png")
    importer(root, [entry("photo", "image", localPath="assets/incoming.png")])
    with pytest.raises(M2VError, match="许可未知"):
        media_assets.resolve(root)


def test_lookdev_has_no_approval_gate():
    """look-dev 只产出检查产物：模块不再暴露确认符号。"""
    from m2v.engine import lookdev
    for name in ("approve", "require_approval", "approval_path", "APPROVAL_FILE"):
        assert not hasattr(lookdev, name), f"lookdev 不应再提供 {name}"


def test_lookdev_cli_rejects_removed_approve_flag(tmp_path):
    """旧命令行必须显式失败，而不是被静默忽略。"""
    from m2v import cli
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["lookdev", "--project", str(tmp_path), "--approve", "--note", "已观看"])
    assert excinfo.value.code == 2


def test_qa_frozen_problem_points_to_shot_and_time(tmp_path):
    root = tmp_path / "work"
    (root / "outputs/media").mkdir(parents=True)
    video = root / "outputs/video.mp4"
    subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                    "-i", "color=c=black:size=192x104:rate=60:duration=4",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
                    "-pix_fmt", "yuv420p", str(video)], check=True)
    make_audio(root / "outputs/media/master.wav", seconds=4)
    prepared = prepared_stub(durationInFrames=240)
    prepared["props"]["compiledScenes"] = [{"id": "s", "startFrame": 0, "narrationSegments": [],
                                            "segmentWindows": {}, "content": {"props": {"shots": [
                                                {"id": "earth", "tier": "hero", "target": "earth",
                                                 "startFrame": 0, "endFrame": 240}]}}}]
    report = qa.run(root, prepared, video=video, step=30)
    problem = report["checks"]["frozenFrames"]["problem"]
    assert problem["shot"] == "earth" and problem["startSeconds"] == 0


def test_normalize_reaches_cinematic_loudness(tmp_path):
    from m2v.engine import audio
    source = make_audio(tmp_path / "quiet.wav", seconds=3)
    target = tmp_path / "master.wav"
    audio.normalize(source, target, integrated=-14.0, true_peak=-1.0)
    report = qa.loudness(target)
    assert report["status"] == "pass" and abs(report["integratedLufs"] + 14) <= 1.0


def test_master_hits_cinematic_loudness_and_peak(tmp_path):
    from m2v.engine import audio
    source = make_audio(tmp_path / "quiet.wav", seconds=3)
    target = tmp_path / "cinematic-master.wav"
    audio.master(source, target, integrated=-14.0, true_peak=-1.0)
    report = qa.loudness(target)
    assert report["status"] == "pass" and abs(report["integratedLufs"] + 14) <= 1.0
    assert report["truePeakDbfs"] <= -1.0


def test_assets_audit_json_round_trip(tmp_path):
    root = tmp_path / "work"
    (root / "assets/media").mkdir(parents=True)
    png = root / "assets/media/color.png"
    subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                    "-i", "color=c=blue:size=64x32", "-frames:v", "1", str(png)], check=True)
    record = {"schemaVersion": 1, "assets": [
        {"id": "sun", "path": "assets/media/color.png", "kind": "image", "width": 4096, "height": 2048,
         "durationSeconds": None, "sha256": "x", "license": "未知"}]}
    prepared = prepared_stub()
    prepared["props"]["compiledScenes"] = [{"id": "s", "narrationSegments": [], "segmentWindows": {},
                                            "content": {"props": {"shots": [
                                                {"id": "sun", "tier": "hero", "target": "sun",
                                                 "startFrame": 0, "endFrame": 480}]}}}]
    report = assets_audit.audit(root, prepared, record)
    saved = json.loads((root / "outputs/asset-audit.json").read_text(encoding="utf-8"))
    assert saved["status"] == report["status"] == "fail"
    assert any("许可未知" in item["reason"] for item in report["problems"])


def test_2d_hero_does_not_require_fabricated_surface_maps(tmp_path):
    prepared = prepared_stub()
    prepared["props"]["compiledScenes"] = [{"content": {"props": {"shots": [
        {"id": "flight", "target": "archive", "tier": "hero"}]}}}]
    subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi", "-i",
                    "color=gray:s=1280x720", "-frames:v", "1", str(tmp_path / "archive.png")], check=True)
    record = {"assets": [{"id": "archive", "role": "other", "path": "archive.png",
                           "width": 1280, "height": 720, "license": "Public domain"}]}
    report = assets_audit.audit(tmp_path, prepared, record)
    assert report["status"] == "pass"
    assert any("不冒充4K" in warning["reason"] for warning in report["warnings"])
    record["assets"][0]["license"] = "未知"
    assert assets_audit.audit(tmp_path, prepared, record)["status"] == "fail"


def test_2d_media_is_audited_even_when_color_map_exists(tmp_path):
    """同一目标另有三维颜色贴图时，二维档案的许可仍必须单独审计。"""
    prepared = prepared_stub()
    prepared["props"]["compiledScenes"] = [{"content": {"props": {"shots": [
        {"id": "flight", "target": "archive", "tier": "hero"}]}}}]
    subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi", "-i",
                    "color=gray:s=4200x4200", "-frames:v", "1", str(tmp_path / "color.png")], check=True)
    subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi", "-i",
                    "color=gray:s=1280x720", "-frames:v", "1", str(tmp_path / "archive.png")], check=True)
    record = {"assets": [
        {"id": "color", "role": "color", "target": "archive", "path": "color.png",
         "width": 4200, "height": 4200, "license": "Public domain"},
        {"id": "photo", "role": "other", "target": "archive", "path": "archive.png",
         "width": 1280, "height": 720, "license": "未知"},
    ]}
    report = assets_audit.audit(tmp_path, prepared, record)
    assert report["status"] == "fail"
    assert any(item.get("asset") == "photo" and "许可未知" in item["reason"]
               for item in report["problems"])


def test_visual_provenance_covers_every_scene():
    """多幕作品逐幕记录镜头与 look，帧号换算成全片帧号。"""
    prepared = {"props": {"compiledScenes": [
        {"id": "a", "startFrame": 0, "content": {"props": {
            "look": {"grain": 0.1},
            "shots": [{"id": "a1", "tier": "major", "target": "t",
                       "startFrame": 0, "endFrame": 10, "post": {}}]}}},
        {"id": "b", "startFrame": 100, "content": {"props": {
            "look": {"grain": 0.2},
            "shots": [{"id": "b1", "tier": "hero", "target": "u",
                       "startFrame": 5, "endFrame": 20, "post": {"bloom": 1}}]}}},
    ]}}
    result = visual_provenance(prepared)
    assert [shot["id"] for shot in result["shots"]] == ["a1", "b1"]
    assert (result["shots"][1]["startFrame"], result["shots"][1]["endFrame"]) == (105, 120)
    assert result["shots"][1]["sceneId"] == "b"
    assert result["look"] == {"a": {"grain": 0.1}, "b": {"grain": 0.2}}
    assert result["postFx"]["shots"]["b1"] == {"bloom": 1}


@pytest.mark.parametrize("silent", [True, False])
def test_silent_film_requires_exact_zero_signal(tmp_path, silent):
    video = tmp_path / "video.mp4"
    subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi", "-i",
                    "testsrc=size=192x104:rate=60:duration=2", "-f", "lavfi", "-i",
                    "anullsrc=r=24000:cl=mono" if silent else "sine=frequency=440:sample_rate=24000",
                    "-t", "2", "-pix_fmt", "yuv420p", str(video)], check=True)
    prepared = prepared_stub()
    prepared["props"]["compiledScenes"] = [{"id": "silent", "startFrame": 0, "endFrame": 120,
        "durationInFrames": 120, "narrationSegments": [], "segmentWindows": {}}]
    report = qa.run(tmp_path, prepared, video=video, step=30)
    check = report["checks"]["loudness"]
    assert check["status"] == ("pass" if silent else "fail")
    assert (check["peakAbsolute"] == 0) == silent
    if silent:
        # 显式声明空 soundtrack 仍是无声设计，不能因此退回响度目标。
        prepared["props"]["soundtrack"] = {"effects": []}
        report = qa.run(tmp_path, prepared, video=video, step=30)
        assert report["checks"]["loudness"]["status"] == "pass"
