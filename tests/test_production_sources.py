"""规则修改必须传播到实际消费者和文档投影，而不是只比较常量副本。"""
import copy
import json

import pytest
import sync_docs

from m2v.core import frames, video_config
from m2v.core.errors import M2VError
from m2v.production import contract, policy, workflow
from test_production_gates import sample


def test_contract_and_project_follow_shared_fps(monkeypatch):
    monkeypatch.setattr(video_config, 'GENERAL_ALLOWED_FPS', (24,))
    c = sample()
    c['fps'] = 24
    contract.validate(c)
    assert video_config.general_fps({}, {'fps': 24}) == 24
    c['fps'] = 30
    with pytest.raises(M2VError, match='24'):
        contract.validate(c)
    with pytest.raises(M2VError, match='24'):
        video_config.general_fps({}, {'fps': 30})


def test_contract_and_material_follow_live_frame_manifest(tmp_path, monkeypatch):
    path = tmp_path / 'frames.json'
    data = copy.deepcopy(frames.manifest())
    data['frames'] = [dict(width=1280, height=720, subtitle={
        'x': 0, 'y': 600, 'width': 1280, 'height': 120, 'fontSize': 32,
        'lineHeight': 1.5, 'textColor': '#ffffff', 'plateColor': '#000000'})]
    data['default'] = '1280x720'
    path.write_text(json.dumps(data), encoding='utf-8')
    monkeypatch.setattr(frames, 'manifest_path', lambda repo_root=None: path)
    c = sample()
    c.update(width=1280, height=720)
    contract.validate(c)
    assert frames.normalize(1280, 720) == (1280, 720)
    c.update(width=1920, height=1080)
    with pytest.raises(M2VError, match='1280x720'):
        contract.validate(c)
    # 同一进程再次编辑也可见，不能跨查询缓存旧配置。
    data['frames'][0]['width'] = 1920
    data['frames'][0]['height'] = 1080
    data['default'] = '1920x1080'
    path.write_text(json.dumps(data), encoding='utf-8')
    contract.validate(c)


@pytest.mark.parametrize('kind', sorted(policy.CORE_GATES))
def test_all_core_risks_require_review_and_appear_in_docs(kind):
    c = sample()
    c['reviewPlan']['risks'] = [{'id': 'risk', 'kind': kind, 'reason': '可见风险',
        'scope': {'checkpointIds': ['one-cp']}, 'requiredEvidence': ['完整窗口']}]
    if kind == 'structure-timing':
        c['scenes'][0]['shots'][0]['timeStructure'] = {'result': {
            'window': [0, 30], 'audience': '理解变化', 'visible': '结果',
            'attention': '主体', 'toleranceFrames': 0, 'failure': '未理解'}}
    contract.validate(c)
    assert policy.requirement(c, policy.CORE_GATES[kind], 'one-cp')['count'] == 1
    assert policy.rounds(c) == {'core': 1, 'rough': 1, 'final': 1, 'defaultCalls': 3}
    assert f'`{kind}`' in sync_docs.production_sections()['review-rounds'][0]


def test_workflow_dependency_and_phase_semantics():
    assert workflow.prerequisites('G0') == ()
    assert workflow.prerequisites('G5') == ('G0', 'G1', 'G2', 'G3', 'G4')
    assert workflow.phase('G4', rough_passed=False) == '粗片验证'
    assert workflow.phase('G4', rough_passed=True) == '精制修订'
    assert workflow.phase('G6', rough_passed=True) == '最终验收'
    with pytest.raises(M2VError):
        workflow.gate('G99')


def test_generated_production_docs_are_current_and_idempotent():
    outputs = sync_docs.build_outputs()
    for relative, generated in outputs.items():
        current, _ = sync_docs.read_text(relative)
        assert generated == current, relative
    text = outputs[sync_docs.CHECKPOINTS]
    for section, lines in sync_docs.production_sections().items():
        assert sync_docs._inject(sync_docs.CHECKPOINTS, text, lines, section=section) == text


def test_document_generator_reads_gate_source(monkeypatch):
    from dataclasses import replace
    changed = replace(workflow.GATES[0], evidence='独有来源证据')
    monkeypatch.setattr(workflow, 'GATES', (changed, *workflow.GATES[1:]))
    assert any('独有来源证据' in row for row in sync_docs.production_sections()['production-gates'])
