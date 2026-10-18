"""替代验收：覆盖、候选定位、缺声和失败处理，用小型真实媒体验证。"""
import subprocess
from pathlib import Path

import pytest
from imageio_ffmpeg import get_ffmpeg_exe
from m2v.core.errors import M2VError
from m2v.engine import qa_inspection as inspect
from m2v.engine import qa
from test_cinematic_media_checks import prepared_stub


def clip(path, *, silent=False, audio=True, seconds=2):
    args = [get_ffmpeg_exe(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
            f'color=c=black:s=192x108:r=60:d={seconds}']
    if audio:
        source = f'anullsrc=r=24000:cl=mono:d={seconds}' if silent else f'sine=frequency=440:sample_rate=24000:duration={seconds}'
        args.extend(['-f', 'lavfi', '-i', source])
    subprocess.run([*args, '-pix_fmt', 'yuv420p', str(path)], check=True)
    return path


def test_sampling_includes_short_last_frame_and_boundaries():
    p = prepared_stub(durationInFrames=7)
    assert inspect.sample_indices(p) == [0, 6]
    p = prepared_stub(durationInFrames=240)
    p['props']['compiledScenes'] = [{'id': 's', 'startFrame': 0, 'durationInFrames': 240,
        'content': {'props': {'shots': [
            {'id': 'one', 'startFrame': 0, 'endFrame': 120},
            {'id': 'two', 'startFrame': 120, 'endFrame': 240}]}}}]
    picks = inspect.sample_indices(p)
    assert {0, 60, 120, 180, 239}.issubset(picks)
    assert {90, 96, 102, 108, 114, 120, 126}.issubset(picks)
    assert picks == sorted(set(picks))
    assert max(picks) < 240


def test_long_sampling_covers_last_page_and_anomaly():
    p = prepared_stub(durationInFrames=36000)
    picks = inspect.sample_indices(p, [{'startSeconds': 598, 'endSeconds': 599}])
    assert picks[-1] == 35999
    assert len(picks) >= 600
    assert 35940 in picks and 35946 in picks


def test_hero_and_multiscene_offsets_are_sampled():
    p = prepared_stub(durationInFrames=180)
    p['props']['compiledScenes'] = [{'id': 'late', 'startFrame': 60, 'content': {'props': {'shots': [
        {'id': 'h', 'tier': 'hero', 'startFrame': 0, 'endFrame': 120}]}}}]
    assert 126 in inspect.sample_indices(p)


def test_multiscene_narration_windows_are_absolute_not_offset_twice():
    """segmentWindows 已是全片绝对帧号；QA 不能再叠一次幕起点。"""
    p = prepared_stub(durationInFrames=1200)
    p['props']['compiledScenes'] = [
        {'id': 'first', 'startFrame': 0,
         'narrationSegments': [{'id': 'a', 'text': '一'}],
         'segmentWindows': {'a': {'startFrame': 30, 'endFrame': 90}}},
        {'id': 'second', 'startFrame': 600,
         'narrationSegments': [{'id': 'b', 'text': '二'}],
         'segmentWindows': {'b': {'startFrame': 660, 'endFrame': 720}}},
    ]
    windows = inspect.narration_windows(p)
    assert windows == [
        {'id': 'a', 'startSeconds': 0.5, 'endSeconds': 1.5},
        {'id': 'b', 'startSeconds': 11.0, 'endSeconds': 12.0},
    ]


def test_black_and_silence_are_candidates_not_visual_failures(tmp_path):
    video = clip(tmp_path / 'black.mp4', silent=True)
    p = prepared_stub()
    p['props']['compiledScenes'] = [{'id': 's', 'startFrame': 0,
        'narrationSegments': [{'id': 's1', 'text': '旁白'}],
        'segmentWindows': {'s1': {'startFrame': 30, 'endFrame': 90}}}]
    visual = inspect.video_candidates(video, 2)
    assert visual['status'] == 'measured'
    assert visual['candidates'][0]['reason'] == 'black-frame'
    signal = inspect.audio_signals(video, p, required=True)
    assert signal['status'] == 'measured'
    assert signal['candidates'][0]['reason'] == 'silence'
    assert signal['candidates'][0]['narrationOverlap'] == ['s1']
    assert 1.9 <= signal['durationSeconds'] <= 2.1


def test_design_pause_is_a_candidate_without_new_export_gate(tmp_path):
    """正常设计停顿只登记候选：技术检查仍按既有门禁判定，不新增阻断。"""
    root = tmp_path / 'pause'
    (root / 'outputs/media').mkdir(parents=True)
    raw = tmp_path / 'raw.wav'
    subprocess.run([get_ffmpeg_exe(), '-y', '-v', 'error', '-f', 'lavfi', '-i',
                    'sine=frequency=440:duration=2', '-af',
                    'loudnorm=I=-16:TP=-1:LRA=11:linear=true', str(raw)], check=True)
    master = root / 'outputs/media/master.wav'
    # 0.55 秒静音为设计停顿，不在旁白窗口内。
    subprocess.run([get_ffmpeg_exe(), '-y', '-v', 'error', '-i', str(raw), '-af',
                    "volume=0:enable='between(t,0.6,1.15)'", str(master)], check=True)
    video = root / 'outputs/video.mp4'
    subprocess.run([get_ffmpeg_exe(), '-y', '-v', 'error', '-f', 'lavfi', '-i',
                    'testsrc=size=192x108:rate=60:duration=2', '-i', str(master),
                    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(video)], check=True)
    prepared = prepared_stub()
    prepared['props']['compiledScenes'] = [{'id': 's', 'startFrame': 0,
        'narrationSegments': [{'id': 'a', 'text': '开场'}],
        'segmentWindows': {'a': {'startFrame': 0, 'endFrame': 30}},
        'content': {'props': {'shots': [{'id': 'open', 'startFrame': 0, 'endFrame': 120}]}}}]
    report = qa.run(root, prepared, video=video, profile='standard', step=30)
    pause = [item for item in report['inspection']['audioSignals']['candidates']
             if item['reason'] == 'silence']
    assert pause and pause[0]['narrationOverlap'] == []
    assert report['status'] == 'pass'
    assert report['inspection']['reviewRequired'] is True
    assert report['inspection']['observation'] == 'not-evaluated'
    # 采样覆盖到片尾，分页清单与采样清单同时登记。
    assert report['inspection']['sequence']['lastFrame'] == 119
    assert report['inspection']['sequence']['pages'] == report['contactSheets']


def test_missing_optional_audio_is_not_applicable_but_required_audio_fails(tmp_path):
    video = clip(tmp_path / 'mute.mp4', audio=False)
    assert inspect.audio_signals(video, prepared_stub(), required=False)['status'] == 'not-applicable'
    with pytest.raises(M2VError, match='缺少音轨'):
        inspect.audio_signals(video, prepared_stub(), required=True)


def test_qa_supports_contractually_silent_video_without_master(tmp_path):
    root = tmp_path / 'mute'
    (root / 'outputs').mkdir(parents=True)
    video = clip(root / 'outputs/video.mp4', audio=False)
    report = qa.run(root, prepared_stub(audio={'segments': []}), video=video)
    assert report['checks']['loudness']['status'] == 'not-applicable'
    assert report['checks']['audioSync']['status'] == 'not-applicable'
    assert report['inspection']['sequence']['lastFrame'] == 119


def test_narration_outside_track_is_a_located_candidate(tmp_path):
    p = prepared_stub()
    p['props']['compiledScenes'] = [{'id': 's', 'startFrame': 0,
        'narrationSegments': [{'id': 's1', 'text': '结束'}],
        'segmentWindows': {'s1': {'startFrame': 100, 'endFrame': 180}}}]
    signal = inspect.audio_signals(clip(tmp_path / 'sound.mp4'), p, required=True)
    assert any(c['reason'] == 'narration-out-of-track' and c['endSeconds'] == 3
               for c in signal['candidates'])


def test_failed_detection_never_returns_empty_success(tmp_path):
    broken = tmp_path / 'broken.mp4'
    broken.write_bytes(b'broken')
    with pytest.raises(M2VError, match='检测失败'):
        inspect.video_candidates(broken, 2)


def test_pagination_preserves_all_samples(tmp_path):
    video = clip(tmp_path / 'pages.mp4', seconds=3)
    p = prepared_stub(durationInFrames=180)
    sequence = inspect.extract_sequence(video, p, tmp_path / 'qa',
        [{'startSeconds': 0, 'endSeconds': 3}])
    assert len(sequence['samples']) > 16 and len(sequence['pages']) >= 2
    assert sequence['samples'][-1]['frame'] == 179
    assert all((tmp_path / row['path']).is_file() for row in sequence['samples'])
    assert all((tmp_path / page).is_file() for page in sequence['pages'])


def test_sequence_accepts_relative_output_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    video = clip(Path('relative.mp4'), seconds=1)
    sequence = inspect.extract_sequence(video, prepared_stub(durationInFrames=60), Path('qa'))
    assert sequence['lastFrame'] == 59
    assert (tmp_path / sequence['pages'][0]).is_file()


def test_delivery_audio_clipping_candidate_is_located(tmp_path):
    video = tmp_path / 'loud.mkv'
    subprocess.run([get_ffmpeg_exe(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
                    'color=c=red:s=192x108:r=60:d=1', '-f', 'lavfi', '-i',
                    'aevalsrc=1:s=24000:d=1', '-c:a', 'pcm_f32le', str(video)], check=True)
    report = inspect.audio_signals(video, prepared_stub(durationInFrames=60), required=True)
    assert any(c['reason'] == 'clipping-candidate' and c['samples'] > 0 for c in report['candidates'])
