"""独立化后源码边界与候选搬移，不借真实整片测试简单存储规则。"""
import json
from pathlib import Path
import shutil

import pytest

from film_runtime.core import delivery
from film_runtime.core.errors import VideoError
from film_runtime.types.scene_film.code_scenes.capture import _assert_pure_sources


@pytest.mark.parametrize('suffix', ['.ts', '.mjs', '.cjs'])
def test_pure_time_checks_adopted_source_but_not_control_clock_or_vendor(tmp_path, suffix):
    root = tmp_path / 'project'
    host = root / 'src/code-scene/host.tsx'
    vendor = root / 'node_modules/react/runtime.js'
    scene = root / 'scenes/demo.tsx'
    helper = root / ('components/helper' + suffix)
    for file in [host, vendor, scene, helper]:
        file.parent.mkdir(parents=True, exist_ok=True)
    host.write_text('setTimeout(controlClock, 1)', encoding='utf-8')
    vendor.write_text('Math.random()', encoding='utf-8')
    scene.write_text('export default () => null', encoding='utf-8')
    helper.write_text('export const random = Math.random()', encoding='utf-8')
    work = tmp_path / 'work'
    work.mkdir()
    (work / 'inputs.json').write_text(json.dumps([str(p) for p in [host, vendor, scene]]), encoding='utf-8')
    _assert_pure_sources(root, work)
    (work / 'inputs.json').write_text(json.dumps([str(p) for p in [host, vendor, scene, helper]]), encoding='utf-8')
    with pytest.raises(VideoError, match='helper' + suffix):
        _assert_pure_sources(root, work)


def test_candidate_survives_move_and_never_reads_original_project(tmp_path):
    original = tmp_path / 'original'
    destination = original / 'outputs/video.mp4'
    binding = {'preparedFingerprint': 'same-inputs', 'type': 'text-motion'}
    calls = []
    def generate(path):
        calls.append(path)
        path.write_bytes(b'candidate-bytes')
    delivery.export_once(destination, binding, generate, lambda path: None, lambda: binding)
    record = delivery.read_record(original / 'outputs')
    assert not Path(record['path']).is_absolute()
    moved = tmp_path / 'moved folder'
    shutil.copytree(original, moved)
    shutil.rmtree(original)
    # 原目录完全不存在仍能取回候选；不能靠原绝对路径或重新生成通过。
    def unexpected(path):
        raise AssertionError('moved candidate must be reused')
    delivery.export_once(moved / 'outputs/video.mp4', binding, unexpected, lambda path: None, lambda: binding)
    assert len(calls) == 1
    assert delivery.candidate(moved, binding)['sha256'] == delivery.digest(moved / 'outputs/video.mp4')


@pytest.mark.parametrize('path', ['../outside.mp4', 'absolute', ''])
def test_candidate_path_cannot_leave_project(tmp_path, path):
    reference = str(tmp_path.parent / 'outside.mp4') if path == 'absolute' else path
    with pytest.raises(VideoError, match='路径'):
        delivery._local_path(tmp_path, reference)
