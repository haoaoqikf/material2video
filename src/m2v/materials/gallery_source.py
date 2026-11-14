"""复用现有 Pixabay 规格解析；桥接受控网络，不恢复 Pexels API。"""
from __future__ import annotations

import os
from urllib.parse import quote_plus, unquote, urlencode

from m2v.core.errors import M2VError
from m2v.engine.gallery.pixabay import PIXABAY_LICENSE, PIXABAY_MIN_PAGE_SIZE, PixabayProvider as GalleryPixabay
from .contracts import SourceData
from .errors import MaterialError
from .network import SafeHTTP, validate_url
from .source_types import Capability, ResolvedSource, SearchPage, check_search, integer, page_number, source, text, variant

_KEY_ENV = 'M2V_PIXABAY_API_KEY'
_BASE = 'https://pixabay.com/api'


class _Transport:
    def __init__(self, http):
        self.http, self.payload, self.error = http, None, None

    def get_json(self, url, headers, timeout_s):
        try:
            self.payload = self.http.get_json(url, headers=headers, max_bytes=min(8*1024*1024, self.http.budget.max_bytes))
            if not isinstance(self.payload, dict):
                raise MaterialError('invalid-response', 'Pixabay 未返回 JSON 对象', stage='discover')
            return self.payload
        except MaterialError as exc:
            self.error = exc
            raise


class PixabayProvider:
    name = 'pixabay'
    capability = Capability(True, True, True, False, True, credentials=_KEY_ENV,
        limitations=(f'API 最小实际页容量为 {PIXABAY_MIN_PAGE_SIZE}；新工作层不保存带 Key 的原始响应缓存',), kinds=('image', 'video'))

    def __init__(self, http: SafeHTTP):
        self.http = http

    def _client(self):
        bridge = _Transport(self.http)
        client = GalleryPixabay({'apiBase': _BASE, 'apiKeyEnv': _KEY_ENV, 'orientation': 'any'}, bridge)
        return client, bridge

    @staticmethod
    def _secrets():
        key = os.environ.get(_KEY_ENV, '').strip()
        if not key:
            raise MaterialError('credential-missing', f'缺少 {_KEY_ENV}；可继续使用其他来源', stage='discover')
        return key, quote_plus(key)

    @classmethod
    def _source(cls, raw, candidate, kind):
        identifier = integer(raw.get('id')) if isinstance(raw, dict) else None
        if identifier is None or not isinstance(raw.get('pageURL'), str):
            return None
        secrets = cls._secrets()
        def clean(value):
            return text(value, secrets=secrets)
        addresses = [raw['pageURL']] + ([candidate.download_url] if candidate else [])
        if any(secret in value or secret in unquote(value) for value in addresses for secret in secrets if secret):
            raise MaterialError('credential-leak', '来源响应在地址中回显凭据，拒绝持久化', stage='discover')
        variants = [variant('original', None, kind=kind)]
        if candidate:
            variants = [variant('original', candidate.download_url, kind=kind, width=candidate.width,
                                height=candidate.height)]
        return source('pixabay', str(identifier), raw['pageURL'], title=clean(raw.get('tags')) or str(identifier),
            author=clean(raw.get('user')), description=clean(raw.get('tags')), publisher=clean(raw.get('user')),
            license=clean(raw.get('license')) or PIXABAY_LICENSE, source_type='stock', variants=variants,
            limitations=[] if candidate else ['页面候选尚无可用规格，不冒充已下载或可用媒体'])

    @staticmethod
    def _failure(bridge):
        if bridge.error:
            raise bridge.error
        raise MaterialError('invalid-response', 'Pixabay 响应或规格无法规范化；可换查询或来源', stage='discover') from None

    def search(self, query, *, kind='video', limit=20, cursor=None):
        check_search(query, kind, limit)
        if kind not in self.capability.kinds:
            raise MaterialError('unsupported-kind', 'Pixabay 单次请求需明确 image 或 video', stage='discover')
        self._secrets()
        client, bridge = self._client()
        page = page_number(cursor)
        try:
            candidates = client.search(query, 'photo' if kind == 'image' else 'video', limit,
                                       self.http.budget.timeout_s, page=page, image_type='all')
            by_id = {item.id: item for item in candidates}
            hits = bridge.payload['hits']
            if not isinstance(hits, list):
                raise MaterialError('invalid-response', 'Pixabay hits 结构无效', stage='discover')
            items = [item for raw in hits[:limit] if isinstance(raw, dict)
                     and (item := self._source(raw, by_id.get(str(raw.get('id'))), kind))]
        except MaterialError:
            raise
        except (M2VError, KeyError, TypeError, ValueError):
            self._failure(bridge)
        total = integer(bridge.payload.get('totalHits'), zero=True)
        upstream_limit = max(PIXABAY_MIN_PAGE_SIZE, limit)
        more = page * upstream_limit < total if total is not None else len(hits) == upstream_limit
        limitations = [f'API 实际页容量 {upstream_limit}，本次仅保留每页前 {limit} 项；其它项未保留'] if limit < upstream_limit else []
        return SearchPage(items, str(page+1) if more else None, total, limitations)

    def resolve(self, item: SourceData):
        if item.provider != self.name or integer(item.externalId) is None:
            raise MaterialError('invalid-request', 'Pixabay 来源身份无效', stage='resolve')
        kinds = {entry.kind for entry in item.variants if entry.kind in self.capability.kinds}
        if len(kinds) != 1:
            # 页面无规格的候选不能从数字 ID 猜图片还是视频；调用方应显式重新发现。
            raise MaterialError('metadata-required', 'Pixabay 候选缺少明确图片/视频规格，请重新 discover 指定类型', stage='resolve')
        kind = next(iter(kinds))
        key = self._secrets()[0]
        client, bridge = self._client()
        endpoint = _BASE + ('/videos/' if kind == 'video' else '/')
        payload = bridge.get_json(endpoint + '?' + urlencode({'id': item.externalId, 'key': key}), client.headers(),
                                  self.http.budget.timeout_s)
        hits = payload.get('hits')
        if not isinstance(hits, list):
            raise MaterialError('invalid-response', 'Pixabay 详情缺少 hits', stage='resolve')
        for raw in hits[:16]:
            if not isinstance(raw, dict) or str(raw.get('id')) != item.externalId:
                continue
            try:
                candidate = client.parse_candidate(raw, 'photo' if kind == 'image' else 'video')
                current = self._source(raw, candidate, kind)
            except MaterialError:
                raise
            except (M2VError, KeyError, TypeError, ValueError):
                self._failure(bridge)
            if current is not None and candidate is not None:
                current.queries = item.queries.copy()
                return ResolvedSource(current, {'original': validate_url(candidate.download_url).url})
        raise MaterialError('not-found', 'Pixabay 当前条目没有可用规格', stage='resolve')
