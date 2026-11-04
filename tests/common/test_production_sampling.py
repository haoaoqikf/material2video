"""采样负载、短暂状态和原生/派生证据的行为回归。"""
from PIL import Image
import pytest

from m2v.production.evidence_images import derive_images
from m2v.production.sampling import sample_frames, sampling_step
from m2v.production.checks import event_coverage


def point(**kwargs):
    return {'frame': 150, 'window': [0, 300], 'textPlan': [], **kwargs}


def test_default_reduces_ordinary_window_but_keeps_unknown_dynamics_dense():
    cp = point()
    frames = sample_frames(cp, {})
    assert len(frames) <= 23 and {0, 150, 299} <= set(frames)
    assert len(sample_frames(cp, {}, dynamic=True)) == 300
    assert sampling_step(point(minEventFrames=90)) == 15
    assert sampling_step(point(minEventFrames=3)) == 3
    assert sampling_step(point(minEventFrames=3), dynamic=True) == 3
    assert sampling_step(point(sampleStep=8, minEventFrames=3)) == 8  # 由密度检查保持未验证


@pytest.mark.parametrize('fps', [24, 30, 60])
def test_event_text_state_and_time_boundaries_survive_coarse_defaults(fps):
    cp = point(textPlan=[{'window': [7, 8]}], statePlan=[{'window': [52, 55]}])
    shot = {'timeStructure': {'reveal': {'window': [101, 103]}, 'pause': {'window': None}}}
    frames = sample_frames(cp, shot, fps=fps, event_frames=[0, 222, 299, 999])
    assert {0, 1, 6, 7, 8, 9, 51, 52, 53, 54, 55, 56, 100, 101, 102, 103, 104, 221, 222, 223, 298, 299} <= set(frames)
    assert frames == sorted(set(frames)) and min(frames) == 0 and max(frames) == 299


def test_event_diagnostic_records_effective_step():
    result = event_coverage({'props': {'resolvedEvents': [{'id': 'pulse', 'sceneId': 'a', 'frame': 7}]}},
                            {'id': 'a'}, point(), [6, 7, 8], step=15)
    assert result['sampleStep'] == 15 and not result['missedFrames']


def test_image_derivation_keeps_native_bytes_and_transparency(tmp_path, monkeypatch):
    source = tmp_path / 'source.png'
    Image.new('RGBA', (192, 108), (120, 80, 40, 100)).save(source)
    native, phone, medium = (tmp_path / name for name in ('native.png', 'phone.png', 'medium.png'))
    # No subprocess can be used for picture derivation.
    monkeypatch.setattr('subprocess.run', lambda *a, **k: pytest.fail('逐图启动子进程'))
    derive_images(source, {192: native, 39: phone, 85: medium})
    assert native.read_bytes() == source.read_bytes()
    with Image.open(phone) as image:
        assert image.size == (39, 22) and image.mode == 'RGBA'
        assert image.getpixel((10, 10))[3] == 100
    with Image.open(medium) as image:
        assert image.size == (85, 48)


def test_capture_receipt_reuses_bounded_windows_write_retry(tmp_path, monkeypatch):
    from m2v.core import delivery
    from m2v.production.storage import read
    from m2v.types.general.code_scenes.capture import _clip_receipt
    original = delivery._write_json
    calls, waits = [], []
    def busy_twice(path, value):
        calls.append(path)
        if len(calls) <= 2:
            raise PermissionError('短暂文件占用')
        original(path, value)
    monkeypatch.setattr(delivery, '_write_json', busy_twice)
    monkeypatch.setattr(delivery.time, 'sleep', waits.append)
    video = tmp_path / 'window.mp4'
    video.write_bytes(b'fixture')
    _clip_receipt(video, 0, 30, extra={'verified': True})
    assert len(calls) == 3 and waits == [.05, .1]
    assert read(video.with_suffix('.json'))['verified']
