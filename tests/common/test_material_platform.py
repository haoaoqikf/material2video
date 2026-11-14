"""平台搜索与已知链接：身份规范化、能力声明与受限结果。"""
from __future__ import annotations

import pytest

from m2v.materials import platform
from m2v.materials.contracts import SourceData
from m2v.materials.errors import MaterialError
from m2v.materials.store import MaterialStore


class _Worker:
    def __init__(self, response=None, error=None):
        self.response = response or {}
        self.error = error
        self.requests = []

    def __call__(self, request, *, timeout_s):
        self.requests.append(request)
        if self.error:
            raise self.error
        return self.response


def test_platform_search_normalizes_identity_and_keeps_usage_unchecked():
    worker = _Worker({'entries': [
        {'id': 'abc12345678', 'title': '公开影像', 'uploader': '发布者', 'upload_date': '20240102',
         'width': 1920, 'height': 1080, 'sourceUrl': 'https://www.youtube.com/watch?v=abc12345678&t=30'},
        {'id': 'no-page', 'title': '缺少页面身份'},
    ]})
    provider = platform.PlatformProvider('youtube', worker=worker, max_items=10)
    page = provider.search('城市 夜景', kind='video', limit=5)
    assert [item.sourceUrl for item in page.items] == ['https://www.youtube.com/watch?v=abc12345678']
    item = page.items[0]
    assert item.provider == 'youtube' and item.author == '发布者'
    assert item.policy.usage.status == 'not-checked'
    assert item.metadataSnapshotSha256
    assert worker.requests[0]['provider'] == 'youtube' and worker.requests[0]['mode'] == 'search'
    assert provider.capability.search and not provider.capability.pagination


def test_platform_search_validates_before_worker_and_reports_limited():
    worker = _Worker({'entries': []})
    source = platform.PlatformProvider('bilibili', worker=worker)
    with pytest.raises(MaterialError):
        source.search(' ', kind='video', limit=5)
    with pytest.raises(MaterialError):
        source.search('查询', kind='image', limit=5)
    with pytest.raises(MaterialError):
        source.search('查询', kind='video', limit=5, cursor='2')
    page = source.search('查询', kind='video', limit=5)
    assert page.items == [] and page.limitations
    assert len(worker.requests) == 1
    with pytest.raises(MaterialError):
        platform.PlatformProvider('douyin', worker=worker)


def test_known_links_cover_declared_platforms_and_reject_unknown_hosts():
    for url, provider in (('https://v.douyin.com/abcd/?utm_source=x', 'douyin'),
                          ('https://www.xiaohongshu.com/explore/abc?xsec_token=secret', 'xiaohongshu'),
                          ('https://weibo.com/1234567/AbCdEf?from=page', 'weibo'),
                          ('https://www.ixigua.com/7123456789012345678', 'xigua')):
        data, locator = platform.link_source(url)
        assert data.provider == provider and data.state == 'registered'
        assert 'utm_source' not in (data.sourceUrl or '') and 'xsec_token' not in (data.sourceUrl or '')
        assert data.policy.usage.status == 'not-checked'
        assert any('尚未获取' in note for note in data.limitations)
        assert locator == url
    with pytest.raises(MaterialError):
        platform.link_source('https://vimeo.com/12345')
    with pytest.raises(MaterialError):
        platform.link_source('http://127.0.0.1/video')


def test_platform_resolve_probes_metadata_and_rejects_drm():
    worker = _Worker({'metadata': {'id': 'BV1xx411c7mD', 'title': '平台标题', 'uploader': 'UP主',
                                   'sourceUrl': 'https://www.bilibili.com/video/BV1xx411c7mD',
                                   'has_drm': False}})
    source = platform.PlatformProvider('bilibili', worker=worker)
    item = SourceData(provider='bilibili', sourceUrl='https://www.bilibili.com/video/BV1xx411c7mD',
                      title='旧标题')
    resolved = source.resolve(item)
    assert resolved.source.title == '平台标题' and resolved.source.author == 'UP主'
    assert resolved.locators == {'original': 'https://www.bilibili.com/video/BV1xx411c7mD'}
    assert worker.requests[-1]['mode'] == 'probe'
    refusing = platform.PlatformProvider('bilibili', worker=_Worker({'metadata': {
        'id': 'x', 'sourceUrl': 'https://www.bilibili.com/video/BV1xx411c7mD', 'has_drm': True}}))
    with pytest.raises(MaterialError) as failure:
        refusing.resolve(item)
    assert failure.value.code == 'unsupported-source'


def test_session_cookie_path_is_passed_but_never_persisted(tmp_path):
    cookie = tmp_path / 'session.txt'
    cookie.write_text('# Netscape HTTP Cookie File\n', encoding='utf-8')
    worker = _Worker({'entries': []})
    provider = platform.PlatformProvider('youtube', worker=worker, cookies=str(cookie))
    provider.search('查询', kind='video', limit=3)
    assert worker.requests[0]['cookies'] == str(cookie)


def test_register_link_publishes_immutable_source(tmp_path):
    with MaterialStore(tmp_path / 'library') as store:
        document, locator = platform.register_link(store, 'https://v.douyin.com/xyz/')
        assert document.id.startswith('source-') and locator == 'https://v.douyin.com/xyz/'
        again, _ = platform.register_link(store, 'https://v.douyin.com/xyz/')
        assert again.id == document.id and store.get(document.id) == document
