"""过程证据的最低媒体容量：只证明可探测与长度，不判断内容是否正确。

这些用例覆盖伪装视频、纯音频、过短片段、一帧容差与单次操作内的探测缓存；
真实表达是否成立仍由独立评审判断。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError
from m2v.production import media_evidence

pytestmark = pytest.mark.media


def make_video(path: Path, seconds: float, fps: int = 30, audio: float | None = None) -> Path:
    args = [get_ffmpeg_exe(), '-y', '-v', 'error', '-f', 'lavfi',
            '-i', f'testsrc=size=320x180:rate={fps}:duration={seconds}']
    if audio is not None:
        args += ['-f', 'lavfi', '-i', f'sine=frequency=440:duration={audio}', '-c:a', 'aac']
    args += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)]
    subprocess.run(args, check=True, timeout=300)
    return path


def make_audio_only(path: Path, seconds: float) -> Path:
    subprocess.run([get_ffmpeg_exe(), '-y', '-v', 'error', '-f', 'lavfi',
                    '-i', f'sine=frequency=440:duration={seconds}', '-c:a', 'aac', str(path)],
                   check=True, timeout=300)
    return path


def make_frames(path: Path, frames: int, fps: int = 30) -> Path:
    """按帧数而非秒数生成，用于验证「不足不超过一帧」的边界。"""
    subprocess.run([get_ffmpeg_exe(), '-y', '-v', 'error', '-f', 'lavfi',
                    '-i', f'testsrc=size=320x180:rate={fps}', '-frames:v', str(frames),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)], check=True, timeout=300)
    return path


def contract(fps: int = 30) -> dict:
    return {'fps': fps}


def coverage(name: str, window: list[int], checkpoint: str = 'one-cp') -> dict:
    return {'checkpointId': checkpoint, 'window': window,
            'evidence': [{'path': f'media/{name}', 'sha256': 'x'}]}


def test_probe_reads_only_the_video_stream(tmp_path: Path):
    # 音轨比视频长：容器时长不能冒充视频长度。
    path = make_video(tmp_path / 'long-audio.mp4', 1, audio=4)
    assert media_evidence.probe(path) == pytest.approx(1, abs=.05)


def test_probe_rejects_fake_audio_only_and_missing(tmp_path: Path):
    fake = tmp_path / 'fake.mp4'
    fake.write_bytes(b'not a video')
    with pytest.raises(M2VError, match='无法解码'):
        media_evidence.probe(fake)
    with pytest.raises(M2VError, match='缺少有效视频流'):
        media_evidence.probe(make_audio_only(tmp_path / 'audio.mp4', 2))
    with pytest.raises(M2VError):
        media_evidence.probe(tmp_path / 'missing.mp4')


def test_validate_requires_one_video_covering_the_window(tmp_path: Path):
    (tmp_path / 'media').mkdir()
    make_video(tmp_path / 'media/short.mp4', .5)
    c = contract()
    with pytest.raises(M2VError, match='检查窗需要'):
        media_evidence.validate([coverage('short.mp4', [0, 30])], c, tmp_path, {'one-cp'})
    # 多段短片段不能求和冒充完整过程。
    with pytest.raises(M2VError, match='检查窗需要'):
        media_evidence.validate([coverage('short.mp4', [0, 30])], c, tmp_path, {'one-cp'})
    with pytest.raises(M2VError, match='端点静帧不足'):
        media_evidence.validate([{'checkpointId': 'one-cp', 'window': [0, 30],
                                  'evidence': [{'path': 'media/shot.png', 'sha256': 'x'}]}], c, tmp_path, {'one-cp'})


def test_validate_allows_one_frame_tolerance_and_skips_other_checkpoints(tmp_path: Path):
    (tmp_path / 'media').mkdir()
    make_video(tmp_path / 'media/exact.mp4', 30 / 30 - 1 / 30 + .001)
    c = contract()
    media_evidence.validate([coverage('exact.mp4', [0, 30])], c, tmp_path, {'one-cp'})
    # 非动态核心检查点不探测视频，允许只有静帧。
    media_evidence.validate([{'checkpointId': 'two-cp', 'window': [0, 30],
                              'evidence': [{'path': 'media/shot.png', 'sha256': 'x'}]}], c, tmp_path, {'one-cp'})


def test_probe_is_cached_once_per_operation_including_failures(tmp_path: Path, monkeypatch):
    (tmp_path / 'media').mkdir()
    make_video(tmp_path / 'media/ok.mp4', 2)
    broken = tmp_path / 'media/broken.mp4'
    broken.write_bytes(b'not a video')
    calls = []
    original = media_evidence.probe
    monkeypatch.setattr(media_evidence, 'probe', lambda path: calls.append(path) or original(path))
    items = [coverage('ok.mp4', [0, 30]), coverage('ok.mp4', [0, 30])]
    with media_evidence.snapshot():
        media_evidence.validate(items, contract(), tmp_path, {'one-cp'})
        media_evidence.validate(items, contract(), tmp_path, {'one-cp'})
        for _ in range(2):
            with pytest.raises(M2VError):
                media_evidence.validate([coverage('broken.mp4', [0, 30])], contract(), tmp_path, {'one-cp'})
    assert sorted(path.name for path in calls) == ['broken.mp4', 'ok.mp4']
    # 下一次操作必须重验，不能跨查询缓存成功或失败。
    with media_evidence.snapshot():
        media_evidence.validate(items, contract(), tmp_path, {'one-cp'})
        with pytest.raises(M2VError):
            media_evidence.validate([coverage('broken.mp4', [0, 30])], contract(), tmp_path, {'one-cp'})
    assert len(calls) == 4


def test_status_rejects_invalid_process_evidence_without_rewriting_history(tmp_path: Path):
    """历史报告摘要仍匹配、但视频不可探测或过短时，当前制作完成必须为 false。"""
    import json
    from m2v.core.delivery import outputs
    from m2v.production import ledger, contract, checks
    from m2v.production.storage import locked, receipt
    from helpers.production import sample

    root = tmp_path / 'work'
    root.mkdir()
    c = sample()
    c['reviewPlan']['risks'] = [{'id': 'e', 'kind': 'core-event', 'scope': {'checkpointIds': ['one-cp']},
                                 'reason': '过程关系未验证', 'requiredEvidence': ['完整动态窗口']}]
    (root / 'DESIGN.md').write_text('```m2v-checkpoints\n' + json.dumps(c) + '\n```\n', encoding='utf-8')
    (root / 'scenes').mkdir()
    for scene in c['scenes']:
        (root / 'scenes' / (scene['id'] + '.tsx')).write_text('export default 1;', encoding='utf-8')
    (root / 'storyboard.json').write_text(json.dumps({'width': 1920, 'height': 1080, 'fps': 30, 'scenes': [
        {'id': s['id'], 'durationFrames': 30, 'content': {'entry': f'scenes/{s["id"]}.tsx'}} for s in c['scenes']]}),
        encoding='utf-8')
    out = outputs(root)
    out.mkdir()
    (out / 'visual-notes.md').write_text('```m2v-issues\n[]\n```\n', encoding='utf-8')
    (out / 'production').mkdir()
    (out / 'production/comparisons.json').write_text('[]', encoding='utf-8')
    manifest = {'id': 'work', 'type': 'general'}
    with locked(root):
        path = checks.save_report(root, c, 'G4', [{'name': '测量', 'status': 'pass', 'detail': 'fixture'}],
                                  scene_id='one', checkpoint_id='one-cp')
        event = ledger.register(root, manifest, path)
        video = out / 'production/frames/clip.mp4'
        video.parent.mkdir(parents=True, exist_ok=True)
        make_video(video, .5)
        ledger.append(root, manifest, 'review', gate='G4', scene_id='one', checkpoint_id='one-cp',
                      upstream=event['upstream'], evidence=[receipt(out, video)],
                      data={'checkId': event['id'], 'reviewerId': 'R1', 'reviewType': 'blind', 'verdict': 'pass',
                            'focus': 'comprehensive', 'isolation': 'independent-subagent',
                            'coverage': [{'checkpointId': 'one-cp', 'window': [0, 30], 'status': 'pass',
                                          'observations': '片段可见变化',
                                          'evidence': [receipt(out, video)], 'issues': [],
                                          'assessment': {name: {'status': 'pass', 'observations': 'ok'}
                                                         for name in ('understanding', 'presentation',
                                                                      'representativeness')}}]})
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file() and p.name != '.lock'}
    row = ledger.status(root, manifest)['scenes'][0]
    assert row['evidenceStatus'] == '待评审'
    assert any('动态过程证据无效' in item for item in row['missingAcceptance'])
    assert before == {p: p.read_bytes() for p in root.rglob('*') if p.is_file() and p.name != '.lock'}


def test_probe_ignores_leading_pts_offset(tmp_path: Path):
    """视频前的音轨偏移不能把 1 秒画面垫成 5 秒。"""
    (tmp_path / 'media').mkdir()
    shifted = tmp_path / 'media/shifted.mp4'
    subprocess.run([get_ffmpeg_exe(), '-y', '-v', 'error',
                    '-itsoffset', '4', '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=30:duration=1',
                    '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
                    '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', str(shifted)], check=True, timeout=300)
    assert media_evidence.probe(shifted) == pytest.approx(1, abs=.05)
    with pytest.raises(M2VError, match='检查窗需要'):
        media_evidence.validate([coverage('shifted.mp4', [0, 150])], contract(), tmp_path, {'one-cp'})


@pytest.mark.parametrize('fps', [30, 60])
def test_one_frame_short_still_passes(tmp_path: Path, fps):
    """「时长不足不超过一帧」通过，微秒截断不得把边界误判为失败。"""
    (tmp_path / 'media').mkdir()
    make_frames(tmp_path / 'media/short.mp4', fps - 1, fps)
    media_evidence.validate([coverage('short.mp4', [0, fps])], contract(fps), tmp_path, {'one-cp'})
    make_frames(tmp_path / 'media/shorter.mp4', fps - 2, fps)
    with pytest.raises(M2VError, match='检查窗需要'):
        media_evidence.validate([coverage('shorter.mp4', [0, fps])], contract(fps), tmp_path, {'one-cp'})


@pytest.mark.parametrize('window', [[0], None, 'ab', [5, 1], [0, 'x'], [0, 30, 60]])
def test_malformed_window_is_a_diagnosis_not_a_crash(tmp_path: Path, window):
    """畸形覆盖记录必须转成可读诊断；状态查询不能因此崩溃。"""
    (tmp_path / 'media').mkdir()
    make_video(tmp_path / 'media/ok.mp4', 2)
    item = {'checkpointId': 'one-cp', 'window': window, 'evidence': [{'path': 'media/ok.mp4', 'sha256': 'x'}]}
    with pytest.raises(M2VError, match='过程证据记录无效|检查窗需要'):
        media_evidence.validate([item], contract(), tmp_path, {'one-cp'})


def test_failure_cache_reports_from_each_call_site(tmp_path: Path):
    """缓存的失败以原因复用：每次重新构造异常，不把同一实例抛出两次。"""
    (tmp_path / 'media').mkdir()
    broken = tmp_path / 'media/broken.mp4'
    broken.write_bytes(b'not a video')
    raised = []
    with media_evidence.snapshot():
        for _ in range(2):
            with pytest.raises(M2VError) as info:
                media_evidence.duration(broken)
            raised.append(info.value)
    assert raised[0] is not raised[1]
    assert str(raised[0]) == str(raised[1])


def test_valid_pass_is_not_reported_as_invalid_alongside_it(tmp_path: Path):
    """存在有效通过时不再罗列无效证据，避免状态同时声明完成与证据无效。"""
    import json
    from m2v.core.delivery import outputs
    from m2v.production import ledger, checks
    from m2v.production.storage import locked, receipt
    from helpers.production import sample

    root = tmp_path / 'work'
    root.mkdir()
    c = sample()
    c['reviewPlan']['risks'] = [{'id': 'e', 'kind': 'core-event', 'scope': {'checkpointIds': ['one-cp']},
                                 'reason': '过程关系未验证', 'requiredEvidence': ['完整动态窗口']}]
    (root / 'DESIGN.md').write_text('```m2v-checkpoints\n' + json.dumps(c) + '\n```\n', encoding='utf-8')
    (root / 'scenes').mkdir()
    for scene in c['scenes']:
        (root / 'scenes' / (scene['id'] + '.tsx')).write_text('export default 1;', encoding='utf-8')
    (root / 'storyboard.json').write_text(json.dumps({'width': 1920, 'height': 1080, 'fps': 30, 'scenes': [
        {'id': s['id'], 'durationFrames': 30, 'content': {'entry': f'scenes/{s["id"]}.tsx'}} for s in c['scenes']]}),
        encoding='utf-8')
    out = outputs(root)
    out.mkdir()
    (out / 'visual-notes.md').write_text('```m2v-issues\n[]\n```\n', encoding='utf-8')
    (out / 'production').mkdir()
    (out / 'production/comparisons.json').write_text('[]', encoding='utf-8')
    manifest = {'id': 'work', 'type': 'general'}

    def append_review(event, video, reviewer):
        ledger.append(root, manifest, 'review', gate='G4', scene_id='one', checkpoint_id='one-cp',
                      upstream=event['upstream'], evidence=[receipt(out, video)],
                      data={'checkId': event['id'], 'reviewerId': reviewer, 'reviewType': 'blind',
                            'verdict': 'pass', 'focus': 'comprehensive', 'isolation': 'independent-subagent',
                            'coverage': [{'checkpointId': 'one-cp', 'window': [0, 30], 'status': 'pass',
                                          'observations': '片段可见变化',
                                          'evidence': [receipt(out, video)], 'issues': [],
                                          'assessment': {name: {'status': 'pass', 'observations': 'ok'}
                                                         for name in ('understanding', 'presentation',
                                                                      'representativeness')}}]})

    with locked(root):
        path = checks.save_report(root, c, 'G4', [{'name': '测量', 'status': 'pass', 'detail': 'fixture'}],
                                  scene_id='one', checkpoint_id='one-cp')
        event = ledger.register(root, manifest, path)
        frames = out / 'production/frames'
        frames.mkdir(parents=True, exist_ok=True)
        short, full = frames / 'short.mp4', frames / 'full.mp4'
        make_video(short, .5)
        make_video(full, 1)
        append_review(event, short, 'R1')
        append_review(event, full, 'R2')
        row = ledger.status(root, manifest)['scenes'][0]

    assert row['evidenceStatus'] == '通过'
    assert not any('动态过程证据无效' in item for item in row['missingAcceptance'])
