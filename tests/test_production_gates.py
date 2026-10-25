"""制作门的行为回归：防止陈旧证据放行、误删引用及状态查询写盘。"""
import json
from pathlib import Path

import pytest

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from m2v.production import baselines, checks, contract, issues, ledger, measure
from m2v.production.storage import locked, read, receipt, write


def sample():
    return {'version': 1, 'fps': 30, 'width': 1920, 'height': 1080, 'structureRisk': False,
            'scenes': [{'id': sid, 'durationFrames': 30,
                'shots': [{'id': sid + '-shot', 'tier': 'B', 'window': [0, 30]}],
                'checkpoints': [{'id': sid + '-cp', 'shotId': sid + '-shot', 'frame': 15, 'window': [0, 30],
                    'expected': [{'role': 'disc', 'count': 2}], 'textPlan': [], 'claims': [], 'forbidden': []}]} for sid in ('one', 'two')]}


@pytest.fixture
def project(tmp_path):
    root = tmp_path / 'work'
    root.mkdir()
    c = sample()
    (root / 'DESIGN.md').write_text('```m2v-checkpoints\n' + json.dumps(c) + '\n```\n', encoding='utf-8')
    (root / 'scenes').mkdir()
    for s in c['scenes']:
        (root / 'scenes' / (s['id'] + '.tsx')).write_text('export default 1;', encoding='utf-8')
    write(root / 'storyboard.json', {'width': 1920, 'height': 1080, 'fps': 30,
        'scenes': [{'id': s['id'], 'durationFrames': 30, 'content': {'entry': f'scenes/{s["id"]}.tsx'}} for s in c['scenes']]})
    out = outputs(root)
    out.mkdir()
    (out / 'visual-notes.md').write_text('```m2v-issues\n[]\n```\n', encoding='utf-8')
    write(out / 'production/comparisons.json', [])
    return root, {'id': 'work', 'type': 'general'}, c


@pytest.mark.parametrize('mutation', ['unknown', 'duplicate', 'frame', 'empty', 'claim'])
def test_invalid_contract_rejected(mutation):
    c = sample()
    cp = c['scenes'][0]['checkpoints'][0]
    if mutation == 'unknown':
        cp['invented'] = True
    elif mutation == 'duplicate':
        c['scenes'][1]['checkpoints'][0]['id'] = cp['id']
    elif mutation == 'frame':
        cp['frame'] = 30
    elif mutation == 'empty':
        cp['expected'] = []
    else:
        cp['claims'] = [{'id': 'year', 'value': v, 'unit': '年', 'basis': '同一时点'} for v in (29, 30)]
    with pytest.raises(M2VError):
        contract.validate(c)


def test_readonly_status_and_stale_contract(project):
    root, manifest, c = project
    with locked(root):
        path = checks.run(root, manifest, 'G1')[0]
        ledger.register(root, manifest, path)
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = ledger.status(root, manifest)
    assert result['gates'][1]['status'] == '过期'  # 缺 G0，不能授权下游。
    assert before == {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    c['scenes'][0]['checkpoints'][0]['expected'][0]['count'] = 3
    changed = contract.scope_digest(c, 'one', 'one-cp')
    assert changed != contract.scope_digest(sample(), 'one', 'one-cp')
    assert contract.scope_digest(c, 'two', 'two-cp') == contract.scope_digest(sample(), 'two', 'two-cp')


def test_log_damage_and_repair_preserves_original(project):
    root, manifest, _ = project
    with locked(root):
        event = ledger.append(root, manifest, 'started', event_id='same')
        assert ledger.append(root, manifest, 'started', event_id='same') == event
        path = outputs(root) / 'production/history.jsonl'
        with path.open('a', encoding='utf-8') as stream:
            stream.write('{broken')
        original = path.read_bytes()
        assert ledger.history(root)[1]
        with pytest.raises(M2VError):
            ledger.append(root, manifest, 'started')
        result = ledger.repair(root)
        assert Path(result['backup']).read_bytes() == original
        assert not ledger.history(root)[1]


def test_five_versions_protected_then_pruned_records_survive(project):
    root, manifest, _ = project
    out = outputs(root)
    (out / 'video.mp4').write_bytes(b'media')
    with locked(root):
        values = [baselines.create(root, manifest, reason='重制', files=['video.mp4']) for _ in range(4)]
        write(out / 'production/comparisons.json', [{'status': 'active', 'versionRefs': [v['id'] for v in values]}])
        result = baselines.prune(root, manifest)
        assert result['fullVersions'] == 5 and result['excess'] == 2
        write(out / 'production/comparisons.json', [])
        result = baselines.prune(root, manifest)
        assert result['fullVersions'] == 3
        for value in baselines.manifests(root):
            directory = out / 'baselines' / value['id']
            assert all((directory / entry['path']).is_file() for entry in value['records'])
            if value['retention'] == 'record-only':
                assert value['prunedAt'] and all(not (directory / e['path']).exists() for e in value['media'])


def test_invalid_references_stop_cleanup(project):
    root, manifest, _ = project
    (outputs(root) / 'visual-notes.md').write_text('```m2v-issues\ninvalid\n```', encoding='utf-8')
    with locked(root), pytest.raises(M2VError):
        baselines.prune(root, manifest)


def element(**kw):
    return dict(id='x', role='body', state='', color='rgb(255, 255, 255)', visible=True, clipped=False,
                text='正文', fontSize=80, x=10, y=10, width=100, height=80, parents=[], **kw)


def test_measure_allowed_containment_and_hidden_count():
    cp = sample()['scenes'][0]['checkpoints'][0]
    cp['expected'] = [{'role': 'body', 'count': 1}]
    cp['measurement'] = {'bodyRoles': ['body'], 'thresholdSource': '设计', 'minFont393': 12, 'maxTextCharacters': 5}
    body = element()
    parent = {**element(), 'id': 'background', 'role': 'background', 'width': 1000, 'height': 900}
    body['parents'] = ['background']
    hidden = {**body, 'id': 'hidden', 'visible': False}
    result = measure.evaluate([body, parent, hidden], cp, width=1920, height=1080, frame=15)
    assert all(x['status'] == 'pass' for x in result)
    overlap = {**body, 'id': 'other', 'parents': []}
    result = measure.evaluate([body, overlap], cp, width=1920, height=1080, frame=15)
    assert any(x['name'] == '未授权重叠' and x['status'] == 'fail' for x in result)


def test_non_general_needs_no_contract(tmp_path):
    assert ledger.status(tmp_path, {'type': 'housing-timeseries'})['applicability'] == '专用类型契约'


def test_local_source_change_does_not_expire_other_scene(project):
    root, _, c = project
    first = ledger.upstream(root, c, 'G4', 'one', 'one-cp')
    other = ledger.upstream(root, c, 'G4', 'two', 'two-cp')
    (root / 'scenes/one.tsx').write_text('export default 2;', encoding='utf-8')
    assert first != ledger.upstream(root, c, 'G4', 'one', 'one-cp')
    assert other == ledger.upstream(root, c, 'G4', 'two', 'two-cp')


def test_no_a_keyframe_gate_is_not_applicable(project):
    root, manifest, _ = project
    path = checks.run(root, manifest, 'G2')[0]
    assert read(path)['status'] == 'not-applicable'
    with locked(root):
        event = ledger.register(root, manifest, path)
    assert event['data']['status'] == 'not-applicable'


def test_cleanup_interruption_resumes_media_plan(project, monkeypatch):
    root, manifest, _ = project
    out = outputs(root)
    (out / 'video.mp4').write_bytes(b'media')
    with locked(root):
        versions = [baselines.create(root, manifest, reason='重置', files=['video.mp4']) for _ in range(3)]
        original = Path.unlink
        def fail_once(path, *args, **kwargs):
            if versions[1]['id'] in str(path) and path.suffix == '.mp4':
                raise OSError('模拟删除中断')
            return original(path, *args, **kwargs)
        monkeypatch.setattr(Path, 'unlink', fail_once)
        with pytest.raises(OSError):
            baselines.prune(root, manifest)
        pending = read(out / 'baselines' / versions[1]['id'] / 'manifest.json')
        assert pending['retention'] == 'record-only' and pending['pendingDelete']
        monkeypatch.setattr(Path, 'unlink', original)
        baselines.prune(root, manifest)
        assert read(out / 'baselines' / versions[1]['id'] / 'manifest.json')['prunedAt']


def test_contract_path_id_is_rejected():
    c = sample()
    c['scenes'][0]['checkpoints'][0]['id'] = '../escape'
    with pytest.raises(M2VError):
        contract.validate(c)


def test_animatic_real_encode_and_duration(project):
    root, _, c = project
    for cp in c['scenes'][0]['checkpoints']:
        cp['window'] = [0,30]
    directory = outputs(root) / 'design'
    directory.mkdir()
    image = directory / 'key.png'
    checks.ffmpeg(['-f','lavfi','-i','color=c=blue:s=64x64','-frames:v','1',str(image)])
    entries=[]
    for scene in c['scenes']:
        cp = scene['checkpoints'][0]
        entries.append({'checkpointId':cp['id'],'width':c['width'],'path':image.relative_to(outputs(root)).as_posix()})
    write(outputs(root) / 'production/design-frames.json', {'frames':entries})
    video = checks.make_animatic(root,c)
    assert video.is_file() and video.stat().st_size > 100
    assert read(video.with_name('manifest.json'))['nonDelivery']


def test_missing_canvas_observation_is_unverified():
    cp=sample()['scenes'][0]['checkpoints'][0]
    assert all(x['status'] != 'pass' for x in measure.evaluate([],cp,width=1920,height=1080,frame=15))


def test_review_import_is_idempotent_and_bound(project):
    from m2v.production import reviews
    root, manifest, c = project
    out = outputs(root)
    evidence = out / 'neutral.png'
    checks.ffmpeg(['-f','lavfi','-i','color=c=blue:s=64x64','-frames:v','1',str(evidence)])
    cp = c['scenes'][0]['checkpoints'][0]
    report = checks.save_report(root,c,'G4',[{'name':'观察','status':'pass','detail':'fixture'}],
        scene_id='one',checkpoint_id=cp['id'],evidence=[receipt(out,evidence)])
    with locked(root):
        check = ledger.register(root,manifest,report)
        pack = reviews.package(root,gate='G5',scene_id=None,checkpoint_ids=[cp['id']],
            files=['neutral.png'],kind='scene-window',display_sizes=[393],timecodes=[[0,30]])
        value = dict(gate='G5',sceneId=None,checkpointIds=[cp['id']],packPath=(pack/'manifest.json').relative_to(out).as_posix(),
            packSha256=receipt(out,pack/'manifest.json')['sha256'],reviewerId='isolated-agent',
            isolation='independent-subagent',reviewType='blind',verdict='pass',observations=['观察'],checkIds=[check['id']])
        imported=out/'report.json';write(imported,value)
        first=reviews.import_report(root,manifest,imported)
        assert first==reviews.import_report(root,manifest,imported)
        (pack/'evidence-0000.png').write_bytes(b'changed')
        with pytest.raises(M2VError):
            reviews.import_report(root,manifest,imported)


def test_blind_pack_rejects_design_and_consistency_exports_contract(project):
    from m2v.production import reviews
    root, _, c = project
    out=outputs(root)
    (out/'design.md').write_text('秘密设计',encoding='utf-8')
    cp=c['scenes'][0]['checkpoints'][0]
    with pytest.raises(M2VError):
        reviews.package(root,gate='G4',scene_id='one',checkpoint_ids=[cp['id']],files=['design.md'],kind='scene-window',display_sizes=[393])
    pack=reviews.package(root,gate='G4',scene_id='one',checkpoint_ids=[cp['id']],files=['design.md'],kind='scene-window',display_sizes=[393],review_type='consistency')
    assert (pack/'contract-scope.json').exists()


def test_contract_change_does_not_change_prepared_fingerprint(project):
    root, _, c=project
    prepared=root/'outputs/prepared.json';write(prepared,{'preparedFingerprint':'unchanged','props':{'compiledScenes':[]}})
    old=prepared.read_bytes()
    c['scenes'][0]['checkpoints'][0]['expected'][0]['count']=3
    (root/'DESIGN.md').write_text('```m2v-checkpoints\n'+json.dumps(c)+'\n```\n',encoding='utf-8')
    ledger.status(root,{'id':'work','type':'general'})
    assert prepared.read_bytes()==old


@pytest.mark.slow
def test_rough_player_uses_composition_without_full_encode(project, monkeypatch, chromium_ready):
    from m2v.production import timeline
    from m2v.engine.http_server import LocalServer
    from m2v.engine import frames
    from playwright.sync_api import sync_playwright
    root, manifest, _=project
    clip=root/'clip.mp4'
    checks.ffmpeg(['-f','lavfi','-i','color=c=blue:s=1920x1080:r=30:d=1', '-c:v','libx264','-pix_fmt','yuv420p',str(clip)])
    props={'version':8,'schemaVersion':8,'fps':30,'width':1920,'height':1080,'title':'',
        'durationInFrames':30,'subtitle':frames.spec(1920,1080)['subtitle'],'subtitleCues':[],
        'compiledScenes':[{'id':'one','startFrame':0,'endFrame':30,'durationInFrames':30,'transitionFrames':0,'mediaPath':'clip.mp4'}]}
    prepared={'props':props,'durationInFrames':30,'fps':30,'width':1920,'height':1080}
    monkeypatch.setattr('m2v.commands._prepared',lambda *_:prepared)
    monkeypatch.setattr('m2v.types.general.code_scenes.materialize',lambda *_:prepared)
    monkeypatch.setattr('m2v.engine.lookdev.sample_audio',lambda *_:(False,None))
    monkeypatch.setattr(ledger,'status',lambda *_:{'scenes':[{'checkpointId':'one-cp','checkStatus':'通过','status':'待评审'}]})
    directory=timeline.build(root,manifest)
    assert not (directory/'video.mp4').exists()
    assert (directory/'evidence-0000.mp4').read_bytes()==clip.read_bytes()
    errors=[]
    with LocalServer(directory) as server, sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            page=browser.new_page()
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(server.base_url+'/index.html')
            page.locator('video').wait_for()
            assert not errors
        finally:browser.close()


def test_b_batch_review_can_close_g4_without_waiting_for_g5_pass(project):
    from m2v.production import reviews
    root,manifest,c=project
    out=outputs(root);image=out/'neutral.png'
    checks.ffmpeg(['-f','lavfi','-i','color=c=blue:s=64x64','-frames:v','1',str(image)])
    ids=[]
    with locked(root):
        for gate in ('G0','G1','G3'):
            path=checks.save_report(root,c,gate,[{'name':'事实与结构','status':'pass','detail':'fixture'}],evidence=[receipt(out,image)])
            ledger.register(root,manifest,path)
        ledger.register(root,manifest,checks.run(root,manifest,'G2')[0])
        for scene,_,cp in contract.checkpoints(c):
            path=checks.save_report(root,c,'G4',[{'name':'检查点','status':'pass','detail':'fixture'}],scene_id=scene['id'],checkpoint_id=cp['id'],evidence=[receipt(out,image)])
            ids.append(ledger.register(root,manifest,path)['id'])
        state=ledger.status(root,manifest)
        assert state['currentGate']=='G4' and 'G5' in state['next']
        cpids=[cp['id'] for _,_,cp in contract.checkpoints(c)]
        pack=reviews.package(root,gate='G5',scene_id=None,checkpoint_ids=cpids,files=['neutral.png'],kind='scene-window',display_sizes=[393])
        report=dict(gate='G5',sceneId=None,checkpointIds=cpids,packPath=(pack/'manifest.json').relative_to(out).as_posix(),packSha256=receipt(out,pack/'manifest.json')['sha256'],reviewerId='independent',isolation='independent-subagent',reviewType='blind',verdict='pass',observations=['观察'],checkIds=ids)
        path=out/'batch.json';write(path,report);reviews.import_report(root,manifest,path)
        state=ledger.status(root,manifest)
        assert state['currentGate']=='G5'
        assert all(x['status']=='通过' for x in state['scenes'])


def test_source_tag_alone_does_not_prove_independent_keyframe(project):
    root,_,c=project
    c['scenes'][0]['shots'][0]['core']=True
    entries=[{'checkpointId':'one-cp','width':w,'source':'independent-design'} for w in (1920,852,393)]
    write(outputs(root)/'production/design-frames.json',{'frames':entries})
    result=checks.design_frames(root,c)
    assert any(x['status']=='unverified' for x in result)


def test_lock_excludes_second_writer_and_missing_newline_is_safe(project):
    root,manifest,_=project
    with locked(root):
        with pytest.raises(M2VError):
            with locked(root):pass
        ledger.append(root,manifest,'first')
        path=outputs(root)/'production/history.jsonl'
        path.write_bytes(path.read_bytes().rstrip(b'\n'))
        ledger.append(root,manifest,'second')
    events,diagnostics=ledger.history(root)
    assert len(events)==2 and not diagnostics


def test_corrupt_middle_event_blocks_prefix_authorization(project):
    root,manifest,_=project
    with locked(root):
        ledger.append(root,manifest,'first')
        ledger.append(root,manifest,'second')
        path=outputs(root)/'production/history.jsonl'
        lines=path.read_text(encoding='utf-8').splitlines()
        path.write_text(lines[0]+'\n{}\n'+lines[1]+'\n',encoding='utf-8')
        events,diagnostics=ledger.history(root)
        assert len(events)==1 and diagnostics
        assert ledger.status(root,manifest)['diagnostics']


def test_title_year_claim_conflict_rejected():
    c=sample();cp=c['scenes'][0]['checkpoints'][0]
    cp['textPlan']=[{'role':'year','text':'第30年','window':[0,30]}]
    cp['claims']=[{'id':'year','value':29,'unit':'年','basis':'相同时间状态','role':'year'}]
    with pytest.raises(M2VError,match='文字与定量主张矛盾'):
        contract.validate(c)
