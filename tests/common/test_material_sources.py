"""原生来源解析/隐私/分页；不发真实网络请求，也不把声明规格当实测。"""
from __future__ import annotations

from email.message import Message
import io
import json
import socket
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from pydantic import ValidationError

from m2v.materials.contracts import Query, SourceData
from m2v.materials.errors import MaterialError
from m2v.materials.discovery import discover
from m2v.materials.network import NetworkBudget, SafeHTTP
from m2v.materials.gallery_source import PixabayProvider
from m2v.materials.public_sources import ArchiveProvider, CommonsProvider, NasaProvider
from m2v.materials.source_types import media_url, page_url, source, text, variant


class HTTP:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []
        self.budget = SimpleNamespace(timeout_s=3, max_bytes=8*1024*1024)

    def get_json(self, url, **kwargs):
        self.calls.append((url, kwargs))
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def commons_page(url='https://upload.wikimedia.org/wikipedia/commons/clip.webm'):
    return {'pageid': 12, 'title': 'File:Robot.webm', 'imageinfo': [{
        'url': url, 'descriptionurl': 'https://commons.wikimedia.org/wiki/File:Robot.webm',
        'mime': 'video/webm', 'width': 1280, 'height': 720, 'size': 12345,
        'extmetadata': {'Artist': {'value': '<a href="https://example.org">Alice</a>'},
            'LicenseShortName': {'value': 'CC BY 4.0'}, 'ImageDescription': {'value': '<p>Robot</p><p>arm</p>'}}}]}


def nasa_item():
    return {'data': [{'nasa_id': 'Artemis Origins', 'title': 'Artemis', 'media_type': 'video',
                     'date_created': '2022-09-01T12:00:00Z', 'center': 'KSC'}],
            'links': [{'render': 'image', 'href': 'https://images-assets.nasa.gov/video/Artemis Origins/preview.jpg'}]}


def test_small_shared_network_budget_is_respected_and_traffic_not_double_counted():
    payloads = [{'collection': {'items': [nasa_item()], 'metadata': {'total_hits': 1}}},
                {'query': {'pages': [commons_page()]}}]
    bodies = [json.dumps(value).encode() for value in payloads]
    expected = sum(map(len, bodies))
    def transport(*args):
        raw = io.BytesIO(bodies.pop(0))
        raw.status, raw.headers = 200, Message()
        return raw, lambda: None
    http = SafeHTTP(NetworkBudget(max_bytes=1024, total_bytes=4096, retries=0),
        resolver=lambda host, port, **kw: [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', port))],
        transport=transport)
    result = discover(selected=[NasaProvider(http), CommonsProvider(http)], queries=[Query(text='robot')], page_size=1)
    assert result.exit_code == 0 and len(result.sources) == 2
    assert result.stats['requests'] == 2 and result.stats['bytes'] == expected


def test_commons_pagination_specs_plain_author_and_no_observation_promotion():
    http = HTTP({'query': {'pages': [commons_page()]}, 'continue': {'gsroffset': 20}})
    page = CommonsProvider(http).search('机械臂', kind='video', limit=20)
    item = page.items[0]
    assert item.externalId == '12' and item.author == 'Alice' and item.license == 'CC BY 4.0'
    assert item.policy.description == 'Robot arm' and item.policy.usage.status == 'not-checked'
    assert item.variants[0].width == 1280 and item.variants[0].bytes == 12345
    assert item.state == 'discovered' and page.cursor == '20'
    arguments = parse_qs(urlsplit(http.calls[0][0]).query)
    assert arguments['gsrsearch'] == ['filetype:video 机械臂'] and arguments['gsroffset'] == ['0']
    assert 'probe' not in item.model_dump() and 'observations' not in item.model_dump()


def test_commons_page_only_candidate_and_additional_rights_are_not_dropped():
    raw = commons_page()
    raw['imageinfo'][0]['extmetadata']['Restrictions'] = {'value': 'Keep original context'}
    http = HTTP({'query': {'pages': [raw, {'pageid': 99, 'title': 'File:Missing.webm'}]}},
                {'query': {'pages': [{'pageid': 99, 'title': 'File:Missing.webm'}]}})
    provider = CommonsProvider(http)
    page = provider.search('robot', kind='video', limit=2)
    assert 'Keep original context' in page.items[0].license
    assert not page.items[1].variants and page.items[1].limitations and page.items[1].license == '未知'
    with pytest.raises(MaterialError) as error:
        provider.resolve(page.items[1])
    assert error.value.code == 'metadata-unavailable'


def test_commons_signed_locator_only_in_ephemeral_resolution():
    raw = commons_page('https://cdn.example.org/a.webm?signature=SECRET')
    http = HTTP({'query': {'pages': [raw]}}, {'query': {'pages': [raw]}})
    provider = CommonsProvider(http)
    original = provider.search('robot', kind='video', limit=1).items[0]
    assert original.variants[0].url is None
    resolved = provider.resolve(original)
    assert 'SECRET' in resolved.locators['original']
    assert 'SECRET' not in resolved.source.model_dump_json()
    assert parse_qs(urlsplit(http.calls[-1][0]).query)['pageids'] == ['12']


def test_commons_empty_response_differs_from_invalid_and_api_error():
    assert CommonsProvider(HTTP({'batchcomplete': True})).search('nothing', limit=1).items == []
    for response in ({}, {'error': {'info': 'untrusted?token=SECRET'}}):
        with pytest.raises(MaterialError) as error:
            CommonsProvider(HTTP(response)).search('bad', limit=1)
        assert 'SECRET' not in str(error.value)


def test_archive_query_fields_and_date_precision_then_resolve_files():
    metadata = {'identifier': 'robot-demo', 'title': 'Robot', 'creator': ['A', 'B'], 'date': '1962',
                'licenseurl': 'https://creativecommons.org/licenses/by/4.0/'}
    http = HTTP({'response': {'numFound': 9, 'docs': [metadata]}},
                {'metadata': metadata, 'files': [
                    {'name': '../escape.mp4', 'size': '9'}, {'name': 'good.mp4', 'size': '123'},
                    {'name': 'good.zh.srt', 'size': '34'}, {'name': 'cover.jpg', 'size': '56'}]})
    provider = ArchiveProvider(http)
    page = provider.search('robot', kind='video', limit=3)
    assert page.cursor == '2' and page.total == 9 and page.items[0].publishedAt == '1962'
    parameters = parse_qs(urlsplit(http.calls[0][0]).query)
    assert 'identifier' in parameters['fl[]'] and 'mediatype:movies' in parameters['q'][0]
    resolved = provider.resolve(page.items[0])
    assert set(resolved.locators) == {'good.mp4', 'good.zh.srt', 'cover.jpg'}
    assert {item.kind for item in resolved.source.variants} == {'video', 'subtitle', 'image'}
    assert resolved.source.variants[0].bytes == 123 and resolved.source.variants[0].width is None
    assert resolved.source.author == 'A; B' and resolved.source.policy.usage.status == 'not-checked'


def test_nasa_keeps_unknown_license_and_width_and_resolves_asset_links():
    http = HTTP({'collection': {'items': [nasa_item()], 'metadata': {'total_hits': 2}}},
                {'collection': {'items': [{'href': 'https://images-assets.nasa.gov/a/film~orig.mp4'},
                    {'href': 'https://images-assets.nasa.gov/a/caption.srt?token=SECRET'},
                    {'href': 'https://images-assets.nasa.gov/a/collection.json'}]}})
    provider = NasaProvider(http)
    page = provider.search('artemis', kind='video', limit=1)
    item = page.items[0]
    assert page.cursor == '2' and item.license == '未知' and item.author == '未知'
    assert item.policy.sourceType == 'official' and item.variants[0].kind == 'video'
    assert item.variants[0].width is None and '%20' in item.variants[1].url
    resolved = provider.resolve(item)
    assert len(resolved.locators) == 2 and {v.kind for v in resolved.source.variants} == {'video', 'subtitle'}
    assert 'SECRET' not in resolved.source.model_dump_json()
    assert http.calls[-1][0].endswith('/asset/Artemis%20Origins')


@pytest.mark.parametrize('provider', [ArchiveProvider, NasaProvider])
def test_native_invalid_response_is_not_zero_results(provider):
    with pytest.raises(MaterialError, match='缺少'):
        provider(HTTP({})).search('robot', limit=1)


def pixabay_hit():
    return {'id': 123, 'pageURL': 'https://pixabay.com/videos/id-123/', 'user': 'Author', 'tags': 'robot',
            'duration': 2, 'videos': {'small': {'url': 'https://cdn.example.org/123.mp4', 'width': 640, 'height': 360}}}


def test_pixabay_reuses_candidate_parser_and_requests_selected_page(monkeypatch):
    monkeypatch.setenv('M2V_PIXABAY_API_KEY', 'SECRET')
    raw = pixabay_hit()
    raw['tags'] = 'robot SECRET'
    http = HTTP({'hits': [raw], 'totalHits': 30}, {'hits': [raw], 'totalHits': 1})
    provider = PixabayProvider(http)
    page = provider.search('robot', kind='video', limit=3, cursor='2')
    assert page.cursor == '3' and page.items[0].variants[0].width == 640
    assert 'SECRET' not in page.items[0].model_dump_json()
    assert parse_qs(urlsplit(http.calls[0][0]).query)['page'] == ['2']
    resolved = provider.resolve(page.items[0])
    assert resolved.locators['original'].endswith('123.mp4')
    assert parse_qs(urlsplit(http.calls[-1][0]).query)['id'] == ['123']


def test_pixabay_image_search_does_not_implicitly_exclude_illustrations(monkeypatch):
    monkeypatch.setenv('M2V_PIXABAY_API_KEY', 'SECRET')
    raw = {**pixabay_hit(), 'largeImageURL': 'https://cdn.example.org/vector-preview.jpg',
           'imageWidth': 2000, 'imageHeight': 1000}
    http = HTTP({'hits': [raw], 'totalHits': 1})
    page = PixabayProvider(http).search('diagram', kind='image', limit=1)
    item = page.items[0]
    assert page.limitations and parse_qs(urlsplit(http.calls[0][0]).query)['per_page'] == ['3']
    assert parse_qs(urlsplit(http.calls[0][0]).query)['image_type'] == ['all']
    assert item.variants[0].kind == 'image' and item.variants[0].width == 1280


def test_pixabay_missing_key_has_no_request_and_preserves_network_error_code(monkeypatch):
    monkeypatch.delenv('M2V_PIXABAY_API_KEY', raising=False)
    http = HTTP()
    with pytest.raises(MaterialError) as error:
        PixabayProvider(http).search('robot', kind='video')
    assert error.value.code == 'credential-missing' and http.calls == []
    http.responses.append({'collection': {'items': [nasa_item()], 'metadata': {'total_hits': 1}}})
    result = discover(selected=[PixabayProvider(http), NasaProvider(http)], queries=[Query(text='robot')], page_size=1)
    assert result.partial and len(result.sources) == 1 and result.failures[0]['error']['code'] == 'credential-missing'
    assert len(http.calls) == 1
    monkeypatch.setenv('M2V_PIXABAY_API_KEY', 'SECRET')
    http = HTTP(MaterialError('rate-limited', '受控限流', stage='network', retryable=True))
    with pytest.raises(MaterialError) as error:
        PixabayProvider(http).search('robot', kind='video')
    assert error.value.code == 'rate-limited' and error.value.retryable


def test_pixabay_metadata_only_candidate_and_no_key_echo(monkeypatch):
    monkeypatch.setenv('M2V_PIXABAY_API_KEY', 'SECRET')
    raw = pixabay_hit()
    raw['videos'] = {}
    provider = PixabayProvider(HTTP({'hits': [raw], 'totalHits': 1}))
    item = provider.search('robot', kind='video', limit=3).items[0]
    assert item.variants[0].url is None and item.variants[0].kind == 'video' and item.limitations
    for value in ('SECRET', '%53%45%43%52%45%54'):
        raw['pageURL'] = 'https://pixabay.com/videos/id-123/?id=' + value
        with pytest.raises(MaterialError, match='回显凭据'):
            PixabayProvider(HTTP({'hits': [raw], 'totalHits': 1})).search('robot', kind='video', limit=3)


def test_resolve_does_not_silently_bind_a_different_native_item():
    item = source('commons', '999', 'https://commons.wikimedia.org/wiki/File:X')
    with pytest.raises(MaterialError) as error:
        CommonsProvider(HTTP({'query': {'pages': [commons_page()]}})).resolve(item)
    assert error.value.code == 'source-changed'
    item = source('archive', 'expected', 'https://archive.org/details/expected')
    with pytest.raises(MaterialError) as error:
        ArchiveProvider(HTTP({'metadata': {'identifier': 'different'}, 'files': []})).resolve(item)
    assert error.value.code == 'source-changed'


@pytest.mark.parametrize('caption', [{'location': 'https://images-assets.nasa.gov/a/captions.srt'},
                                    MaterialError('not-found', '字幕不存在', stage='network')])
def test_nasa_optional_caption_endpoint_is_bounded_and_missing_is_not_failure(caption):
    item = NasaProvider._source(nasa_item())
    http = HTTP({'collection': {'items': [{'href': 'https://images-assets.nasa.gov/a/film.mp4'}]}}, caption)
    resolved = NasaProvider(http).resolve(item)
    assert http.calls[-1][0].endswith('/captions/Artemis%20Origins')
    assert ('captions' in resolved.locators) == isinstance(caption, dict)
    assert any(entry.kind == 'video' for entry in resolved.source.variants)


def test_url_and_text_normalization_preserves_identity_not_sessions():
    assert page_url('https://example.org/p?id=12&xsec_token=SECRET&tracking=opaque') == 'https://example.org/p?id=12'
    assert media_url('https://cdn.example.org/x.jpg?w=600') == 'https://cdn.example.org/x.jpg?w=600'
    assert media_url('https://cdn.example.org/x.jpg?unknown=SECRET') is None
    assert 'SECRET' not in text('<b>hello</b> https://example.org/a?token=SECRET')
    assert 'SECRET' not in text('Cookie=SECRET Authorization:SECRET')
    assert media_url('https://cdn.example.org/' + 'opaque' * 30 + '/film.mp4') is None
    assert len(text('x'*3000)) == 3000
    value = source('manual', '1', 'https://example.org/p', title='../../x', author=None, license=None)
    assert value.title == '../../x' and value.author == value.license == '未知'
    with pytest.raises(ValidationError, match='规格 ID'):
        SourceData(**{**value.model_dump(), 'variants': [variant('same', None, kind='video')]*2})
