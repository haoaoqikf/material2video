"""平台来源适配：B站/YouTube 搜索与已知分享链接的元数据提取。

搜索与元数据都走固定版本的隔离 worker；这里只做来源身份、页面规范化与
能力声明。ARIA/登录/会话限制按实际结果报告为 limited，不把未验证的接口
写成稳定支持，也不自建平台搜索服务。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from m2v.core.media_policy import SourceMetadata, Usage

from .contracts import Query, Source, SourceData, Variant
from .errors import MaterialError
from .network import validate_url
from .source_catalog import put_source
from .source_types import Capability, SearchPage, ResolvedSource, check_search, page_url, snapshot, text
from .store import MaterialStore

logger = logging.getLogger(__name__)

SEARCH_PROVIDERS = {'youtube': 'youtube', 'bilibili': 'bilibili'}
LINK_PROVIDERS = {'douyin': ('douyin.com', 'iesdouyin.com'),
                  'xiaohongshu': ('xiaohongshu.com', 'xhslink.com'),
                  'weibo': ('weibo.com', 'weibo.cn'),
                  'xigua': ('ixigua.com',)}
_ALLOWED = {'youtube': ('youtube.com', 'youtu.be'),
            'bilibili': ('bilibili.com', 'b23.tv'),
            **LINK_PROVIDERS}


def provider_for(url: str) -> str:
    target = validate_url(url)
    for name, hosts in _ALLOWED.items():
        if any(target.host == host or target.host.endswith('.' + host) for host in hosts):
            return name
    raise MaterialError('unsupported-source', '链接不属于已声明的平台入口；请改用公开文件或本地素材', stage='platform')


def _author(metadata: dict) -> str:
    return text(metadata.get('uploader') or metadata.get('channel') or metadata.get('uploader_id')) or '未知'


def source_from_metadata(provider: str, metadata: dict, *, query: Query | None = None) -> SourceData:
    locator = metadata.get('sourceUrl')
    if not isinstance(locator, str) or not locator:
        raise MaterialError('metadata-unavailable', '平台条目缺少可追溯页面，未作为来源保存', stage='platform')
    identifier = metadata.get('id') or locator
    width = metadata.get('width') if type(metadata.get('width')) is int else None
    height = metadata.get('height') if type(metadata.get('height')) is int else None
    variants = [Variant(id='original', kind='video', width=width, height=height)] if width or height else []
    limitations = []
    if metadata.get('live_status'):
        limitations.append('平台声明直播状态；直播不在自动获取范围')
    data = SourceData(provider=provider, externalId=text(str(identifier), limit=128) or None,
        sourceUrl=page_url(locator), title=text(metadata.get('title')) or text(str(identifier)) or '平台条目',
        author=_author(metadata), license='未知', publishedAt=text(str(metadata.get('upload_date') or '')) or None,
        variants=variants, queries=[query] if query else [], state='discovered', limitations=limitations,
        policy=SourceMetadata(sourceType='other', publisher=_author(metadata),
                              description=text(metadata.get('description')),
                              usage=Usage(status='not-checked')))
    return snapshot(data)


def link_source(url: str, *, author: str | None = None, license: str | None = None,
                title: str | None = None, references=()) -> tuple[SourceData, str]:
    """已知分享链接登记为平台来源；地址可含签名参数，但只保存规范页面身份。"""
    provider = provider_for(url)
    locator = validate_url(url).url
    public = page_url(locator)
    limitations = ['仅登记平台已知链接；媒体尚未获取/探测，不表示可稳定下载',
                   '平台会话/风控可能要求显式 cookie 文件或改用本地素材']
    if public is None or public != locator:
        limitations.append('临时或未知地址参数未保存；重新获取须显式提供原链接')
    data = snapshot(SourceData(provider=provider, externalId=None, sourceUrl=public,
        title=text(title) or f'{provider} 分享链接', author=text(author) or '未知',
        license=text(license) or '未知', state='registered', limitations=limitations,
        variants=[Variant(id='original', kind='video')],
        policy=SourceMetadata(sourceType='other', publisher=text(author) or '未知',
                              usage=Usage(status='not-checked'))))
    return data, locator


@dataclass
class PlatformProvider:
    name: str
    worker: object | None = None
    cookies: str | None = None
    timeout_s: float = 330.0
    max_items: int = 20

    def __post_init__(self):
        if self.name not in SEARCH_PROVIDERS:
            raise MaterialError('unsupported-source', '该平台没有已验证的关键词搜索接口', stage='platform')
        if not isinstance(self.timeout_s, (int, float)) or isinstance(self.timeout_s, bool) or not 0 < self.timeout_s <= 600:
            raise MaterialError('invalid-request', '平台查询时限无效', stage='platform')
        if type(self.max_items) is not int or not 1 <= self.max_items <= 50:
            raise MaterialError('invalid-request', '平台单页数量必须在 1..50', stage='platform')
        self.capability = Capability(True, True, True, True, False,
            limitations=('搜索与元数据依赖固定版本 yt-dlp；会话/风控可能导致 limited',
                         '不执行浏览器、外部下载器或联网 FFmpeg 回退'))

    def _run(self, request: dict) -> dict:
        from .ytdlp_worker import run_ytdlp
        worker = self.worker or run_ytdlp
        request = {'schemaVersion': 1, 'budget': {}, **request}
        if self.cookies is not None:
            request['cookies'] = str(self.cookies)
        try:
            return worker(request, timeout_s=self.timeout_s)
        except MaterialError as exc:
            raise MaterialError(exc.code, str(exc), stage='platform', retryable=exc.retryable) from None

    def search(self, query, *, kind='any', limit=20, cursor=None):
        check_search(query, kind, limit)
        if kind not in {'video', 'any'}:
            raise MaterialError('unsupported-kind', '平台搜索当前只返回视频条目', stage='platform')
        if cursor is not None:
            raise MaterialError('unsupported-source', '平台搜索没有已验证的分页游标，请缩小查询', stage='platform')
        data = self._run({'mode': 'search', 'provider': SEARCH_PROVIDERS[self.name], 'query': query,
                          'max_items': min(limit, self.max_items)})
        entries = data.get('entries') or []
        items = []
        for entry in entries[:limit]:
            try:
                items.append(source_from_metadata(self.name, entry, query=Query(text=query)))
            except MaterialError:
                logger.debug('平台搜索条目缺少页面身份，已跳过 provider=%s', self.name)
        limitations = list(data.get('warnings') or [])[:8]
        if not items:
            limitations.append('本次查询未返回可追溯条目；会话/风控或查询范围可能受限')
        return SearchPage(items, None, limitations=limitations)

    def resolve(self, item: SourceData) -> ResolvedSource:
        if item.provider != self.name or not item.sourceUrl:
            raise MaterialError('invalid-request', '平台来源身份不匹配', stage='platform')
        data = self._run({'mode': 'probe', 'url': validate_url(item.sourceUrl).url})
        metadata = data.get('metadata') or {}
        if not metadata.get('sourceUrl'):
            metadata = {**metadata, 'sourceUrl': item.sourceUrl}
        current = source_from_metadata(self.name, metadata)
        current.queries = item.queries.copy()
        current.limitations = list(dict.fromkeys([*item.limitations, *current.limitations]))
        if metadata.get('has_drm'):
            raise MaterialError('unsupported-source', '平台条目声明 DRM，不在自动获取范围', stage='platform')
        return ResolvedSource(current, {'original': current.sourceUrl or item.sourceUrl})


def platform_providers(worker=None, *, cookies: str | None = None, timeout_s: float = 330.0,
                       max_items: int = 20) -> list[PlatformProvider]:
    return [PlatformProvider(name, worker=worker, cookies=cookies, timeout_s=timeout_s,
                             max_items=max_items) for name in SEARCH_PROVIDERS]


def register_link(store: MaterialStore | None, url: str, *, author=None, license=None,
                  title=None, references=()) -> tuple[Source, str]:
    data, locator = link_source(url, author=author, license=license, title=title)
    document = put_source(store, data, references)
    logger.info('平台已知链接登记 id=%s provider=%s', document.id, data.provider)
    return document, locator
