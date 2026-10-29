"""制作门的行为回归：防止陈旧证据放行、误删引用及状态查询写盘。"""
import json
from pathlib import Path

import pytest

from m2v.core.delivery import outputs
from m2v.core.errors import M2VError
from m2v.production import baselines, checks, contract, issues, ledger, measure
from m2v.production.storage import locked, read, receipt, write


def sample():
    return {'version': 2, 'cycleId': 'test-cycle', 'fps': 30, 'width': 1920, 'height': 1080,
            'reviewPlan': {'basis': '基础布局无核心未决风险', 'risks': []},
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
        cp['expected'] = None
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
    assert result['gates'][1]['status'] == '等待前置'
    assert result['gates'][1]['evidenceStatus'] == '通过'
    assert result['gates'][1]['prerequisites'] == ['G0']
    assert not result['gates'][1]['ready']
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


def test_measure_screen_subtitle_safe_area_and_single_line():
    cp = sample()['scenes'][0]['checkpoints'][0]
    cp['expected'] = []
    cp['textPlan'] = [{'role': 'subtitle', 'text': '夜空为什么是黑的', 'window': [0, 30]}]
    cp['measurement'] = {'subtitleRoles': ['subtitle']}
    safe = {'x': 192, 'y': 888, 'width': 1536, 'height': 113}
    inside = element()
    inside.update(id='sub', role='subtitle', text='夜空为什么是黑的', x=500, y=900,
                  width=900, height=66, fontSize=44, lineHeight=66, scrollWidth=880, clientWidth=900)
    result = measure.evaluate([inside], cp, width=1920, height=1080, frame=15, safe_area=safe)
    assert all(x['status'] != 'fail' for x in result), result
    assert any(x['name'].startswith('屏幕字幕安全区') and x['status'] == 'pass' for x in result)
    assert any(x['name'].startswith('屏幕字幕单行') and x['status'] == 'pass' for x in result)
    outside = {**inside, 'y': 1020}
    result = measure.evaluate([outside], cp, width=1920, height=1080, frame=15, safe_area=safe)
    assert any(x['name'].startswith('屏幕字幕安全区') and x['status'] == 'fail' for x in result)
    overflow = {**inside, 'scrollWidth': 1200}
    result = measure.evaluate([overflow], cp, width=1920, height=1080, frame=15, safe_area=safe)
    assert any(x['name'].startswith('屏幕字幕单行') and x['status'] == 'fail' for x in result)
    # prepared 的 subtitle 对象含 safeArea；传整个对象也必须能解出安全区。
    nested = measure.evaluate([inside], cp, width=1920, height=1080, frame=15,
                              safe_area={'safeArea': safe, 'fontSize': 40})
    assert any(x['name'].startswith('屏幕字幕安全区') and x['status'] == 'pass' for x in nested)


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
    # 两幕各 30 帧 = 2 秒；编码不得按图片默认帧率漂移。
    from imageio_ffmpeg import count_frames_and_secs
    frames, seconds = count_frames_and_secs(str(video))
    assert abs(seconds - 2.0) < 0.05, (frames, seconds)


def test_missing_canvas_observation_is_unverified():
    cp=sample()['scenes'][0]['checkpoints'][0]
    assert all(x['status'] != 'pass' for x in measure.evaluate([],cp,width=1920,height=1080,frame=15))


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
    from m2v.core import frames
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
    monkeypatch.setattr(ledger,'status',lambda *_:{'scenes':[{'checkpointId':'one-cp','checkStatus':'通过','status':'通过'}],
        'gates':[{'gate':g,'evidenceStatus':'通过'} for g in ('G2','G3')]})
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


def test_source_tag_alone_does_not_prove_independent_keyframe(project):
    root,_,c=project
    c['reviewPlan']['risks']=[{'id':'static','kind':'static-expression','scope':{'checkpointIds':['one-cp']},
        'reason':'新空间关系尚未验证','requiredEvidence':['目标图']} ]
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


def passing_check(root, manifest, c, gate='G4'):
    scope = dict(scene_id='one', checkpoint_id='one-cp') if gate == 'G4' else {}
    path=checks.save_report(root,c,gate,[{'name':'测量','status':'pass','detail':'fixture'}], **scope)
    return ledger.register(root,manifest,path)


def test_sampling_includes_short_text_and_state_boundaries():
    c=sample();scene,shot,cp=next(contract.checkpoints(c))
    cp.update(sampleStep=10,textPlan=[{'role':'title','text':'揭示','window':[7,8]}],
              statePlan=[{'window':[13,16],'expected':[{'role':'disc','count':1}]}])
    shot['timeStructure']={'reveal':{'window':[21,25]},'pause':{'window':None}}
    frames=checks.sample_frames(cp,shot)
    assert {6,7,8,9,12,13,14,15,16,17,20,21,22,24,25,26} <= set(frames)
    assert frames==sorted(set(frames)) and min(frames)==0 and max(frames)==29
    # 粗步长遗漏的单帧文字现在实际参与检查。
    cp['expected']=[{'role':'title','count':0}]
    results=measure.evaluate([],cp,width=1920,height=1080,frame=7)
    assert any(x['name']=='文字状态:title' and x['status']=='fail' for x in results)


def test_state_plan_detects_middle_error_despite_correct_endpoint():
    cp=sample()['scenes'][0]['checkpoints'][0]
    cp['statePlan']=[{'window':[5,10],'expected':[{'role':'disc','count':1}]}]
    wrong=[{**element(),'id':str(i),'role':'disc','x':i*200} for i in range(2)]
    results=measure.evaluate(wrong,cp,width=1920,height=1080,frame=7)
    assert any(x['name']=='对象状态:disc' and x['status']=='fail' for x in results)
    results=measure.evaluate(wrong,cp,width=1920,height=1080,frame=15)
    assert any(x['name']=='对象状态:disc' and x['status']=='pass' for x in results)


@pytest.mark.parametrize('plans',[
    [{'window':[0,10],'expected':[{'role':'disc','count':1}]}, {'window':[9,20],'expected':[{'role':'disc','count':2}]}],
    [{'window':[0,31],'expected':[{'role':'disc','count':1}]}],
    [{'window':[0,10],'expected':[]}],
])
def test_invalid_state_plan_rejected(plans):
    c=sample();c['scenes'][0]['checkpoints'][0]['statePlan']=plans
    with pytest.raises(M2VError): contract.validate(c)


def test_waiting_prerequisite_does_not_invalidate_own_evidence(project):
    root,manifest,c=project
    check=passing_check(root,manifest,c,'G1')
    row=ledger.status(root,manifest)['gates'][1]
    assert row['status']=='等待前置' and row['evidenceStatus']=='通过'
    passing_check(root,manifest,c,'G0')
    row=ledger.status(root,manifest)['gates'][1]
    assert row['status']=='通过' and row['ready'] and not row['prerequisites']
    c['scenes'][0]['checkpoints'][0]['expected'][0]['count']=3
    (root/'DESIGN.md').write_text('```m2v-checkpoints\n'+json.dumps(c)+'\n```\n',encoding='utf-8')
    row=ledger.status(root,manifest)['gates'][1]
    assert row['evidenceStatus']=='过期' and row['status']=='过期'


def test_policy_derives_rounds_from_risks_only():
    from m2v.production import policy
    plain = sample()
    assert policy.rounds(plain) == {'core': 0, 'rough': 0, 'final': 1, 'defaultCalls': 1}
    core = sample()
    core['reviewPlan']['risks'] = [{'id': 'event', 'kind': 'core-event', 'scope': {'checkpointIds': ['one-cp']},
        'reason': '因果尚未验证', 'requiredEvidence': ['完整窗口']}]
    assert policy.rounds(core) == {'core': 1, 'rough': 0, 'final': 1, 'defaultCalls': 2}
    assert policy.requirement(core, 'G4', 'one-cp')['count'] == 1
    assert policy.requirement(core, 'G4', 'two-cp')['count'] == 0
    split = sample()
    split['reviewPlan']['risks'] = [{'id': 'split', 'kind': 'split-final', 'scope': {'checkpointIds': ['one-cp']},
        'reason': '用户要求双人', 'requiredEvidence': ['两份隔离报告']}]
    assert policy.requirement(split, 'G6')['focuses'] == ['structure', 'visual-copy']
    assert policy.rounds(split) == {'core': 0, 'rough': 0, 'final': 2, 'defaultCalls': 2}
    # 镜头等级本身不是风险，不派生审核。
    graded = sample()
    graded['scenes'][0]['shots'][0]['tier'] = 'A'
    assert policy.rounds(graded) == policy.rounds(sample())


@pytest.mark.parametrize('mutate', [
    lambda c: c.update(version=1),
    lambda c: (c.pop('reviewPlan'), c.update(structureRisk=False)),
    lambda c: c.update(acceptanceChecks=True),
    lambda c: c['reviewPlan'].update(risks=[{'id': 'x', 'kind': 'unknown', 'scope': {'checkpointIds': ['one-cp']},
        'reason': 'r', 'requiredEvidence': ['e']}]),
    lambda c: c['reviewPlan'].update(risks=[{'id': 'x', 'kind': 'core-event', 'scope': {'checkpointIds': []},
        'reason': 'r', 'requiredEvidence': ['e']}]),
    lambda c: c['reviewPlan'].update(risks=[{'id': 'x', 'kind': 'core-event', 'scope': {'checkpointIds': ['missing']},
        'reason': 'r', 'requiredEvidence': ['e']}]),
    lambda c: c['reviewPlan'].update(risks=[{'id': 'x', 'kind': 'core-event', 'scope': {'checkpointIds': ['one-cp']},
        'reason': 'r', 'requiredEvidence': []}]),
    lambda c: c['reviewPlan'].update(risks=[{'id': 'x', 'kind': 'structure-timing',
        'scope': {'checkpointIds': ['one-cp']}, 'reason': 'r', 'requiredEvidence': ['e']}]),
])
def test_contract_v2_rejects_legacy_or_unfounded_plan(mutate):
    c = sample()
    mutate(c)
    with pytest.raises(M2VError):
        contract.validate(c)


def test_coverage_must_match_scope_and_sequence():
    from m2v.production import acceptance
    c = sample()
    report = {'checkpointIds': ['one-cp'], 'round': 'core', 'reviewType': 'blind', 'verdict': 'pass'}
    item = {'checkpointId': 'one-cp', 'window': [0, 30], 'status': 'pass',
            'observations': '看到两枚圆片', 'evidence': [{'path': 'x', 'sha256': 'y'}], 'issues': [],
            'assessment': assessment()}
    valid = lambda base, entries: True
    assert acceptance.validate([item], c, report, Path('.'), valid) == item['evidence']
    with pytest.raises(M2VError, match='覆盖'):
        acceptance.validate([{**item, 'window': [0, 29]}], c, report, Path('.'), valid)
    with pytest.raises(M2VError, match='失败或证据不足'):
        acceptance.validate([{k: v for k, v in {**item, 'status': 'insufficient'}.items() if k != 'assessment'}],
                            c, report, Path('.'), valid)
    with pytest.raises(M2VError, match='缺少必要覆盖'):
        acceptance.validate([item], c, {**report, 'round': 'rough'}, Path('.'), valid)
    core = {**report, 'round': 'core', 'gate': 'G4'}
    with pytest.raises(M2VError, match='完整过程片段'):
        core_c = sample()
        core_c['reviewPlan']['risks'] = [{'id': 'e', 'kind': 'core-event', 'scope': {'checkpointIds': ['one-cp']},
            'reason': 'r', 'requiredEvidence': ['e']}]
        acceptance.validate([item], core_c, core, Path('.'), valid)
    # 静态轮不因同一检查点声明了动态风险而要求视频。
    static_c = sample()
    static_c['reviewPlan']['risks'] = [{'id': 'e', 'kind': 'core-event', 'scope': {'checkpointIds': ['one-cp']},
        'reason': 'r', 'requiredEvidence': ['e']}]
    for gate in ('G0', 'G2', 'G3'):
        assert acceptance.validate([item], static_c, {**core, 'gate': gate}, Path('.'), valid) == item['evidence']


def assessment(**states):
    return {name: {'status': states.get(name, 'pass'), 'observations': '当前证据支持此项判断'}
            for name in ('understanding', 'presentation', 'representativeness')}


def _review_inputs(root, manifest, event, *, round_name='core', focus='comprehensive',
                   reviewer='R1', blind_id=None):
    from datetime import datetime, timedelta, timezone
    from m2v.production import reviews
    out = outputs(root)
    (out / 'production/frames').mkdir(parents=True, exist_ok=True)
    image = out / 'production/frames/window.png'
    checks.ffmpeg(['-f', 'lavfi', '-i', 'color=c=blue:s=64x64', '-frames:v', '1', str(image)])
    pack = reviews.package(root, gate=event['gate'], scene_id=event['sceneId'],
                           checkpoint_ids=[event['checkpointId']], files=['production/frames/window.png'],
                           kind='scene-window', display_sizes=[1920], blind_id=blind_id,
                           review_type='blind' if blind_id is None else 'consistency')
    pack_path = pack / 'manifest.json'
    value = read(pack_path)
    media = next(e for e in value['files'] if e['path'].endswith('.png'))
    evidence = [receipt(out, pack / media['path'])]
    suffix = round_name + '-' + ('blind' if blind_id is None else 'consistency')
    invocation = out / f'invocation-{reviewer}-{suffix}.json'
    write(invocation, {
        'id': 'inv-' + reviewer + '-' + suffix, 'reviewerId': reviewer, 'freshContext': True,
        'startedAt': (datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat(),
        'completedAt': (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat(),
        'inputPaths': [pack_path.relative_to(out).as_posix()], 'readReportIds': [] if blind_id is None else [blind_id]})
    report = out / f'report-{reviewer}-{suffix}.json'
    write(report, {
        'gate': event['gate'], 'round': round_name, 'roundId': 'round-' + reviewer, 'sceneId': event['sceneId'],
        'checkpointIds': [event['checkpointId']], 'packPath': pack_path.relative_to(out).as_posix(),
        'packSha256': receipt(out, pack_path)['sha256'], 'reviewerId': reviewer,
        'isolation': 'independent-subagent', 'reviewType': 'blind' if blind_id is None else 'consistency',
        'verdict': 'pass', 'observations': ['看到两枚圆片和明确变化'], 'checkIds': [event['id']], 'focus': focus,
        'coverage': [{'checkpointId': event['checkpointId'], 'window': [0, 30], 'status': 'pass',
                      'observations': '完整窗口内有可见变化', 'evidence': evidence, 'issues': [],
                      'assessment': assessment()}],
        'invocation': receipt(out, invocation)})
    return report, pack_path


def test_one_report_binds_multiple_checks_and_rejects_reuse(project):
    from m2v.production import reviews
    root, manifest, c = project
    with locked(root):
        event = passing_check(root, manifest, c)
        report, _ = _review_inputs(root, manifest, event)
        result = reviews.import_report(root, manifest, report)
        assert len(result['events']) == 1
        # 重复导入幂等。
        assert reviews.import_report(root, manifest, report)['events'] == result['events']
        # 同一调用不能换身份冒充第二名终审。
        second, _ = _review_inputs(root, manifest, event, reviewer='R2')
        reviews.import_report(root, manifest, second)
        value = read(second)
        value['reviewerId'] = 'R3'
        value['invocation'] = {'path': value['invocation']['path'], 'sha256': value['invocation']['sha256']}
        write(second, value)
        with pytest.raises(M2VError):
            reviews.import_report(root, manifest, second)


def test_final_review_requires_unused_reviewer(project):
    from m2v.production import reviews
    root, manifest, c = project
    with locked(root):
        event = passing_check(root, manifest, c)
        early, _ = _review_inputs(root, manifest, event, reviewer='R1')
        reviews.import_report(root, manifest, early)
        final, _ = _review_inputs(root, manifest, event, round_name='final', reviewer='R1')
        with pytest.raises(M2VError, match='新代理'):
            reviews.import_report(root, manifest, final)


def test_consistency_requires_prior_blind_round(project):
    from m2v.production import reviews
    root, manifest, c = project
    with locked(root):
        event = passing_check(root, manifest, c)
        blind, _ = _review_inputs(root, manifest, event, reviewer='R1')
        reviews.import_report(root, manifest, blind)
        blind_id = next(e for e in ledger.history(root)[0] if e['type'] == 'review')['data']['reportId']
        consistency, _ = _review_inputs(root, manifest, event, reviewer='R1', blind_id=blind_id)
        reviews.import_report(root, manifest, consistency)
        # 缺 blind_id 的对照包直接拒绝。
        with pytest.raises(M2VError):
            reviews.package(root, gate=event['gate'], scene_id=event['sceneId'],
                            checkpoint_ids=[event['checkpointId']], files=['production/frames/window.png'],
                            kind='scene-window', display_sizes=[1920], review_type='consistency')


def test_text_boundary_can_reuse_one_role_for_successive_words():
    cp=sample()['scenes'][0]['checkpoints'][0]
    cp['textPlan']=[{'role':'body','text':'建立','window':[0,7]},
                    {'role':'body','text':'揭示','window':[7,8]}]
    actual={**element(),'text':'揭示'}
    result=measure.evaluate([actual],cp,width=1920,height=1080,frame=7)
    assert [x['status'] for x in result if x['name']=='文字状态:body']==['pass']


def static_risk(root, c):
    c['reviewPlan']['risks'] = [{'id': 'style', 'kind': 'static-expression',
        'scope': {'checkpointIds': ['one-cp']}, 'reason': '参考关键造型尚未兑现',
        'requiredEvidence': ['风格契约中的主体与光线采用项']}]
    (root / 'DESIGN.md').write_text('```m2v-checkpoints\n' + json.dumps(c) + '\n```\n', encoding='utf-8')


@pytest.mark.parametrize('dimension,state', [('presentation', 'fail'), ('representativeness', 'insufficient')])
def test_core_cannot_merge_understanding_pass_with_weak_presentation(dimension, state):
    from m2v.production import acceptance
    c = sample()
    c['reviewPlan']['risks'] = [{'id': 'style', 'kind': 'static-expression',
        'scope': {'checkpointIds': ['one-cp']}, 'reason': 'r', 'requiredEvidence': ['e']}]
    item = {'checkpointId': 'one-cp', 'window': [0, 30], 'status': 'pass', 'observations': '看懂了',
            'evidence': [{'path': 'x', 'sha256': 'y'}], 'issues': [], 'assessment': assessment(**{dimension: state})}
    report = {'checkpointIds': ['one-cp'], 'round': 'core', 'reviewType': 'blind', 'verdict': 'pass'}
    with pytest.raises(M2VError, match='不得合并'):
        acceptance.validate([item], c, report, Path('.'), lambda *_: True)
    item['status'] = state
    assert acceptance.validate([item], c, {**report, 'verdict': state}, Path('.'), lambda *_: True)
    item.pop('assessment')
    with pytest.raises(M2VError, match='assessment'):
        acceptance.validate([item], c, report, Path('.'), lambda *_: True)


def test_core_target_requires_independent_same_round_consistency(project):
    from m2v.production import reviews
    root, manifest, c = project
    static_risk(root, c)
    with locked(root):
        event = passing_check(root, manifest, c)
        blind, _ = _review_inputs(root, manifest, event)
        reviews.import_report(root, manifest, blind)
        row = ledger.status(root, manifest)['scenes'][0]
        assert row['status'] == '待评审' and row['missingAcceptance'] == ['同轮设计对照']
        blind_id = receipt(outputs(root), blind)['sha256']
        paired, _ = _review_inputs(root, manifest, event, blind_id=blind_id)
        value = read(paired)
        value['isolation'] = 'self-review'
        write(paired, value)
        with pytest.raises(M2VError, match='同一代理'):
            reviews.import_report(root, manifest, paired)
        value['isolation'] = 'independent-subagent'
        write(paired, value)
        reviews.import_report(root, manifest, paired)
        assert ledger.status(root, manifest)['scenes'][0]['evidenceStatus'] == '通过'
        # 当前有效报告被改写后，不沿用旧对照。
        value['observations'] = ['changed']
        write(paired, value)
        assert ledger.status(root, manifest)['scenes'][0]['status'] == '待评审'


def test_consistency_cannot_bind_another_check(project):
    from m2v.production import reviews
    root, manifest, c = project
    with locked(root):
        event = passing_check(root, manifest, c)
        blind, _ = _review_inputs(root, manifest, event)
        reviews.import_report(root, manifest, blind)
        second = passing_check(root, manifest, c)
        paired, _ = _review_inputs(root, manifest, second, blind_id=receipt(outputs(root), blind)['sha256'])
        with pytest.raises(M2VError, match='同一代理|相同检查'):
            reviews.import_report(root, manifest, paired)


def test_historical_core_pass_without_assessment_cannot_authorize(project):
    root, manifest, c = project
    static_risk(root, c)
    with locked(root):
        event = passing_check(root, manifest, c, 'G2')
        ledger.append(root, manifest, 'review', gate='G2', upstream=event['upstream'], evidence=event['evidence'],
            data={'checkId': event['id'], 'reviewerId': 'legacy', 'reviewType': 'blind',
                  'verdict': 'pass', 'focus': 'comprehensive', 'isolation': 'independent-subagent',
                  'coverage': [{'checkpointId': 'one-cp', 'status': 'pass'}]})
    row = ledger.status(root, manifest)['gates'][2]
    assert row['evidenceStatus'] == '待评审'
    assert row['missingAcceptance'] == ['核心理解、表现与代表性凭据']


def test_review_issue_needs_current_independent_recheck_and_keeps_scope(project):
    from m2v.production import reviews
    root, manifest, c = project
    static_risk(root, c)
    with locked(root):
        event = passing_check(root, manifest, c)
        failed, _ = _review_inputs(root, manifest, event, reviewer='failed')
        value = read(failed)
        value.update(verdict='fail')
        value['coverage'][0].update(status='fail', assessment=assessment(presentation='fail'))
        write(failed, value)
        reviews.import_report(root, manifest, failed)
        item = issues.load(root)[0]
        assert item['checkpointId'] == 'one-cp'
        with pytest.raises(M2VError, match='原范围'):
            issues.update(root, {**item, 'required': False})
        fake = {**receipt(outputs(root), failed), 'gate': 'G4'}
        with pytest.raises(M2VError, match='独立通过复查'):
            issues.update(root, {**item, 'status': 'closed', 'evidence': [fake]})
        passed, _ = _review_inputs(root, manifest, event, reviewer='recheck')
        reviews.import_report(root, manifest, passed)
        evidence = [{**receipt(outputs(root), passed), 'gate': 'G4'}]
        issues.update(root, {**item, 'status': 'closed', 'evidence': evidence})
        assert issues.load(root)[0]['status'] == 'closed'
        assert ledger.status(root, manifest)['scenes'][0]['evidenceStatus'] == '待评审'
        # 核心目标变化不能用旧报告关闭或保持通过。
        c['scenes'][0]['checkpoints'][0]['expected'][0]['count'] = 3
        (root / 'DESIGN.md').write_text('```m2v-checkpoints\n' + json.dumps(c) + '\n```\n', encoding='utf-8')
        with pytest.raises(M2VError, match='独立通过复查'):
            issues.load(root)
        result = ledger.status(root, manifest)
        assert not result['complete'] and result['diagnostics']
        issues.update(root, {**item, 'status': 'open'})
        assert issues.load(root)[0]['status'] == 'open'


def test_expansion_keeps_unrelated_scope_available_and_status_readonly(project):
    root, manifest, c = project
    # 普通准备门已完成；仅第一个检查点有失败，第二个仍允许继续。
    with locked(root):
        for gate in ('G0', 'G1', 'G2', 'G3'):
            passing_check(root, manifest, c, gate)
        for sid in ('one', 'two'):
            path = checks.save_report(root, c, 'G4', [{'name': 'fixture', 'status': 'pass', 'detail': 'ok'}],
                                     scene_id=sid, checkpoint_id=sid + '-cp')
            ledger.register(root, manifest, path)
        issues.update(root, {'id': 'layout', 'status': 'open', 'required': True, 'gate': 'G4', 'sceneId': 'one',
            'checkpointId': 'one-cp', 'caughtAt': 'G4', 'catchableAt': 'G4', 'evidence': [], 'versionRefs': []})
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = ledger.status(root, manifest)
    assert not result['complete']
    assert [row['allowed'] for row in result['expansion']] == [False, True]
    assert before == {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_technical_delivery_summary_does_not_claim_production_complete(project, monkeypatch):
    from m2v import commands
    from types import SimpleNamespace
    root, manifest, _ = project
    monkeypatch.setattr(commands.registry, 'get', lambda *_: SimpleNamespace(manual_review_available=False))
    monkeypatch.setattr(commands, '_prepared', lambda *_: {'preparedFingerprint': 'current'})
    monkeypatch.setattr(commands, 'read_record', lambda *_: {'status': 'delivered'})
    monkeypatch.setattr(commands, 'candidate', lambda *_: {'status': 'delivered'})
    result = commands._status(root, manifest)
    assert result['stage'] == 'delivered'
    assert result['summary'] == '候选已生成，制作未完成'
    assert not result['production']['complete']


