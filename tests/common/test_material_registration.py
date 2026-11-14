"""显式候选、静态网页和 locator 隔离；不启动浏览器、不连接外网。"""
from __future__ import annotations

from email.message import Message
import io
import json
import socket
import subprocess
from types import SimpleNamespace

import pytest

from m2v.materials import registration
from m2v.materials.contracts import IdentityConstraint, Requirement, RequirementData
from m2v.materials.errors import MaterialError
from m2v.materials.registration import file_stamp, register_local, register_url, source_gap
from m2v.materials.source_catalog import put_source
from m2v.materials.store import MaterialStore
from m2v.materials.webpage import WebpageProvider, parse_page


class HTTP:
    budget = SimpleNamespace(max_bytes=2*1024*1024)
    def __init__(self, body, url='https://publisher.example/story', content_type='text/html'):
        self.body, self.url, self.content_type, self.calls = body, url, content_type, []
    def check(self):
        pass
    def open(self, url, **kwargs):
        self.calls.append((url, kwargs))
        raw = io.BytesIO(self.body.encode() if isinstance(self.body, str) else self.body)
        raw.url, raw.headers = self.url, Message()
        raw.headers['Content-Type'] = self.content_type
        return raw


def test_registration_is_offline_and_local_snapshot_contains_no_private_parent(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('registration must not use network or child processes')
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    folder = tmp_path / 'private-parent'
    folder.mkdir()
    source = folder / 'movie.mp4'
    source.write_bytes(b'not-yet-probed')
    with MaterialStore(tmp_path / 'work') as store:
        first = register_local(source, store=store)
        again = register_local(source, store=store)
        assert first.document == again.document
        assert first.document.data.variants[0].kind == 'unknown'
        assert first.stamp == file_stamp(source) and first.locator == source
        assert str(folder) not in first.document.model_dump_json() and str(folder) not in repr(first)
        assert list((store.root / 'objects').iterdir()) == []
        assert list(store.documents(kind='material.media')) == []
        public = register_url('https://publisher.example/story?v=12', store=store)
        assert public.document.data.state == 'registered' and not public.document.data.variants
        changed = register_local(source, title='<b></b>')
        assert changed.document.data.title == source.name
        source.write_bytes(b'new-longer-bytes')
        assert file_stamp(source) != first.stamp


@pytest.mark.parametrize('value', [r'\\server\share\movie.mp4', r'\\.\pipe\movie', 'foo:secret', 'relative/foo:secret'])
def test_unc_device_ads_rejected_before_filesystem_lookup(value, monkeypatch):
    monkeypatch.setattr(registration, 'no_links', lambda *a, **kw: pytest.fail('must reject before lstat'))
    with pytest.raises(MaterialError) as error:
        register_local(value)
    assert error.value.code == 'security-blocked'


def test_missing_empty_and_directory_are_not_media_candidates(tmp_path):
    empty = tmp_path / 'empty.mp4'
    empty.touch()
    for path in (empty, tmp_path, tmp_path / 'absent.mp4'):
        with pytest.raises(MaterialError) as error:
            register_local(path)
        assert str(tmp_path) not in str(error.value)


def test_sensitive_locator_only_in_call_and_unknown_resources_not_falsely_merged(tmp_path):
    value = 'https://publisher.example/download?token=DO-NOT-PERSIST'
    with MaterialStore(tmp_path / 'work') as store:
        first = register_url(value, store=store, mode='file')
        other = register_url(value.replace('DO-NOT-PERSIST', 'ANOTHER'), store=store, mode='file')
        assert first.document.id != other.document.id
        assert first.document.data.externalId is None and first.document.data.state == 'limited'
        assert first.document.data.variants[0].url is None
        assert 'DO-NOT-PERSIST' not in repr(first) + first.document.model_dump_json()
        assert first.locator == value
    flag = register_url('https://publisher.example/download?private', mode='file')
    assert flag.document.data.externalId is None and flag.document.data.variants[0].url is None
    opaque = register_url('https://publisher.example/' + 'a'*120, mode='file')
    assert opaque.document.data.sourceUrl is None and opaque.document.data.externalId is None
    assert 'a'*120 not in opaque.document.model_dump_json()


@pytest.mark.parametrize('value', ['file:///C:/private/x.mp4', 'javascript:alert(1)', 'http://name:secret@example.org/x'])
def test_url_registration_does_not_accept_implicit_files_or_credentials(value):
    with pytest.raises(MaterialError):
        register_url(value)


def test_static_parser_resolves_base_and_media_but_never_executes_scripts_or_iframes():
    body = b'''<base href="https://cdn.example/media/"><base href="https://other.example/">
      <title>Actual title</title><video poster="poster.jpg"><source src="movie.mp4" type="video/mp4">
      <track src="captions.vtt"></video><audio src="sound.mp3"></audio>
      <img src="picture.jpg" width="640" height="360" srcset="other.jpg 2x">
      <script>document.write('<video src="never.mp4">');</script>
      <iframe src="https://embedded.example/player"></iframe><img src="javascript:alert(1)">'''
    page = parse_page(body, 'https://publisher.example/story')
    assert {entry.kind for entry in page.assets} == {'image', 'video', 'audio', 'subtitle'}
    assert all(entry.url.startswith('https://cdn.example/media/') for entry in page.assets)
    assert not any('never.mp4' in entry.url or 'embedded.example' in entry.url for entry in page.assets)
    assert page.limitations and page.metadata['title'] == 'Actual title'


def test_jsonld_nested_itemlist_metadata_and_budgets():
    data = {'@type': 'ItemList', 'itemListElement': [{'item': {'@type': 'VideoObject', 'name': '原始标题',
        'contentUrl': 'movie.mp4?signature=DO-NOT-PERSIST', 'thumbnailUrl': ['preview.jpg'],
        'author': {'name': 'Actual Author'}, 'license': 'CC BY 4.0', 'uploadDate': '2024'}}]}
    page = parse_page(('<script type="application/ld+json">' + json.dumps(data) + '</script>').encode(), 'https://publisher.example/story')
    assert page.metadata['author'] == 'Actual Author' and page.metadata['published'] == '2024'
    assert [entry.kind for entry in page.assets] == ['video', 'image']
    oversized = parse_page(b'<img src="1.jpg"><img src="2.jpg"><img src="3.jpg">', 'https://publisher.example/', max_assets=2)
    assert len(oversized.assets) == 2 and oversized.limitations
    invalid = parse_page(b'<script type="application/ld+json">{"x":NaN}</script>', 'https://publisher.example/')
    assert not invalid.assets and invalid.limitations
    deep = {'item': {'@type': 'VideoObject', 'contentUrl': 'hidden.mp4'}}
    for _ in range(10):
        deep = {'item': deep}
    limited = parse_page(('<script type="application/ld+json">' + json.dumps(deep) + '</script>').encode(), 'https://publisher.example/')
    assert not limited.assets and limited.limitations


def test_page_resolution_separates_signed_locators_and_keeps_manual_metadata(monkeypatch):
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: pytest.fail('static page must not launch a browser'))
    body = '''<title>Page title</title><meta name="author" content="Page Author"><meta property="og:site_name" content="Publisher">
      <video src="https://cdn.example/movie.mp4?signature=DO-NOT-PERSIST"></video>
      <link rel="license" href="/terms"><meta name="description" content="Authorization: DO-NOT-PERSIST">'''
    http = HTTP(body)
    original = register_url('https://publisher.example/story', author='Explicit Author').document.data
    result = WebpageProvider(http).resolve(original)
    assert len(http.calls) == 1 and result.source.author == 'Explicit Author'
    assert result.source.license == 'https://publisher.example/terms'
    assert result.source.policy.publisher == 'Publisher'
    assert result.source.variants[0].url is None and result.locators['video-0'].endswith('DO-NOT-PERSIST')
    assert 'DO-NOT-PERSIST' not in result.source.model_dump_json() + repr(result)
    assert result.source.policy.usage.status == 'not-checked'


def test_page_only_and_temporary_page_requirements_do_not_guess_a_resource():
    http = HTTP('<title>Only a page</title><input type="password">')
    provider = WebpageProvider(http)
    data = register_url('https://publisher.example/story').document.data
    result = provider.resolve(data)
    assert result.source.state == 'limited' and not result.locators and result.source.limitations
    private = register_url('https://publisher.example/story?token=DO-NOT-PERSIST').document.data
    with pytest.raises(MaterialError) as error:
        provider.resolve(private)
    assert error.value.code == 'locator-required' and len(http.calls) == 1
    provider.resolve(private, locator='https://publisher.example/story?token=DO-NOT-PERSIST')
    assert len(http.calls) == 2
    with pytest.raises(MaterialError) as changed:
        provider.resolve(data, locator='https://other.example/another-page')
    assert changed.value.code == 'source-changed' and len(http.calls) == 2


def test_parser_does_not_expand_external_entities_or_allow_deep_media(tmp_path):
    hidden = tmp_path / 'private.txt'
    hidden.write_text('DO-NOT-DISCLOSE', encoding='utf-8')
    body = ('<!DOCTYPE html [<!ENTITY hidden SYSTEM "' + hidden.as_uri() + '">]><title>&hidden;</title>').encode()
    try:
        result = parse_page(body, 'https://publisher.example/')
    except MaterialError as error:
        assert error.code in {'security-blocked', 'invalid-response'}
    else:
        assert 'DO-NOT-DISCLOSE' not in str(result.metadata)
    with pytest.raises(MaterialError) as error:
        parse_page(b'<video>'*100 + b'</video>'*100, 'https://publisher.example/')
    assert error.value.code == 'resource-limit'


def test_parser_encoding_type_and_title_limits():
    parsed = parse_page('<title>中文标题</title>'.encode('gb18030'), 'https://publisher.example/', content_type='text/html;charset=gb18030')
    assert parsed.metadata['title'] == '中文标题'
    unknown_encoding = parse_page(b'<title>\xff</title>', 'https://publisher.example/')
    assert unknown_encoding.limitations
    fragmented = parse_page(('<title>' + '<b>x</b>'*18000 + '</title>').encode(), 'https://publisher.example/')
    assert len(fragmented.metadata['title']) < 18000
    for body, content_type in ((b'x', 'video/mp4'), (b'x'*(2*1024*1024+1), 'text/html')):
        with pytest.raises(MaterialError):
            parse_page(body, 'https://publisher.example/', content_type=content_type)


def test_shared_source_publication_preserves_refs_and_immutable_time(tmp_path):
    with MaterialStore(tmp_path / 'work') as store:
        requirement = Requirement(id='r1', data=RequirementData(text='actual scene'))
        store.put(requirement)
        registered = register_url('https://publisher.example/story', store=store, references=['r1'])
        again = put_source(store, registered.document.data, ['r1'])
        assert registered.document == again
        assert store.connection.execute('SELECT target FROM refs WHERE owner=?', (again.id,)).fetchone()[0] == 'r1'


def test_gap_advice_preserves_identity_and_adds_process_warning_without_auto_adoption():
    simple = Requirement(id='r1', data=RequirementData(text='scene', identity=IdentityConstraint(entity='ACME', mustMatch=True)))
    process = simple.model_copy(deep=True)
    process.data.task = 'process'
    assert any('ACME' in item for item in source_gap(simple))
    assert len(source_gap(process)) > len(source_gap(simple))
