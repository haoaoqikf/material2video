"""作品本地 lookdev 静帧的合成 props 与路径边界。"""
from pathlib import Path

import pytest

from film_runtime.core.errors import VideoError
from film_runtime.engine import lookdev


def test_still_props_keep_only_captured_scene_and_serve_relative(tmp_path):
    root = tmp_path / 'project'
    picture = root / 'outputs/lookdev/frame-000010.png'
    picture.parent.mkdir(parents=True)
    picture.write_bytes(b'png')
    prepared = {'props': {'compiledScenes': [
        {'id': 'a', 'startFrame': 0, 'endFrame': 20},
        {'id': 'b', 'startFrame': 20, 'endFrame': 40}]}}
    props = lookdev.still_props(root, prepared, {('a', 10): picture}, 10, 'http://media/')
    assert [scene['id'] for scene in props['compiledScenes']] == ['a']
    assert props['compiledScenes'][0]['stillPath'] == 'http://media/outputs/lookdev/frame-000010.png'
    assert props['mediaBase'] == 'http://media/'
    assert [scene['id'] for scene in prepared['props']['compiledScenes']] == ['a', 'b']


def test_still_props_reject_outside_project(tmp_path):
    root = tmp_path / 'project'
    root.mkdir()
    outside = tmp_path / 'outside.png'
    outside.write_bytes(b'png')
    prepared = {'props': {'compiledScenes': [{'id': 'a', 'startFrame': 0, 'endFrame': 20}]}}
    with pytest.raises(VideoError, match='越过作品'):
        lookdev.still_props(root, prepared, {('a', 10): outside}, 10, 'http://media/')


def test_native_stills_failure_identifies_scene_and_preserves_cause(tmp_path, monkeypatch):
    from contextlib import nullcontext
    import playwright.sync_api
    from film_runtime.types.scene_film import code_scenes, media_assets

    prepared = {'width': 1920, 'height': 1080, 'fps': 30, 'props': {
        'subtitle': {}, 'compiledScenes': [
            {'id': 'knowledge', 'startFrame': 300, 'endFrame': 330,
             'content': {'entry': 'scenes/knowledge.tsx'}}]}}
    monkeypatch.setattr(playwright.sync_api, 'sync_playwright', lambda: nullcontext(object()))
    monkeypatch.setattr(media_assets, 'resolve', lambda root: {'media': {}})
    monkeypatch.setattr(code_scenes, 'build_scene', lambda *args: None)
    monkeypatch.setattr(code_scenes, 'scene_config', lambda *args, **kwargs: {})
    cause = VideoError('origin.x 必须是有限数值')

    def fail(*args, **kwargs):
        raise cause

    monkeypatch.setattr(code_scenes, '_capture', fail)
    with pytest.raises(VideoError, match='knowledge.*scenes/knowledge.tsx.*origin.x') as caught:
        lookdev.native_stills(tmp_path, prepared, [310], tmp_path)
    assert caught.value.__cause__ is cause
    assert not list(tmp_path.rglob('frame-*.png'))
