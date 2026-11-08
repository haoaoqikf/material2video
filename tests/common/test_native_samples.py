"""原生采集与交付分离；模拟编码只用于证据/门禁边界，真实采集另有媒体节点。"""
from pathlib import Path
import os

import pytest
from PIL import Image

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from m2v.core.project import create_project, load_project
from m2v.production import dependencies, issues, ledger, media_evidence, reviews, samples
from m2v.production.storage import read, write
from common.test_media_reviews import report


@pytest.fixture
def native(tmp_path, monkeypatch):
    root = tmp_path / 'work'
    create_project(root, 'text-motion', {'storyboard': 'storyboard.json'})
    project = load_project(root)[1]
    (root / 'scenes').mkdir(exist_ok=True)
    (root / 'scenes/main.tsx').write_text('export default 1;', encoding='utf-8')

    def render(root, project, stage, **options):
        Image.new('RGB', (640, 360), 'blue').save(stage / 'still-000001.png')
        (stage / 'sample.mp4').write_bytes(b'test-encoded-video')
        (stage / 'web').mkdir()
        (stage / 'web/index.html').write_text('native fixture', encoding='utf-8')
        return dict(entry='scenes/main.tsx', props={}, fps=30, width=640, height=360,
                    durationInFrames=3, stills=[dict(frame=1, path='still-000001.png')], video='sample.mp4',
                    inputs={**samples.design_sample.source_binding(root, 'scenes/main.tsx', {})['files'],
                            'work/project.json': dependencies.digest(root / 'project.json')},
                    config={'media': {}, 'props': {}}, determinism=[], project={k: project.get(k) for k in ('id', 'type', 'output')})

    def media_copy(args):
        target = Path(args[-1])
        if target.suffix == '.png':
            for n in range(1, 4) if '%' in target.name else [0]:
                name = target.with_name(target.name % n) if n else target
                Image.new('RGB', (640, 360), 'blue').save(name)
        else:
            target.write_bytes(b'test-review-clip')

    monkeypatch.setattr(samples.design_sample, 'render', render)
    monkeypatch.setattr(reviews, 'ffmpeg', media_copy)
    monkeypatch.setattr(media_evidence, 'duration', lambda path: .1)
    captured = samples.capture(root, project)
    return root, project, captured['id']


def pair(native, *, verdict='pass', isolation='independent-subagent', refs=True, still_only=False):
    root, project, identity = native
    directory = outputs(root) / 'samples' / identity
    request = read(directory / 'review-request.json')
    request['conditions'] = ['主体轮廓与空间关系']
    if refs:
        Image.new('RGB', (640, 360), 'red').save(outputs(root) / 'target.png')
        request.update(references=['target.png'], conditions=['整体品质参考：主体轮廓与空间关系'])
    if still_only:
        request['items'] = request['items'][:-1]
    pack = reviews.package(root, project, request)
    blind = reviews.import_report(root, project, report((root, project), pack, verdict=verdict, isolation=isolation))
    request.update(reviewType='consistency', blindId=blind['id'])
    pack = reviews.package(root, project, request)
    comparison = reviews.import_report(root, project, report((root, project), pack, verdict=verdict, isolation=isolation))
    return dict(blind_id=blind['id'], comparison_id=comparison['id'], basis='主体与目标品质已通过实际对照')


def test_delivery_reuses_the_reviewed_media_without_encoding(native, monkeypatch):
    root, project, identity = native
    args = pair(native)
    monkeypatch.setattr(samples.design_sample, 'render', lambda *a, **k: pytest.fail('交付不得重渲染'))
    delivered = samples.deliver(root, project, identity, **args)
    assert not delivered['reused']
    target = Path(delivered['path'])
    assert (target / 'sample.mp4').read_bytes() == b'test-encoded-video'
    assert samples.deliver(root, project, identity, **args)['reused']


@pytest.mark.parametrize('options', [dict(verdict='fail'), dict(verdict='insufficient'),
                                     dict(isolation='self-review'), dict(refs=False), dict(still_only=True)])
def test_incomplete_or_nonindependent_review_cannot_deliver(native, options):
    root, project, identity = native
    args = pair(native, **options)
    with pytest.raises(M2VError):
        samples.deliver(root, project, identity, **args)
    assert not (outputs(root) / 'sample-deliveries' / identity).exists()


@pytest.mark.parametrize('change', ['source', 'artifact', 'receipt', 'cycle', 'project'])
def test_old_or_modified_capture_is_invalid(native, change):
    root, project, identity = native
    directory = outputs(root) / 'samples' / identity
    if change == 'source':
        (root / 'scenes/main.tsx').write_text('changed', encoding='utf-8')
    elif change == 'artifact':
        (directory / 'sample.mp4').write_bytes(b'changed')
    elif change == 'receipt':
        write(directory / 'capture.json', {})
    elif change == 'cycle':
        ledger.start(root, project, basis='test new cycle')
    else:
        project = {**project, 'output': {**project['output'], 'fps': 24}}
    with pytest.raises(M2VError):
        samples.load(root, project, identity)


def test_arbitrary_image_and_handwritten_receipt_do_not_establish_native_capture(native):
    root, project, _ = native
    forged = outputs(root) / 'samples/forged/capture.json'
    write(forged, {'native': True})
    with pytest.raises(M2VError, match='采集事件'):
        samples.load(root, project, 'forged')


def test_open_required_issue_blocks_delivery(native, monkeypatch):
    root, project, identity = native
    args = pair(native)
    monkeypatch.setattr(issues, 'load', lambda *a, **k: [{'required': True, 'status': 'open'}])
    with pytest.raises(M2VError, match='必改项'):
        samples.deliver(root, project, identity, **args)


def test_failed_capture_does_not_publish_an_event(native, monkeypatch):
    root, project, _ = native
    before = ledger.history(root)[0]
    def fail(*args, **kwargs):
        raise M2VError('test render failed')
    monkeypatch.setattr(samples.design_sample, 'render', fail)
    with pytest.raises(M2VError, match='render failed'):
        samples.capture(root, project)
    assert ledger.history(root)[0] == before
    assert not list((outputs(root) / 'samples').glob('.sample-*'))


def test_capture_defers_private_warning_but_still_checks_publication(native, monkeypatch, caplog):
    from m2v.core import security
    root, project, _ = native
    render = samples.design_sample.render

    def encoded(root, project, stage, **options):
        result = render(root, project, stage, **options)
        security._warn_if_still_unusable(stage / 'sample.mp4')
        return result

    def publish(stage, target):
        stage.replace(target)
        security._warn_if_still_unusable(target)

    monkeypatch.setattr(samples.design_sample, 'render', encoded)
    monkeypatch.setattr(security, 'deliver_directory', publish)
    monkeypatch.setattr(security, 'has_usable_access', lambda path: False)
    captured = samples.capture(root, project)
    warnings = [r.getMessage() for r in caplog.records if r.name == 'm2v.core.security']
    assert len(warnings) == 1
    assert str(outputs(root) / 'samples' / captured['id']) in warnings[0]
    assert '.sample-' not in warnings[0]


def test_failed_sample_can_be_closed_by_a_new_native_capture(native):
    root, project, identity = native
    pair(native, verdict='fail')
    with pytest.raises(M2VError, match='不能重开周期'):
        ledger.start(root, project, basis='attempt to evade')
    fresh = samples.capture(root, project)['id']
    args = pair((root, project, fresh))
    for item in issues.load(root):
        item.update(status='closed', cause='implementation', closureReportId=args['blind_id'])
        issues.update(root, item)
    assert all(item['status'] == 'closed' for item in issues.load(root))
    assert samples.deliver(root, project, fresh, **args)['sampleId'] == fresh


def test_generic_or_truncated_review_cannot_close_native_failure(native):
    root, project, identity = native
    pair(native, verdict='fail')
    fresh = samples.capture(root, project)['id']
    args = pair((root, project, fresh), still_only=True)
    item = issues.load(root)[0]
    item.update(status='closed', cause='design', closureReportId=args['blind_id'])
    with pytest.raises(M2VError, match='对应范围'):
        issues.update(root, item)


def test_corruption_before_capture_event_does_not_allow_cycle_reset(native):
    root, project, identity = native
    path = ledger.directory(root) / 'history.jsonl'
    path.write_text('{broken\n' + path.read_text(encoding='utf-8'), encoding='utf-8')
    with pytest.raises(M2VError, match='不能重开周期'):
        ledger.start(root, project, basis='attempt to evade broken history')


def test_missing_report_cannot_deliver(native):
    root, project, identity = native
    with pytest.raises(M2VError, match='缺失'):
        samples.deliver(root, project, identity, blind_id='missing', comparison_id='missing', basis='test')


def test_request_write_failure_does_not_publish_capture(native, monkeypatch):
    root, project, identity = native
    before = ledger.history(root)[0]
    original = samples.write
    def fail_request(path, value):
        if path.name == 'review-request.json':
            raise OSError('test disk failure')
        original(path, value)
    monkeypatch.setattr(samples, 'write', fail_request)
    with pytest.raises(OSError, match='disk failure'):
        samples.capture(root, project)
    assert ledger.history(root)[0] == before


def test_source_changed_after_compiler_read_is_rejected(native, monkeypatch, tmp_path):
    from types import SimpleNamespace
    from m2v.types.scene_film.code_scenes import config
    root, project, _ = native
    source = root / 'scenes/main.tsx'
    build = tmp_path / 'build'
    build.mkdir()
    def compiler(*args, **kwargs):
        write(build / 'inputs.json', [str(source)])
        write(build / 'input-digests.json', {str(source): dependencies.digest(source)})
        source.write_text('edited after compiler read', encoding='utf-8')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(config.subprocess, 'run', compiler)
    scene = {'id': 'test', 'content': {'entry': 'scenes/main.tsx', 'props': {}}}
    with pytest.raises(M2VError, match='构建期间'):
        config.build_scene(root, scene, build)


@pytest.mark.parametrize('change', ['media', 'source'])
def test_edit_during_delivery_does_not_publish_different_content(native, monkeypatch, change):
    root, project, identity = native
    args = pair(native)
    original = samples.shutil.copy2
    def copy(source, destination):
        if change == 'media' and source.name == 'sample.mp4':
            source.write_bytes(b'edited during delivery')
        if change == 'source':
            (root / 'scenes/main.tsx').write_text('edited during delivery', encoding='utf-8')
        return original(source, destination)
    monkeypatch.setattr(samples.shutil, 'copy2', copy)
    with pytest.raises(M2VError, match='发生变化'):
        samples.deliver(root, project, identity, **args)
    assert not (outputs(root) / 'sample-deliveries' / identity).exists()


@pytest.mark.skipif(os.name != 'nt', reason='Windows临时目录ACL回归')
@pytest.mark.media
def test_native_publish_restores_access_to_stills_video_and_web(native):
    """真实受限临时目录经采集与已评交付发布后，标准权限应用可读取全部媒体。"""
    import shutil
    from uuid import uuid4
    from m2v.core import security
    original, project, _ = native
    # pytest临时根本身受限；将同一模拟作品复制到正常继承ACL的工作区。
    cache = (Path.cwd() / '.cache').resolve()
    root = cache / f'native-access-{uuid4().hex}'
    assert root.is_relative_to(cache)
    try:
        shutil.copytree(original, root)
        fresh = samples.capture(root, project)['id']
        captured = outputs(root) / 'samples' / fresh
        for path in [captured, captured / 'still-000001.png', captured / 'sample.mp4', captured / 'web/index.html']:
            assert security.has_usable_access(path), path
        args = pair((root, project, fresh))
        delivered = Path(samples.deliver(root, project, fresh, **args)['path'])
        for path in [delivered, delivered / 'still-000001.png', delivered / 'sample.mp4']:
            assert security.has_usable_access(path), path
    finally:
        if root.exists():
            shutil.rmtree(root)
