"""双来源音效、动作同步和立体声闭环；网络由传输夹具隔离。"""
from array import array
import json
import math
import shutil
import struct
import time
import wave

import pytest

from m2v.cli import main
from m2v.core.errors import M2VError
from m2v.core.project import load_current_prepared
from m2v.engine import audio
from m2v.engine.sound import asset_digest
from m2v.types.general import adapter, explainer, sound_library as library, sound_synthesis as synth
from _helpers import board, fake_record, project, scene_root

pytestmark = pytest.mark.media


def write_tone(path, seconds, frequency=220):
    with wave.open(str(path), "wb") as out:
        out.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        out.writeframes(b"".join(struct.pack("<h", round(6000 * math.sin(math.tau*frequency*i/24000)))
                                 for i in range(round(seconds*24000))))
    return path


def manifest(*entries):
    return {"schemaVersion": 1, "assets": list(entries)}


def generated(identity="keys", name="keyboard-typing", **params):
    return {"id": identity, "synthesis": {"name": name, "seed": 42, **params}}


def imported(path, **extra):
    return {"id": "real-key", "localPath": str(path), "sourceUrl": "https://example.org/sound/1",
            "author": "测试作者", "license": "CC0-1.0", **extra}


def pcm(path):
    with wave.open(str(path), "rb") as stream:
        params = (stream.getnchannels(), stream.getframerate(), stream.getnframes())
        samples = array("h", stream.readframes(stream.getnframes()))
    return params, samples


def energy(samples):
    return sum(s*s for s in samples) / max(1, len(samples))


def test_catalog_and_synthesis_are_distinct_reproducible_and_bounded(tmp_path):
    digests = set()
    for row in synth.catalog():
        a, b = tmp_path / "a.wav", tmp_path / "b.wav"
        value = {"name": row["name"], "seed": 7}
        assert synth.synthesize(value, a) == synth.synthesize(value, b)
        assert a.read_bytes() == b.read_bytes()
        (_, rate, count), values = pcm(a)
        assert rate == 24000 and count == row["durationMs"] * 24
        assert energy(values) > 1000 and max(abs(v) for v in values) < 32767
        digests.add(asset_digest(a))
    assert len(digests) == len(synth.CATALOG)
    started = time.perf_counter()
    synth.synthesize({"name": "electric-crackle", "durationMs": 10000}, tmp_path / "long.wav")
    assert time.perf_counter() - started < 5


def test_seed_and_explicit_key_events(tmp_path):
    first, second = tmp_path / "a.wav", tmp_path / "b.wav"
    synth.synthesize({"name": "keyboard-typing", "durationMs": 1000, "eventsMs": [100, 500]}, first)
    synth.synthesize({"name": "keyboard-typing", "durationMs": 1000, "eventsMs": [100, 500], "seed": 1}, second)
    assert asset_digest(first) != asset_digest(second)
    _, samples = pcm(first)
    assert not any(samples[:2400])
    assert energy(samples[2400:4000]) > 1000
    assert not any(samples[8000:12000])
    assert energy(samples[12000:13600]) > 1000


def test_hum_loop_has_no_discontinuous_seam(tmp_path):
    synth.synthesize({"name": "electric-hum", "durationMs": 1703}, tmp_path / "hum.wav")
    _, samples = pcm(tmp_path / "hum.wav")
    assert abs(samples[0]-samples[-1]) <= max(abs(b-a) for a, b in zip(samples, samples[1:]))


@pytest.mark.parametrize("value", [
    {"name": "none"}, {"name": "spark", "durationMs": 30001},
    {"name": "spark", "seed": True}, {"name": "spark", "intensity": float("nan")},
    {"name": "spark", "eventsMs": [1]},
    {"name": "keyboard-typing", "eventsMs": [20, 10]},
    {"name": "keyboard-typing", "eventsMs": [10, 10]},
])
def test_invalid_recipe(value):
    with pytest.raises(M2VError):
        synth.recipe(value)


def test_dual_source_import_and_audit(tmp_path):
    source = write_tone(tmp_path / "original.wav", .5)
    record = library.import_assets(tmp_path, manifest(generated(), imported(source)), base=tmp_path)
    assets, inputs = library.resolve(tmp_path)
    assert set(assets) == {"keys", "real-key"}
    assert assets["real-key"]["channels"] == 2
    assert assets["real-key"]["originalSha256"] == asset_digest(source)
    assert assets["keys"]["synthesis"]["version"] == synth.VERSION
    assert inputs["file:" + library.RECORD] == asset_digest(tmp_path / library.RECORD)
    assert len(inputs) == 3
    assert record == library.load_record(tmp_path)


def test_remote_import_uses_transport_and_records_source(tmp_path):
    source = write_tone(tmp_path / "remote.wav", .3)
    class Transport:
        def download(self, url, destination, headers, timeout_s):
            assert url == "https://example.org/key.wav"
            shutil.copyfile(source, destination)
    entry = imported(source)
    del entry["localPath"]
    entry["mediaUrl"] = "https://example.org/key.wav"
    library.import_assets(tmp_path, manifest(entry), base=tmp_path, transport=Transport())
    assets, _ = library.resolve(tmp_path)
    assert assets["real-key"]["mediaUrl"] == entry["mediaUrl"]


@pytest.mark.parametrize("failure", ["license", "sourceUrl", "broken", "duplicate", "empty"])
def test_failed_batch_preserves_existing_record_and_files(tmp_path, failure):
    library.import_assets(tmp_path, manifest(generated()), base=tmp_path)
    prior = (tmp_path / library.RECORD).read_bytes()
    before = sorted(p.name for p in (tmp_path / library.DIRECTORY).iterdir())
    source = write_tone(tmp_path / "original.wav", .1)
    entry = imported(source)
    if failure in {"license", "sourceUrl"}:
        entry[failure] = "未知"
    elif failure == "broken":
        source.write_bytes(b"not audio")
    elif failure == "empty":
        source.write_bytes(b"")
    else:
        entry = generated("new")
    with pytest.raises(M2VError):
        library.import_assets(tmp_path, manifest(generated("new"), entry), base=tmp_path)
    assert (tmp_path / library.RECORD).read_bytes() == prior
    assert sorted(p.name for p in (tmp_path / library.DIRECTORY).iterdir()) == before


@pytest.mark.parametrize("field,value", [("path", "../bad.wav"), ("license", "unknown"), ("frames", 1)])
def test_audit_rejects_bad_records(tmp_path, field, value):
    data = library.import_assets(tmp_path, manifest(generated()), base=tmp_path)
    data["assets"][0][field] = value
    (tmp_path / library.RECORD).write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(M2VError):
        library.resolve(tmp_path)


def test_cli_catalog_import_audit(tmp_path, capsys):
    root, _ = project(tmp_path)
    file = tmp_path / "sound.json"
    file.write_text(json.dumps(manifest(generated())), encoding="utf-8")
    assert main(["general", "sounds", "catalog"]) == 0
    assert "keyboard-typing" in capsys.readouterr().out
    assert main(["general", "sounds", "import", "--project", str(root), "--manifest", str(file)]) == 0
    assert main(["general", "sounds", "audit", "--project", str(root)]) == 0


@pytest.mark.parametrize("extra", [
    {"offsetFrames": 1, "offsetMs": 1}, {"offsetFrames": 1, "segmentId": "a-line"},
    {"offsetFrames": .5}, {"pan": 2}, {"loop": True}, {"durationMs": 0},
    {"fadeInMs": -1}, {"trimStartMs": True}, {"loop": "true"},
])
def test_playback_control_validation(tmp_path, extra):
    data = board()
    data["soundtrack"] = {"effects": [{"builtin": "click", "sceneId": "a", **extra}]}
    with pytest.raises(M2VError):
        explainer.validate(data, scene_root(tmp_path))


@pytest.mark.parametrize("fps", [30, 60])
def test_no_narration_prepare_sync_pan_and_fingerprint(tmp_path, monkeypatch, fps):
    data = board(fps=fps)
    root, project_data = project(tmp_path, data)
    library.import_assets(root, manifest(generated("spark", "spark")), base=root)
    data["scenes"][0]["narrationSegments"] = []
    data["scenes"][0]["durationFrames"] = 2*fps
    data["soundtrack"] = {"effects": [{"assetId": "spark", "sceneId": "a", "offsetFrames": fps//2,
        "trimStartMs": 10, "durationMs": 400, "fadeOutMs": 40, "pan": 1}]}
    (root / "storyboard.json").write_text(json.dumps(data), encoding="utf-8")
    fake_record(monkeypatch)
    result = adapter.prepare(root, project_data)
    file = root / result["audio"]["segments"][0]["path"]
    (channels, rate, count), samples = pcm(file)
    assert channels == 2 and count == result["durationInFrames"] * rate // fps
    # 半秒处开始；允许滤波器边界数个样本的误差。
    assert energy(samples[1:round(.48*rate)*2:2]) == 0
    left = energy(samples[round(.51*rate)*2:round(.85*rate)*2:2])
    right = energy(samples[round(.51*rate)*2+1:round(.85*rate)*2:2])
    assert right > 1000 and left < right * .001
    assert energy(samples[round(.95*rate)*2:]) == 0
    assert "file:" + library.RECORD in result["inputs"]
    library.import_assets(root, manifest(generated("extra", "mouse-click")), base=root)
    with pytest.raises(M2VError, match="文件已变化"):
        load_current_prepared(root, project_data)


def test_trim_loop_fades_and_stereo_master(tmp_path):
    source = write_tone(tmp_path / "tone.wav", .4)
    # 前 .1 秒静音，裁掉后再循环不应重新出现这段静音。
    with wave.open(str(source), "rb") as stream:
        payload = stream.readframes(stream.getnframes())
    with wave.open(str(source), "wb") as stream:
        stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        stream.writeframes(b"\0" * 4800 + payload[4800:])
    silent = write_tone(tmp_path / "silence.wav", 2, 0)
    output = tmp_path / "mixed.wav"
    effect = audio.Effect(source, .25, -12, .1, 1.2, True, .05, .1, -1)
    audio.mix(silent, output, 2, [], None, [effect], tmp_path)
    (channels, rate, count), samples = pcm(output)
    assert channels == 2 and count == 48000
    assert not any(samples[:round(.25*rate)*2])
    assert energy(samples[round(.6*rate)*2:round(.8*rate)*2:2]) > 1000
    assert not any(samples[1::2])
    assert not any(samples[round(1.5*rate)*2:])
    mastered = tmp_path / "mastered.wav"
    audio.master(output, mastered)
    assert pcm(mastered)[0][0] == 2
    assert not any(pcm(mastered)[1][1::2])


def test_soundtrack_envelope_uses_video_frames_and_smooth_silence(tmp_path):
    output = tmp_path / "gain.wav"
    audio.soundtrack_envelope([], 2, 30, output,
        {"curve": "linear", "keyframes": [{"frame": 0, "gainDb": -20},
            {"frame": 30, "gainDb": 0}, {"frame": 60, "gainDb": -20}]})
    (channels, rate, count), samples = pcm(output)
    assert channels == 1 and rate == 24000 and count == 48000
    assert samples[0] == pytest.approx(3277, abs=1)
    assert samples[15*800] == pytest.approx(10362, abs=5)
    assert samples[30*800] == pytest.approx(32767, abs=1)

    audio.soundtrack_envelope([], 2, 30, output, silence=[
        {"startFrame": 10, "endFrame": 50, "fadeFrames": 5}])
    (_, _, count), samples = pcm(output)
    assert count == 48000
    assert samples[10*800] > 32000
    assert samples[12*800] < samples[10*800]
    assert samples[16*800] == 0
    assert samples[30*800] == 0
    assert samples[48*800] < samples[50*800]
    assert samples[50*800] > 32000

    audio.soundtrack_envelope([{"start": .5, "end": 1.}], 2, 30, output,
        {"curve": "linear", "keyframes": [{"frame": 0, "gainDb": -6},
            {"frame": 60, "gainDb": -6}]})
    (_, _, _), samples = pcm(output)
    assert samples[15*800] == pytest.approx(32767 * 10**(-16/20), abs=2)
    assert samples[40*800] == pytest.approx(32767 * 10**(-6/20), abs=2)


def test_soundtrack_envelope_and_silence_apply_to_mixed_effect_and_music(tmp_path):
    narration = write_tone(tmp_path / "voice.wav", 2, 0)
    music = write_tone(tmp_path / "bed.wav", 1, 400)
    effect = write_tone(tmp_path / "effect.wav", .3, 900)
    output = tmp_path / "mix.wav"
    automation = [{"track": "music", "keyframes": [
        {"frame": 0, "gainDb": 0}, {"frame": 60, "gainDb": -12}]},
        {"track": "effects", "keyframes": [
        {"frame": 0, "gainDb": -12}, {"frame": 60, "gainDb": 0}]}]
    audio.mix(narration, output, 2, [], (music, {"gainDb": 0, "loop": True,
        "fadeInMs": 0, "fadeOutMs": 0}), [audio.Effect(effect, 0, 0, 0, 2, True),
        audio.Effect(effect, .2, -3, 0, 1.8, True)], tmp_path,
        fps=30, envelopes=automation, silence=[{"startFrame": 15, "endFrame": 30, "fadeFrames": 3}])
    (channels, rate, count), samples = pcm(output)
    assert channels == 2 and count == 48000
    # 留静窗口中只有音乐和效果音被静音，旁白仍是独立的声音层。
    assert not any(samples[round(.7*rate)*2:round(.8*rate)*2])
    assert energy(samples[round(1.2*rate)*2:round(1.4*rate)*2:2]) > 1000
    mastered = tmp_path / "mastered.wav"
    audio.master(output, mastered)
    (channels, rate, count), final_samples = pcm(mastered)
    assert channels == 2 and count == 48000
    assert not any(final_samples[round(.7*rate)*2:round(.8*rate)*2])
    stats = audio.loudness(mastered)
    assert -15 <= float(stats["input_i"]) <= -13
    assert float(stats["input_tp"]) <= -1


@pytest.mark.parametrize("envelope", [
    {"track": "music", "keyframes": [{"frame": 2, "gainDb": 0}, {"frame": 1, "gainDb": -20}]},
    {"track": "music", "keyframes": [{"frame": 0, "gainDb": 0}, {"frame": 0, "gainDb": -20}]},
    {"track": "music", "keyframes": [{"frame": 0, "gainDb": 5}, {"frame": 1, "gainDb": -20}]},
    {"track": "unknown", "keyframes": [{"frame": 0, "gainDb": 0}, {"frame": 1, "gainDb": -20}]},
])
def test_soundtrack_envelope_validation_rejects_bad_targets_and_order(tmp_path, envelope):
    data = board()
    data["soundtrack"] = {"music": {"sourceRef": "assets/bed.wav"}, "envelopes": [envelope]}
    (tmp_path / "assets").mkdir(exist_ok=True)
    write_tone(tmp_path / "assets" / "bed.wav", 1)
    with pytest.raises(M2VError):
        explainer.validate(data, scene_root(tmp_path))


def test_soundtrack_automation_requires_a_matching_track_and_nonoverlapping_silences(tmp_path):
    data = board()
    data["soundtrack"] = {"envelopes": [{"track": "effects", "keyframes": [
        {"frame": 0, "gainDb": 0}, {"frame": 30, "gainDb": -12}]}]}
    with pytest.raises(M2VError, match="effects 包络需要"):
        explainer.validate(data, scene_root(tmp_path))
    data["soundtrack"] = {"silence": [
        {"startFrame": 0, "endFrame": 30, "fadeFrames": 2},
        {"startFrame": 20, "endFrame": 40, "fadeFrames": 2}],
        "music": {"sourceRef": "assets/bed.wav"}}
    (tmp_path / "assets").mkdir(exist_ok=True)
    write_tone(tmp_path / "assets" / "bed.wav", 1)
    with pytest.raises(M2VError, match="互不重叠"):
        explainer.validate(data, scene_root(tmp_path))
    data["soundtrack"] = {"silence": [{"startFrame": 0, "endFrame": 30, "fadeFrames": 16}]}
    with pytest.raises(M2VError, match="需要 music 或 effects"):
        explainer.validate(data, scene_root(tmp_path))


@pytest.mark.parametrize("extra,match", [
    ({"trimStartMs": 650}, "trimStartMs"),
    ({"durationMs": 651}, "durationMs"),
    ({"durationMs": 100, "fadeOutMs": 101}, "fadeOutMs"),
    ({"offsetFrames": -1}, "起点越界"),
    ({"offsetFrames": 120}, "起点越界"),
])
def test_prepare_rejects_source_and_timeline_boundaries(tmp_path, monkeypatch, extra, match):
    root, project_data = project(tmp_path)
    library.import_assets(root, manifest(generated("spark", "spark")), base=root)
    data = board()
    data["scenes"][0].update(narrationSegments=[], durationFrames=120)
    data["soundtrack"] = {"effects": [{"assetId": "spark", "sceneId": "a", **extra}]}
    (root / "storyboard.json").write_text(json.dumps(data), encoding="utf-8")
    fake_record(monkeypatch)
    with pytest.raises(M2VError, match=match):
        adapter.prepare(root, project_data)


def test_audit_checks_unused_sound_and_truncated_wav(tmp_path):
    data = library.import_assets(tmp_path, manifest(generated()), base=tmp_path)
    file = tmp_path / data["assets"][0]["path"]
    file.write_bytes(file.read_bytes()[:-10])
    with pytest.raises(M2VError, match="摘要变化"):
        explainer.validate(board(), scene_root(tmp_path))
    with pytest.raises(M2VError, match="截断"):
        library.probe(file)


def test_third_party_duration_limit_is_not_silent_truncation(tmp_path, monkeypatch):
    source = write_tone(tmp_path / "source.wav", .1)
    original = library.decode
    def overlong(source, target):
        original(source, target)
        # 稀疏数据会被逐块读取，测试不分配整段 PCM。
        with wave.open(str(target), "wb") as out:
            out.setparams((2, 2, 24000, 0, "NONE", "not compressed"))
            for _ in range(601):
                out.writeframesraw(bytes(24000*4))
        return library.probe(target)
    monkeypatch.setattr(library, "decode", overlong)
    with pytest.raises(M2VError, match="600 秒"):
        library.import_assets(tmp_path, manifest(imported(source)), base=tmp_path)
    assert not (tmp_path / library.RECORD).exists()


def test_default_playback_preserves_third_party_stereo(tmp_path):
    source = tmp_path / "stereo.wav"
    with wave.open(str(source), "wb") as out:
        out.setparams((2, 2, 24000, 0, "NONE", "not compressed"))
        out.writeframes(b"".join(struct.pack("<hh", 0, round(6000*math.sin(math.tau*440*i/24000))) for i in range(24000)))
    silent = write_tone(tmp_path / "silent.wav", 2, 0)
    output = tmp_path / "mixed.wav"
    audio.mix(silent, output, 2, [], None, [audio.Effect(source, 0, -12, 0, 1)], tmp_path)
    _, samples = pcm(output)
    assert not any(samples[::2]) and energy(samples[1::2]) > 1000


def test_example_exercise_recipe_is_importable(tmp_path):
    from _helpers import ROOT
    file = ROOT / "styles/doc-archive/examples/american-science-milestones/assets/sound-exercise.json"
    data = json.loads(file.read_text(encoding="utf-8"))
    library.import_assets(tmp_path, data, base=file.parent)
    assets, _ = library.resolve(tmp_path)
    assert set(assets) == {"typing-demo", "spark-demo"}


def test_first_import_invalidates_prepared_absence(tmp_path, monkeypatch):
    root, project_data = project(tmp_path)
    data = board()
    data["scenes"][0].update(narrationSegments=[], durationFrames=120)
    (root / "storyboard.json").write_text(json.dumps(data), encoding="utf-8")
    fake_record(monkeypatch)
    result = adapter.prepare(root, project_data)
    assert result["inputs"]["absent-file:" + library.RECORD] == "absent"
    load_current_prepared(root, project_data)
    library.import_assets(root, manifest(generated()), base=root)
    with pytest.raises(M2VError, match="文件已变化"):
        load_current_prepared(root, project_data)


def test_publication_failure_rolls_back_new_files(tmp_path, monkeypatch):
    library.import_assets(tmp_path, manifest(generated()), base=tmp_path)
    prior = (tmp_path / library.RECORD).read_bytes()
    before = sorted(p.name for p in (tmp_path / library.DIRECTORY).iterdir())
    def fail(*_):
        raise OSError("模拟磁盘写入失败")
    monkeypatch.setattr(library, "_write_json", fail)
    with pytest.raises(OSError):
        library.import_assets(tmp_path, manifest(generated("spark", "spark")), base=tmp_path)
    assert (tmp_path / library.RECORD).read_bytes() == prior
    assert sorted(p.name for p in (tmp_path / library.DIRECTORY).iterdir()) == before


def test_final_aac_delivery_preserves_pan(tmp_path):
    source = write_tone(tmp_path / "tone.wav", 1)
    silent = write_tone(tmp_path / "silent.wav", 2, 0)
    mixed, master = tmp_path / "mixed.wav", tmp_path / "master.wav"
    audio.mix(silent, mixed, 2, [], None, [audio.Effect(source, .5, -12, 0, 1, pan=1)], tmp_path)
    audio.master(mixed, master)
    video, delivery = tmp_path / "silent.mp4", tmp_path / "delivery.mp4"
    audio.ffmpeg(["-f", "lavfi", "-i", "color=c=black:s=64x64:r=30:d=2", "-an",
                  "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)])
    audio.mux(video, master, delivery, 2)
    decoded = tmp_path / "delivered.wav"
    library.decode(delivery, decoded)
    (channels, _, _), samples = pcm(decoded)
    assert channels == 2
    assert energy(samples[1::2]) > 1000 * max(1, energy(samples[::2]))
