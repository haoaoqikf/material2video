"""显式库登记、清理计划与九条工作流的路由/退出码。"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
import pytest

from m2v.materials import cli, library
from m2v.materials.errors import MaterialError
from m2v.materials.store import MaterialStore


def _image(path: Path, color):
    Image.new('RGB', (32, 24), color=color).save(path, format='PNG')


@pytest.mark.media
def test_scan_dedupes_bytes_but_keeps_sources_and_cleanup_protects(tmp_path):
    folder = tmp_path / 'media'
    folder.mkdir()
    _image(folder / 'first.png', 'navy')
    (folder / 'second.png').write_bytes((folder / 'first.png').read_bytes())
    (folder / 'notes.txt').write_text('ignore', encoding='utf-8')
    with MaterialStore(tmp_path / 'library') as store:
        result = library.scan_directory(store, folder)
        assert result['files'] == 2 and result['duplicateContents']
        assert len(result['sourceIds']) == 2 and len(result['mediaIds']) == 2
        assert store.connection.execute('SELECT count(*) FROM artifacts').fetchone()[0] == 1
        sources = store.documents('material.source')
        assert all(item.data.provider == 'local' and item.data.policy.usage.status == 'not-checked'
                   for item in sources)
        assert library.verify_library(store)['ok'] is True
        stats = library.stats(store)
        assert stats['documents']['material.media'] == 2 and stats['artifacts'] == 1
        orphan = store.publish_bytes(b'orphan-object')
        plan = library.cleanup_plan(store)
        assert [item['sha256'] for item in plan['unboundArtifacts']] == [orphan.sha256]
        with pytest.raises(MaterialError) as stale:
            library.apply_cleanup(store, 'f' * 64)
        assert stale.value.code == 'conflict'
        applied = library.apply_cleanup(store, plan['digest'])
        assert applied['deleted'] >= 1
        assert not store.connection.execute('SELECT 1 FROM artifacts WHERE sha256=?',
                                            (orphan.sha256,)).fetchone()
        assert library.verify_library(store)['ok'] is True
        assert len(store.documents('material.media')) == 2
        with pytest.raises(MaterialError) as blocked:
            library.scan_directory(store, Path.home())
        assert blocked.value.code == 'security-blocked'


@pytest.mark.media
def test_scan_rescans_idempotently(tmp_path):
    folder = tmp_path / 'media'
    folder.mkdir()
    _image(folder / 'only.png', 'teal')
    with MaterialStore(tmp_path / 'library') as store:
        first = library.scan_directory(store, folder)
        second = library.scan_directory(store, folder)
        assert first['mediaIds'] == second['mediaIds']
        assert len(store.documents('material.source')) == 1
        assert len(store.documents('material.media')) == 1


def test_cli_routes_new_workflows_and_maps_exit_codes(tmp_path, capsys):
    workspace = str(tmp_path / 'workspace')
    assert cli.main(['doctor', '--workspace', workspace, '--json']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['performed']['network'] is False
    assert cli.main(['models', 'list', '--workspace', workspace, '--json']) == 0
    assert cli.main(['models', 'verify', '--workspace', workspace, '--name', 'whisper-small']) == 2
    assert cli.main(['library', 'stats', '--workspace', workspace, '--json']) == 0
    assert cli.main(['find', '--workspace', workspace, '--query', '城市夜景', '--json']) == 0
    assert cli.main(['fetch', '--workspace', workspace]) == 2
    assert cli.main(['index', '--workspace', workspace, '--media', 'media-missing']) == 2
    assert cli.main(['discover', '--project', str(tmp_path / 'missing')]) == 2
    assert cli.main(['find', '--workspace', workspace, '--query', 'https://example.com/x']) == 2


def test_legacy_assets_route_hands_new_workflows_to_materials_cli(tmp_path, capsys):
    from m2v.types.scene_film import media_assets
    assert media_assets.main(['doctor', '--workspace', str(tmp_path / 'workspace'), '--json']) == 0
    assert 'performed' in capsys.readouterr().out
