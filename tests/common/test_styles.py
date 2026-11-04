"""临时风格包验证注册、依赖与嵌套作品的构建边界。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from m2v.cli import main
from m2v.core import styles
from m2v.core.errors import M2VError
from m2v.core.project import create_project, file_inputs, load_current_prepared, load_project, save_prepared
from m2v.types.general.code_scenes import build_scene


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def package(tmp_path, monkeypatch):
    base = tmp_path / 'styles'
    root = base / 'test-style'
    root.mkdir(parents=True)
    monkeypatch.setattr(styles, 'STYLES_ROOT', base)
    (root / 'GUIDE.md').write_text('测试风格指导', encoding='utf-8')
    write_json(root / 'tokens.json', {'color': '#123456'})
    (root / 'piece.tsx').write_text("import React from 'react'; import {tokens} from 'm2v/style'; export default () => <div>{String(tokens.color)}</div>;", encoding='utf-8')
    (root / 'mark.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding='utf-8')
    manifest = {'schemaVersion': 1, 'id': root.name, 'version': '1.0.0', 'description': '测试',
                'types': ['general', 'financial-timeseries'], 'frames': [{'width': 1920, 'height': 1080}],
                'guide': 'GUIDE.md', 'tokens': 'tokens.json', 'components': {'piece': 'piece.tsx'},
                'assets': {'mark': {'path': 'mark.svg', 'source': 'original', 'license': 'MIT'}}}
    write_json(root / 'style.json', manifest)
    return root, manifest


@pytest.fixture
def project(tmp_path):
    root = tmp_path / 'work'
    create_project(root, 'financial-timeseries', {'source': 'source.json'})
    (root / 'source.json').write_text('{}', encoding='utf-8')
    _, manifest = load_project(root)
    manifest['output'].update(width=1920, height=1080)
    return root, manifest


def test_empty_registry_and_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(styles, 'STYLES_ROOT', tmp_path)
    assert main(['styles']) == 0
    assert '暂无已注册风格' in capsys.readouterr().out
    assert main(['styles', '--json']) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert styles.selected_style({'type': 'general'}) is None


def test_selection_and_compatibility(package):
    root, _ = package
    assert styles.list_styles()[0]['id'] == root.name
    selected = {'type': 'general', 'style': {'id': root.name}}
    assert styles.selected_style(selected, width=1920, height=1080)['tokens']['color'] == '#123456'
    for invalid in (None, {}, {'id': 'test-style', 'extra': 1}, {'id': '../test-style'}, {'id': 'missing'}):
        with pytest.raises(M2VError):
            styles.selected_style({'type': 'general', 'style': invalid})
    with pytest.raises(M2VError, match='类型'):
        styles.selected_style({**selected, 'type': 'unsupported'})
    with pytest.raises(M2VError, match='画幅'):
        styles.selected_style(selected, width=1080, height=1920)


@pytest.mark.parametrize('field,value', [('schemaVersion', True), ('version', 'v1'), ('id', 'other'),
    ('guide', '../outside.md'), ('guide', '.'), ('tokens', 'missing.json'), ('types', []), ('frames', []),
    ('assets', {'bad': {'path': 'mark.svg'}}), ('unknown', True)])
def test_invalid_package(package, field, value):
    root, manifest = package
    write_json(root / 'style.json', {**manifest, field: value})
    with pytest.raises(M2VError):
        styles.load_style(root.name)


@pytest.mark.parametrize('text', ['{"n":NaN}', '{"n":1e999}', '{"x":1,"x":2}', '[]'])
def test_tokens_reject_nonfinite_and_duplicate_values(package, text):
    root, _ = package
    (root / 'tokens.json').write_text(text, encoding='utf-8')
    with pytest.raises(M2VError):
        styles.load_style(root.name)


def test_style_change_during_preparation_rejected(package, project):
    style_root, _ = package
    root, manifest = project
    manifest['style'] = {'id': style_root.name}
    inputs = file_inputs(root, manifest)
    (style_root / 'GUIDE.md').write_text('changed', encoding='utf-8')
    with pytest.raises(M2VError, match='准备过程中变化'):
        save_prepared(root, project=manifest, composition_id='test', props={}, width=1920, height=1080,
                      fps=30, duration_in_frames=60, inputs=inputs)


def test_status_reports_selected_style(package, project, capsys):
    style_root, _ = package
    root, manifest = project
    manifest['style'] = {'id': style_root.name}
    write_json(root / 'project.json', manifest)
    assert main(['status', '--project', str(root)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['style']['version'] == '1.0.0'
    assert result['prepare']['status'] == 'stale-or-missing'


def test_prepared_rejects_actual_frame(package, project):
    style_root, _ = package
    root, manifest = project
    manifest['style'] = {'id': style_root.name}
    with pytest.raises(M2VError, match='画幅'):
        save_prepared(root, project=manifest, composition_id='test', props={}, width=1080, height=1920,
                      fps=30, duration_in_frames=60, inputs=file_inputs(root, manifest))


@pytest.mark.parametrize('changed', ['GUIDE.md', 'tokens.json', 'piece.tsx', 'mark.svg'])
def test_prepared_style_dependency(package, project, changed):
    style_root, _ = package
    root, manifest = project
    manifest['style'] = {'id': style_root.name}
    prepared = save_prepared(root, project=manifest, composition_id='test', props={}, width=1920, height=1080,
                            fps=30, duration_in_frames=60, inputs=file_inputs(root, manifest))
    assert prepared['style']['version'] == '1.0.0'
    assert load_current_prepared(root, manifest)['style'] == prepared['style']
    target = style_root / changed
    target.write_text(target.read_text(encoding='utf-8') + ' ', encoding='utf-8')
    with pytest.raises(M2VError, match='风格已变化'):
        load_current_prepared(root, manifest)


def test_unstyled_prepare_unchanged(project):
    root, manifest = project
    prepared = save_prepared(root, project=manifest, composition_id='test', props={}, width=1920, height=1080,
                            fps=30, duration_in_frames=60, inputs=file_inputs(root, manifest))
    assert 'style' not in prepared
    assert load_current_prepared(root, manifest) == prepared


@pytest.mark.slow
def test_scene_style_build_and_boundaries(package, project, tmp_path):
    style_root, _ = package
    root, manifest = project
    manifest.update(type='general', style={'id': style_root.name})
    write_json(root / 'project.json', manifest)
    scenes = root / 'scenes'
    scenes.mkdir()
    entry = scenes / 'main.tsx'
    scene = {'id': 'test', 'content': {'entry': 'scenes/main.tsx', 'props': {}}}
    work = tmp_path / 'build'
    work.mkdir()
    entry.write_text("import React from 'react'; import {tokens} from 'm2v/style'; import Piece from 'm2v/style/components/piece'; import mark from 'm2v/style/assets/mark'; export default () => <div style={{color:String(tokens.color)}}><Piece/><img src={mark}/></div>;", encoding='utf-8')
    first = build_scene(root, scene, work)
    assert first['style'] == styles.load_style(style_root.name)['identity']['fingerprint']
    assert '#123456' in (work / 'scene.js').read_text(encoding='utf-8')
    write_json(style_root / 'tokens.json', {'color': '#abcdef'})
    assert build_scene(root, scene, work)['style'] != first['style']
    for imported in ('m2v/style/components/missing', '../../../styles/test-style/piece', 'node:fs'):
        entry.write_text(f"import X from '{imported}'; export default X;", encoding='utf-8')
        with pytest.raises(M2VError, match='构建失败'):
            build_scene(root, scene, work)
    entry.write_text("export {default} from 'm2v/style/components/piece';", encoding='utf-8')
    (style_root / 'piece.tsx').write_text("import X from '../outside'; export default X;", encoding='utf-8')
    (style_root.parent / 'outside.ts').write_text('export default 1;', encoding='utf-8')
    with pytest.raises(M2VError, match='越界'):
        build_scene(root, scene, work)
    (style_root / 'hidden.svg').write_text('<svg/>', encoding='utf-8')
    (style_root / 'piece.tsx').write_text("import X from './hidden.svg'; export default () => X;", encoding='utf-8')
    with pytest.raises(M2VError, match='未登记的风格资产'):
        build_scene(root, scene, work)
    del manifest['style']
    write_json(root / 'project.json', manifest)
    entry.write_text("import {tokens,identity} from 'm2v/style'; export default () => String(identity)+String(tokens);", encoding='utf-8')
    assert 'style' not in build_scene(root, scene, work)
    entry.write_text("export {default} from 'm2v/style/components/piece';", encoding='utf-8')
    with pytest.raises(M2VError, match='未登记的风格入口'):
        build_scene(root, scene, work)


def test_style_file_symlink_rejected(package, tmp_path):
    root, _ = package
    outside = tmp_path / 'outside.txt'
    outside.write_text('outside', encoding='utf-8')
    try:
        (root / 'link.txt').symlink_to(outside)
    except OSError:
        pytest.skip('当前 Windows 用户没有创建符号链接权限')
    with pytest.raises(M2VError, match='符号链接|越界'):
        styles.load_style(root.name)


@pytest.mark.parametrize('field,path', [
    ('guide', 'examples/demo/GUIDE.md'),
    ('tokens', 'examples/demo/tokens.json'),
    ('components', 'examples/demo/piece.tsx'),
    ('assets', 'examples/demo/mark.svg'),
])
def test_shared_manifest_cannot_register_example_files(package, field, path):
    root, manifest = package
    target = root / path
    target.parent.mkdir(parents=True)
    target.write_text('{}', encoding='utf-8')
    value = path
    if field == 'components':
        value = {'piece': path}
    elif field == 'assets':
        value = {'mark': {'path': path, 'source': 'original', 'license': 'MIT'}}
    write_json(root / 'style.json', {**manifest, field: value})
    with pytest.raises(M2VError, match='不能引用示例'):
        styles.load_style(root.name)


def test_example_tree_is_pruned_without_reading_or_hashing(package, monkeypatch):
    root, _ = package
    before = styles.load_style(root.name)['identity']['fingerprint']
    example = root / 'examples/demo'
    for relative in ('scene.tsx', 'assets/media/large.png', 'outputs/video.mp4'):
        target = example / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'not a shared dependency')
    original_walk = styles.os.walk
    visited = []

    def checked_walk(path):
        for directory, dirs, files in original_walk(path):
            visited.append(Path(directory))
            assert not Path(directory).is_relative_to(root / 'examples')
            yield directory, dirs, files

    monkeypatch.setattr(styles.os, 'walk', checked_walk)
    assert styles.load_style(root.name)['identity']['fingerprint'] == before
    assert root in visited
    (example / 'scene.tsx').write_text('changed', encoding='utf-8')
    (example / 'outputs/video.mp4').unlink()
    assert styles.load_style(root.name)['identity']['fingerprint'] == before
    # 非示例目录中的未登记共享文件仍然参与哈希。
    (root / 'unregistered.ts').write_text('export const x = 1;', encoding='utf-8')
    assert styles.load_style(root.name)['identity']['fingerprint'] != before


def test_nested_example_build_preserves_project_and_style_boundaries(package, tmp_path):
    style_root, _ = package
    root = style_root / 'examples/demo'
    create_project(root, 'general', {'storyboard': 'storyboard.json'})
    _, manifest = load_project(root)
    manifest['style'] = {'id': style_root.name}
    write_json(root / 'project.json', manifest)
    scenes = root / 'scenes'
    scenes.mkdir()
    entry = scenes / 'main.tsx'
    (scenes / 'local.tsx').write_text('export default () => null;', encoding='utf-8')
    (scenes / 'own.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding='utf-8')
    scene = {'id': 'nested', 'content': {'entry': 'scenes/main.tsx', 'props': {}}}
    work = tmp_path / 'build-nested'
    work.mkdir()
    entry.write_text("import Piece from 'm2v/style/components/piece'; import Local from './local'; import img from './own.svg'; export default () => <div><Piece/><Local/><img src={img}/></div>;", encoding='utf-8')
    first = build_scene(root, scene, work)
    # 原作品的相对 SVG 不能被错误当作未登记的风格资产。
    assert 'data:image/svg+xml' in (work / 'scene.js').read_text(encoding='utf-8')
    (scenes / 'local.tsx').write_text('export default () => <span>changed</span>;', encoding='utf-8')
    assert build_scene(root, scene, work) != first
    sibling = style_root / 'examples/other'
    sibling.mkdir()
    (sibling / 'piece.tsx').write_text('export default () => null;', encoding='utf-8')
    for imported in ('../../../piece', '../../other/piece'):
        entry.write_text(f"export {{default}} from '{imported}';", encoding='utf-8')
        with pytest.raises(M2VError, match='作品.*越界'):
            build_scene(root, scene, work)
    entry.write_text("export {default} from 'm2v/style/components/piece';", encoding='utf-8')
    (style_root / 'piece.tsx').write_text("export {default} from './examples/other/piece';", encoding='utf-8')
    with pytest.raises(M2VError, match='风格.*越界'):
        build_scene(root, scene, work)


def test_nested_example_symlink_cannot_escape_its_project(package, tmp_path):
    style_root, _ = package
    root = style_root / 'examples/demo'
    create_project(root, 'general', {'storyboard': 'storyboard.json'})
    _, manifest = load_project(root)
    manifest['style'] = {'id': style_root.name}
    write_json(root / 'project.json', manifest)
    scenes = root / 'scenes'
    scenes.mkdir()
    try:
        (scenes / 'escape.tsx').symlink_to(style_root / 'piece.tsx')
    except OSError:
        pytest.skip('当前 Windows 用户没有创建符号链接权限')
    (scenes / 'main.tsx').write_text("export {default} from './escape';", encoding='utf-8')
    work = tmp_path / 'build-symlink'
    work.mkdir()
    scene = {'id': 'nested', 'content': {'entry': 'scenes/main.tsx', 'props': {}}}
    with pytest.raises(M2VError, match='作品.*越界'):
        build_scene(root, scene, work)


@pytest.mark.slow
def test_style_runtime_and_clip_cache(package, tmp_path, chromium_ready):
    from helpers.general import board, project as general_project
    from m2v.core import frames
    from m2v.types.general.code_scenes import record
    from helpers.general import code_scene, write_source
    style_root, _ = package
    root, manifest = general_project(tmp_path / 'content', board())
    manifest['style'] = {'id': style_root.name}
    write_json(root / 'project.json', manifest)
    write_source(root, 'scenes/demo.tsx', """
import React, {useEffect} from 'react';
import {useSceneContext} from 'm2v/code-scene';
import {tokens, identity} from 'm2v/style';
import Piece from 'm2v/style/components/piece';
import mark from 'm2v/style/assets/mark';
export default function Demo() {
 const {ready} = useSceneContext();
 useEffect(() => {
   if (identity?.id !== 'test-style' || tokens.color !== '#123456' || !Object.isFrozen(tokens)) throw new Error('风格参数错误');
   ready();
 }, []);
 return <div style={{width:'100%',height:'100%',background:String(tokens.color)}}><Piece/><img src={mark}/></div>;
}
""")
    scene = code_scene()
    scene.update(startFrame=0, durationInFrames=2, segmentWindows={})
    inputs = {}
    first = record(root, scene, inputs, frame=frames.spec(1920, 1080), media={}, media_digest='empty', fps=30)
    assert (root / first).is_file()
    assert record(root, scene, {}, frame=frames.spec(1920, 1080), media={}, media_digest='empty', fps=30) == first
    (style_root / 'GUIDE.md').write_text('指导变化', encoding='utf-8')
    changed = record(root, scene, {}, frame=frames.spec(1920, 1080), media={}, media_digest='empty', fps=30)
    assert changed != first and (root / changed).is_file()
