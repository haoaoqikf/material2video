"""管理工具不把退出码或自报路径当作有效产物。"""
import hashlib
import json
from pathlib import Path

import pytest

from m2v.core.errors import M2VError
from m2v.standalone import executor


@pytest.fixture
def work(tmp_path):
    (tmp_path / 'run.py').write_text('pass', encoding='utf-8')
    return tmp_path, {'runtime': {'version': 1, 'command': ['python', 'run.py']}}


def reply(monkeypatch, result, *, action='render', code=0, duplicate=False):
    result.setdefault('environment', {'platform': 'test-runner'})
    def execute(argv, root, **options):
        payload = executor.PREFIX + json.dumps({'version': 1, 'command': action, 'result': result})
        options['on_line'](payload)
        if duplicate:
            options['on_line'](payload)
        return code
    monkeypatch.setattr(executor, 'run', execute)


def artifact(root, path='outputs/video.mp4'):
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(b'actual-bytes')
    return {'status': 'candidate', 'path': path, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}


def test_actual_local_artifact_is_rechecked(work, monkeypatch):
    root, project = work
    result = artifact(root)
    reply(monkeypatch, result)
    assert executor.execute(root, project, 'render') == result
    (root / result['path']).write_bytes(b'replaced')
    with pytest.raises(M2VError, match='摘要'):
        executor.execute(root, project, 'render')


@pytest.mark.parametrize('change,match', [({'path': '../external.mp4'}, '路径'),
    ({'path': '/external.mp4'}, '路径'), ({'path': 'missing.mp4'}, '缺失'),
    ({'status': 'failed'}, '状态'), ({'status': []}, '状态'), ({'sha256': 'bad'}, '摘要')])
def test_false_results_are_rejected(work, monkeypatch, change, match):
    root, project = work
    result = {**artifact(root), **change}
    reply(monkeypatch, result)
    with pytest.raises(M2VError, match=match):
        executor.execute(root, project, 'render')


def test_duplicate_result_cannot_hide_failed_or_ambiguous_work(work, monkeypatch):
    root, project = work
    reply(monkeypatch, artifact(root), duplicate=True)
    with pytest.raises(M2VError, match='唯一'):
        executor.execute(root, project, 'render')


def test_qa_status_must_agree_with_exit_and_report(work, monkeypatch):
    root, project = work
    result = {**artifact(root, 'outputs/qa.json'), 'status': 'fail'}
    reply(monkeypatch, result, action='qa', code=0)
    with pytest.raises(M2VError, match='退出码'):
        executor.execute(root, project, 'qa')
    reply(monkeypatch, result, action='qa', code=1)
    assert executor.execute(root, project, 'qa')['status'] == 'fail'


def test_protocol_command_identity_is_checked(work, monkeypatch):
    root, project = work
    reply(monkeypatch, artifact(root), action='preview')
    with pytest.raises(M2VError, match='结构'):
        executor.execute(root, project, 'render')


@pytest.mark.parametrize('action,status', [('prepare', 'prepared'), ('inspect', 'current')])
def test_prepared_is_reused_within_one_management_call(work, monkeypatch, action, status):
    root, project = work
    result = {**artifact(root, 'outputs/prepared.json'), 'status': status, 'preparedFingerprint': 'current'}
    reply(monkeypatch, result, action=action)
    reads = []
    prepared = {'preparedFingerprint': 'current'}
    def read(*args):
        reads.append(args)
        return prepared
    monkeypatch.setattr(executor, 'load_current_prepared', read)
    value = executor.prepare(root, project, []) if action == 'prepare' else executor.current(root, project)
    assert value is prepared
    assert len(reads) == 1
