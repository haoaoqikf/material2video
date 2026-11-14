"""多需求/多语言来源发现，分页与失败独立；不获取媒体、不推断观察结论。"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import logging
import time

from pydantic import ValidationError

from .contracts import Query, Requirement, Source, SourceData, identity, parse_document
from .errors import MaterialError
from .gallery_source import PixabayProvider
from .network import SafeHTTP
from .public_sources import ArchiveProvider, CommonsProvider, NasaProvider
from .source_types import Capability, SearchPage, SourceProvider, attach_query, check_search
from .store import MaterialStore

logger = logging.getLogger(__name__)


class _DisabledPexels:
    name = 'pexels'
    capability = Capability(False, False, False, False, False, credentials='API disabled',
                            limitations=('API 仍停用；可显式登记网页或公开直链，不能因配置 Key 恢复 API',))

    def search(self, *args, **kwargs):
        raise MaterialError('api-disabled', 'Pexels API 仍停用；改用显式网页候选或公开文件', stage='discover')

    def resolve(self, source):
        raise MaterialError('api-disabled', 'Pexels API 仍停用；显式网页需使用网页来源路径', stage='resolve')


def providers(http: SafeHTTP) -> dict[str, SourceProvider]:
    return {item.name: item for item in (CommonsProvider(http), ArchiveProvider(http), NasaProvider(http),
                                       PixabayProvider(http), _DisabledPexels())}


@dataclass
class DiscoveryResult:
    sources: list[Source] = field(default_factory=list)
    coverage: list[dict] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    capabilities: dict = field(default_factory=dict)
    stats: dict | None = None

    @property
    def partial(self) -> bool:
        return bool((self.failures or self.skipped) and any(row['status'] == 'succeeded' for row in self.coverage))

    @property
    def exit_code(self) -> int:
        if any(item['error']['code'] == 'cancelled' for item in self.failures):
            return 130
        if self.failures or self.skipped:
            return 1 if any(row['status'] == 'succeeded' for row in self.coverage) else 2
        return 0

    def to_dict(self) -> dict:
        return {'schemaVersion': 1, 'sources': [item.model_dump(mode='json') for item in self.sources],
                'coverage': self.coverage, 'failures': self.failures, 'skipped': self.skipped,
                'capabilities': self.capabilities, 'stats': self.stats, 'partial': self.partial, 'exitCode': self.exit_code}


def _validate(requirements, queries, selected, kind, page_size, max_pages, max_results, max_queries):
    for value, maximum, label in ((max_pages, 20, '页数'), (max_results, 10000, '结果数'), (max_queries, 128, '查询数')):
        if type(value) is not int or not 1 <= value <= maximum:
            raise MaterialError('invalid-request', f'{label}预算无效', stage='discover')
    check_search('validation', kind, page_size)
    if not selected or len(selected) > 16 or len({item.name for item in selected}) != len(selected):
        raise MaterialError('invalid-request', '需提供 1～16 个不重复来源', stage='discover')
    checked, plans = [], []
    try:
        for raw in requirements:
            item = parse_document(raw.model_dump(mode='json') if isinstance(raw, Requirement) else raw)
            if not isinstance(item, Requirement):
                raise MaterialError('invalid-request', '发现输入必须是需求文档', stage='discover')
            checked.append(item)
            for query in item.data.queries or [Query(text=item.data.text)]:
                plans.append((item.id, query))
        plans.extend((None, Query.model_validate(raw.model_dump() if isinstance(raw, Query) else raw)) for raw in queries)
    except ValidationError as exc:
        raise MaterialError('invalid-request', '查询结构无效', stage='discover') from exc
    if len({item.id for item in checked}) != len(checked):
        raise MaterialError('invalid-request', '需求 ID 不能重复', stage='discover')
    # 相同需求内重复查询不发起两次请求；不同需求保留分别的关联与覆盖记录。
    plans = list({(req, query.text, query.language): (req, query) for req, query in plans}.values())
    if not plans or len(plans) > max_queries:
        raise MaterialError('invalid-request', '查询为空或超出显式查询预算', stage='discover')
    for _, query in plans:
        check_search(query.text, kind, page_size)
        if 'http://' in query.text.lower() or 'https://' in query.text.lower():
            raise MaterialError('invalid-request', '链接请作为显式来源登记，不作为关键词保存', stage='discover')
    return checked, plans


def _failure(provider, request, exc):
    return {**request, 'provider': provider, 'error': exc.to_dict(),
            'nextStep': '可稍后有限重试、缩短查询、换独立来源，或显式提供页面/本地文件；不自动使用个人浏览器'}


def _publish(store: MaterialStore | None, data: SourceData, references: set[str]) -> Source:
    document_id = identity('source', {'data': data.model_dump(mode='json'), 'requirements': sorted(references)})
    if store is not None:
        try:
            previous = store.get(document_id, kind='material.source')
        except MaterialError as exc:
            if exc.code != 'not-found':
                raise
        else:
            if previous.data != data:
                raise MaterialError('conflict', '来源内容与不可变身份不一致', stage='discover')
            return store.put(previous, references=references)
    result = Source(id=document_id, data=data)
    return store.put(result, references=references) if store is not None else result


def _page(provider, query, kind, limit, cursor, cache) -> tuple[SearchPage | MaterialError, bool]:
    key = provider.name, query.text, kind, cursor, limit
    if key in cache:
        return cache[key], True
    try:
        page = provider.search(query.text, kind=kind, limit=limit, cursor=cursor)
        if (not isinstance(page, SearchPage) or not isinstance(page.items, list) or len(page.items) > limit
                or (page.cursor is not None and (not isinstance(page.cursor, str) or not page.cursor or len(page.cursor) > 1000))
                or (page.total is not None and (type(page.total) is not int or page.total < 0))
                or not isinstance(page.limitations, list) or len(page.limitations) > 32
                or any(not isinstance(note, str) for note in page.limitations)):
            raise MaterialError('invalid-response', '来源页面结构或数量超过本页预算', stage='discover')
        # 完整校验一页后才允许发布；查询缓存不保存半个坏页，跨需求也不反复请求坏响应。
        items = [SourceData.model_validate(item.model_dump(mode='json')) for item in page.items]
        if any(item.provider != provider.name or not (item.externalId or item.sourceUrl) for item in items):
            raise MaterialError('invalid-response', '来源响应种类串线或缺少可追溯条目标识', stage='discover')
        cache[key] = replace(page, items=items, limitations=list(page.limitations))
    except (MaterialError, KeyError, TypeError, ValueError, AttributeError) as exc:
        cache[key] = exc if isinstance(exc, MaterialError) else MaterialError('invalid-response', '来源响应无法规范化', stage='discover')
    return cache[key], False


def discover(*, selected: list[SourceProvider], requirements=(), queries=(), store: MaterialStore | None = None,
             kind: str = 'video', page_size: int = 20, max_pages: int = 2, max_results: int = 200,
             max_queries: int = 32, cancelled=None) -> DiscoveryResult:
    checked, plans = _validate(requirements, queries, selected, kind, page_size, max_pages, max_results, max_queries)
    started = time.monotonic()
    # 同一传输会被多个 provider 共享；只取一次增量，不能重复相加或声称 mock 流量为真值。
    clients = {id(client): client for item in selected if isinstance(client := getattr(item, 'http', None), SafeHTTP)}
    before = {key: client.stats for key, client in clients.items()}
    # 先验证全部输入再产生数据库或网络副作用。
    if store is not None:
        for item in checked:
            store.put(item)
    result = DiscoveryResult(capabilities={item.name: item.capability.to_dict() for item in selected})
    accumulated: dict[tuple, SourceData] = {}
    references: dict[tuple, set[str]] = {}
    pages: dict[tuple, object] = {}
    stopped, stop_reason = False, 'result-budget'
    published: dict[tuple, Source] = {}
    for requirement_id, query in plans:
        for provider in selected:
            kinds = [kind] if kind != 'any' or 'any' in provider.capability.kinds else list(provider.capability.kinds)
            for actual_kind in kinds:
                request = {'requirementId': requirement_id, 'query': query.model_dump(mode='json'), 'kind': actual_kind, 'pageSize': page_size}
                if stopped:
                    result.skipped.append({**request, 'provider': provider.name, 'reason': stop_reason})
                    continue
                if actual_kind not in provider.capability.kinds:
                    exc = MaterialError('unsupported-kind', '来源不支持请求的媒体类型', stage='discover')
                    result.failures.append(_failure(provider.name, request, exc))
                    continue
                cursor, visited = None, {None}
                for page_index in range(max_pages):
                    if cancelled and cancelled():
                        exc = MaterialError('cancelled', '来源发现已取消，已完成结果保留', stage='discover')
                        result.failures.append(_failure(provider.name, request, exc))
                        stopped, stop_reason = True, 'cancelled'
                        break
                    page, cache_hit = _page(provider, query, actual_kind, page_size, cursor, pages)
                    logger.debug('素材来源查询 provider=%s page=%d cached=%s', provider.name, page_index+1, cache_hit)
                    if isinstance(page, MaterialError):
                        logger.warning('素材来源查询失败 provider=%s code=%s', provider.name, page.code)
                        result.failures.append(_failure(provider.name, request, page))
                        result.coverage.append({**request, 'provider': provider.name, 'page': page_index+1,
                                                'status': 'failed', 'cacheHit': cache_hit})
                        break
                    validated = page.items
                    changed, discarded = {}, 0
                    for item in validated:
                        key = (item.provider, item.externalId or item.sourceUrl)
                        if key not in accumulated:
                            if len(accumulated) >= max_results:
                                stopped = True
                                discarded += 1
                                continue
                            accumulated[key], references[key] = item, set()
                        accumulated[key] = attach_query(accumulated[key], query)
                        if requirement_id:
                            references[key].add(requirement_id)
                        changed[key] = None
                    # 每个完整成功页即提交；后面的源失败/取消不丢掉已经取得的元数据。
                    for key in changed:
                        published[key] = _publish(store, accumulated[key], references[key])
                    result.coverage.append({**request, 'provider': provider.name, 'page': page_index+1,
                        'status': 'succeeded', 'returned': len(validated), 'total': page.total, 'cacheHit': cache_hit,
                        'truncated': bool(discarded or (page.cursor and page_index+1 == max_pages)),
                        'discarded': discarded, 'limitations': page.limitations})
                    if len(accumulated) >= max_results:
                        stopped = True
                    if stopped or page.cursor is None:
                        break
                    if page.cursor in visited:
                        exc = MaterialError('pagination-loop', '来源返回重复分页游标，已停止该查询', stage='discover')
                        result.failures.append(_failure(provider.name, request, exc))
                        break
                    visited.add(page.cursor)
                    cursor = page.cursor
    result.sources = list(published.values())
    # 方向只排序，来源身份/动作/年代等约束仍在需求内，永不在发现阶段自动满足。
    orientations = {item.id: item.data.preferredOrientation for item in checked}
    def preference(document):
        data = document.data
        refs = references[(data.provider, data.externalId or data.sourceUrl)]
        preferred = {orientations[ref] for ref in refs if orientations.get(ref)}
        for entry in data.variants:
            if entry.width and entry.height:
                orientation = 'square' if entry.width == entry.height else 'landscape' if entry.width > entry.height else 'portrait'
                if orientation in preferred:
                    return 0
        return 1
    result.sources.sort(key=preference)
    if clients:
        after = {key: client.stats for key, client in clients.items()}
        result.stats = {field: sum(after[key][field]-before[key][field] for key in clients) for field in ('bytes', 'requests')}
        result.stats['elapsedSeconds'] = time.monotonic() - started
    return result
