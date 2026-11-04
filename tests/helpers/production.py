"""制作合同与可编辑作品的共用夹具；不反向导入测试模块。"""
import json
from m2v.core.delivery import outputs
from m2v.production.storage import write


def sample():
    return {'version': 2, 'cycleId': 'test-cycle', 'fps': 30, 'width': 1920, 'height': 1080,
            'reviewPlan': {'basis': '基础布局无核心未决风险', 'risks': []},
            'scenes': [{'id': sid, 'durationFrames': 30,
                'shots': [{'id': sid + '-shot', 'tier': 'B', 'window': [0, 30]}],
                'checkpoints': [{'id': sid + '-cp', 'shotId': sid + '-shot', 'frame': 15, 'window': [0, 30],
                    'expected': [{'role': 'disc', 'count': 2}], 'textPlan': [], 'claims': [], 'forbidden': []}]} for sid in ('one', 'two')]}


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
