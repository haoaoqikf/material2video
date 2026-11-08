"""设计检查只保护身份、局部范围与路径，不猜测设计质量。"""
import json
from pathlib import Path

import pytest

import check_scene_design as design
from m2v.core.errors import M2VError


@pytest.fixture
def work(tmp_path):
    (tmp_path / 'project.json').write_text(json.dumps(dict(schemaVersion=2, id='design-test',
        type='text-motion', materials={'storyboard': 'storyboard.json'})), encoding='utf-8')
    (tmp_path / 'storyboard.json').write_text(json.dumps({'scenes': [{'id': 'a'}, {'id': 'b'}]}), encoding='utf-8')
    (tmp_path / 'design/scenes').mkdir(parents=True)
    (tmp_path / 'DESIGN.md').write_text('# 当前设计\n[a](design/scenes/a.md)\n[b](design/scenes/b.md)\n', encoding='utf-8')
    for scene_id in ('a', 'b'):
        (tmp_path / f'design/scenes/{scene_id}.md').write_text(f'# {scene_id}\n当前假设，效果未验证。', encoding='utf-8')
    return tmp_path


def test_complete_checks_identity_without_claiming_quality(work):
    result = design.validate(work)
    assert result['scenes'] == ['a', 'b'] and result['scope'] == 'complete'
    assert '仅结构' in result['meaning']


def test_partial_allows_unwritten_other_scene_but_full_rejects(work):
    (work / 'design/scenes/b.md').unlink()
    assert design.validate(work, ['a'])['scenes'] == ['a']
    with pytest.raises(M2VError):
        design.validate(work)


@pytest.mark.parametrize('change,match', [
    ('duplicate', '重复'), ('mismatch', '错配'), ('escape', '越界'),
    ('empty', '为空'), ('orphan', '不属于'), ('missing_link', '不存在'),
    ('anchor', '锚点不存在'), ('protocol', '协议'), ('fence', '未闭合'),
])
def test_rejects_broken_correspondence(work, change, match):
    path = work / 'DESIGN.md'
    value = path.read_text(encoding='utf-8')
    if change == 'duplicate':
        value += '\n[a](design/scenes/a.md)'
    elif change == 'mismatch':
        value = value.replace('[a](design/scenes/a.md)', '[a](design/scenes/b.md)')
    elif change == 'escape':
        value = value.replace('design/scenes/a.md', '../outside.md')
    elif change == 'empty':
        (work / 'design/scenes/a.md').write_text(' \n', encoding='utf-8')
    elif change == 'orphan':
        (work / 'design/scenes/orphan.md').write_text('过去', encoding='utf-8')
    elif change == 'missing_link':
        value += '\n[证据](missing.png)'
    elif change == 'anchor':
        value += '\n[段落](design/scenes/a.md#不存在)'
    elif change == 'protocol':
        value += '\n[文件](file:///outside.md)'
    else:
        value += '\n```markdown\n'
    path.write_text(value, encoding='utf-8')
    with pytest.raises(M2VError, match=match):
        design.validate(work)


def test_templates_are_not_active_indexes(work):
    path = work / 'DESIGN.md'
    path.write_text(path.read_text(encoding='utf-8') + '\n~~~markdown\n[x](design/scenes/x.md)\n~~~\n', encoding='utf-8')
    design.validate(work)


def test_unknown_scene_and_nonzero_cli_failure(work, capsys):
    with pytest.raises(M2VError, match='未知'):
        design.validate(work, ['unknown'])
    assert design.main(['--project', str(work), '--scene', 'unknown']) == 1
    assert '[error]' in capsys.readouterr().err


def test_scene_id_cannot_be_a_path(work):
    (work / 'storyboard.json').write_text(json.dumps({'scenes': [{'id': '../a'}]}), encoding='utf-8')
    with pytest.raises(M2VError, match='文件名'):
        design.validate(work)


def test_partial_isolated_from_other_indexes_and_allows_pending_neighbor(work):
    (work / 'design/scenes/b.md').unlink()
    path = work / 'DESIGN.md'
    path.write_text(path.read_text(encoding='utf-8') + '\n[b](design/scenes/a.md)', encoding='utf-8')
    scene = work / 'design/scenes/a.md'
    scene.write_text(scene.read_text(encoding='utf-8') + '\n入口见[b](b.md)', encoding='utf-8')
    design.validate(work, ['a'])
    with pytest.raises(M2VError):
        design.validate(work)


def test_partial_does_not_skip_path_escape_in_detail_link(work):
    path = work / 'DESIGN.md'
    path.write_text(path.read_text(encoding='utf-8') + '\n[detail](design/scenes/../../../../outside.md#missing)', encoding='utf-8')
    with pytest.raises(M2VError, match='不存在或越界'):
        design.validate(work, ['a'])


def test_reference_links_cannot_silently_bypass_evidence_check(work):
    path = work / 'design/scenes/a.md'
    path.write_text('# 场景\n[证据][source]\n\n[source]: missing.png', encoding='utf-8')
    with pytest.raises(M2VError, match='内联链接'):
        design.validate(work)


@pytest.mark.parametrize('ids', [['a', 'A'], ['CON'], ['LPT1']])
def test_scene_filenames_are_portable_and_distinct(work, ids):
    (work / 'storyboard.json').write_text(json.dumps({'scenes': [{'id': i} for i in ids]}), encoding='utf-8')
    with pytest.raises(M2VError, match='文件名'):
        design.validate(work)


@pytest.mark.parametrize('link', ['![](missing.png)', '<img src="missing.png">', '<a href="missing.md">证据</a>'])
def test_image_and_html_references_do_not_silently_pass(work, link):
    path = work / 'design/scenes/a.md'
    path.write_text('# 当前设计\n' + link, encoding='utf-8')
    with pytest.raises(M2VError):
        design.validate(work)


def test_all_seven_examples_have_current_scene_correspondence():
    from helpers.examples import EXAMPLE_PATHS
    for root in EXAMPLE_PATHS.values():
        assert design.validate(root)['scope'] == 'complete'
