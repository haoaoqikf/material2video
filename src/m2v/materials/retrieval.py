"""词面、文本语义、视觉语义与元数据的独立召回及 RRF 融合。

查询只读取显式范围内的有效索引，不触发获取、重建或模型下载。不同通道的
原始分数不做统一概率解释；融合只改变排序，不把相似度写成身份或动作已满足。
"""
from __future__ import annotations

import hashlib
import logging
import math
from dataclasses import dataclass, field
from typing import Iterable

import numpy as np

from .contracts import (CandidateData, Observation, Observations, Requirement, RequirementData,
                        RetrievalReason, TimeRange, fingerprint)
from .errors import MaterialError
from .indexing import _find_index, load_vectors, tokens
from .model_manager import ModelManager
from .retrieval_policy import BACKGROUNDS, MIN_MARGIN, MIN_SCORE, VERSION as POLICY_VERSION
from .store import MaterialStore

logger = logging.getLogger(__name__)

CHANNELS = ('lexical', 'text', 'visual', 'metadata')
RRF_K = 60
MAX_QUERY_CHARS = 1000
# 校准后的最低语义证据：低于该值的命中不参与融合，避免弱匹配靠 RRF 名次放大。
SEMANTIC_MIN = MIN_SCORE


@dataclass
class Hit:
    media_id: str
    index_id: str
    record_id: str
    channel: str
    score: float
    excerpt: str = ''
    local_range: TimeRange | None = None
    frame: object | None = None
    model_identity: str | None = None
    retriever: str = ''
    rank: int = 0
    evidence: float = 0.0


@dataclass
class FindResult:
    requirement: Requirement
    candidates: list[CandidateData] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)
    channels: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {'schemaVersion': 1, 'requirementId': self.requirement.id,
                'requirement': self.requirement.model_dump(mode='json'),
                'candidates': [item.model_dump(mode='json') for item in self.candidates],
                'excluded': self.excluded, 'channels': self.channels, 'stats': self.stats}


def _check(query: str | None, channels, top_k: int, context_us: int) -> None:
    if not channels or set(channels) - set(CHANNELS):
        raise MaterialError('invalid-request', '检索通道必须来自 lexical/text/visual/metadata', stage='find')
    if type(top_k) is not int or not 1 <= top_k <= 200:
        raise MaterialError('invalid-request', 'Top-K 必须是 1..200', stage='find')
    if type(context_us) is not int or not 0 <= context_us <= 3600 * 1_000_000:
        raise MaterialError('invalid-request', '上下文窗口无效', stage='find')
    if query is not None:
        if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_CHARS:
            raise MaterialError('invalid-request', f'查询必须为 1～{MAX_QUERY_CHARS} 字符', stage='find')
        if 'http://' in query.lower() or 'https://' in query.lower():
            raise MaterialError('invalid-request', '链接请作为显式来源，不作为关键词查询', stage='find')


def _requirement(store: MaterialStore, requirement: Requirement | None, query: str | None,
                 scene_id: str | None) -> Requirement:
    if requirement is not None:
        if not isinstance(requirement, Requirement):
            raise MaterialError('invalid-request', '检索需求必须是 material.requirement', stage='find')
        try:
            store.put(requirement)
        except MaterialError as exc:
            if exc.code != 'conflict':
                raise
            existing = store.get(requirement.id, kind='material.requirement')
            if existing.data != requirement.data:
                raise
            return existing
        return requirement
    if query is None:
        raise MaterialError('invalid-request', '需要查询文本或需求文档', stage='find')
    data = RequirementData(text=query, sceneId=scene_id)
    digest = fingerprint({'text': query, 'sceneId': scene_id})
    document = Requirement(id=f'req-{digest[:32]}', data=data)
    try:
        store.put(document, cache_key=f'find-query:{digest}')
    except MaterialError as exc:
        if exc.code != 'conflict':
            raise
    return store.get(document.id, kind='material.requirement')


def _index_map(store: MaterialStore, media_map, excluded) -> dict[tuple[str, str], object]:
    """一次查询内只解码一次索引目录，避免每个媒体/通道重复扫描。"""
    result: dict[tuple[str, str], object] = {}
    for document in store.documents('material.index'):
        media = media_map.get(document.data.mediaId)
        if media is None:
            continue
        if (document.data.status != 'complete' or document.data.mediaSha256 != media.data.artifact.sha256
                or document.data.timelineMappingSha256 != fingerprint(media.data.probe.timeline)):
            excluded.append({'mediaId': media.id, 'indexId': document.id, 'reason': 'stale-index',
                             'note': '索引未完成或媒体/时间映射绑定失效'})
            continue
        key = (document.data.mediaId, document.data.channel)
        current = result.get(key)
        if current is None or (document.createdAt, document.id) > (current.createdAt, current.id):
            result[key] = document
    return result


def _lexical(store: MaterialStore, media, query_tokens: set[str], limit: int,
             indexes=None) -> list[Hit]:
    hits = []
    for channel in ('captions', 'asr', 'ocr', 'chapters'):
        index = (indexes or {}).get((media.id, channel)) if indexes is not None else _find_index(store, media, channel)
        if index is None or index.data.status != 'complete':
            continue
        for record in store.records(index.id):
            record_tokens = set(tokens(record.text))
            if not record_tokens:
                continue
            overlap = len(record_tokens & query_tokens)
            if not overlap:
                continue
            score = overlap / math.sqrt(len(record_tokens) * max(1, len(query_tokens)))
            if channel == 'chapters':
                score *= 0.5  # 章节标题是元数据级命中，排序低于逐句字幕
            hits.append(Hit(media.id, index.id, record.id, channel, score,
                            excerpt=record.text[:400], local_range=record.localRange,
                            retriever=f'lexical:{channel}:{media.id}'))
    hits.sort(key=lambda item: item.score, reverse=True)
    return hits[:limit]


def _semantic(store: MaterialStore, media, manager: ModelManager, channel: str, query: str,
              limit: int, indexes=None, query_cache=None, encoding_batches=None) -> tuple[list[Hit], list[str]]:
    index = ((indexes or {}).get((media.id, 'text' if channel == 'text' else 'visual'))
             if indexes is not None
             else _find_index(store, media, 'text' if channel == 'text' else 'visual'))
    if index is None or index.data.status != 'complete':
        return [], []
    spec = index.data.embeddingSpec
    model_name = 'e5-small' if channel == 'text' else 'siglip2-base'
    identity = manager.identity(model_name)
    expected = next(item['sha256'] for item in identity['files'] if item['path'] == 'model.safetensors')
    from . import embedding
    if (spec is None or spec.model != model_name or spec.revision != identity['revision']
            or spec.weightsSha256 != expected or spec.preprocessing != identity['preprocessing']
            or spec.dimensions != embedding.dimensions(manager, model_name) or not spec.normalized
            or spec.dtype != 'float32' or spec.precision != 'float32'):
        return [], [f'{channel}: 索引模型身份或预处理与当前模型不一致，已排除']
    matrix = load_vectors(store, index)
    records = store.records(index.id)
    by_vector = {record.vectorRow: record for record in records}
    if set(by_vector) != set(range(len(matrix))):
        return [], [f'{channel}: 向量行与证据记录不一致，已排除']
    queries = [query, *BACKGROUNDS[channel]]
    cache_key = fingerprint({'model': identity, 'queries': queries, 'channel': channel, 'policy': POLICY_VERSION})
    if query_cache is not None and cache_key in query_cache:
        vectors = query_cache[cache_key]
    else:
        vectors = (embedding.embed_texts(manager, queries, prefix='query') if channel == 'text'
                   else embedding.embed_visual_text(manager, queries))
        if query_cache is not None:
            query_cache[cache_key] = vectors
        if encoding_batches is not None:
            encoding_batches[channel] = encoding_batches.get(channel, 0) + 1
    vector = vectors[0]
    if vector.shape[0] != matrix.shape[1]:
        return [], [f'{channel}: 查询向量维数与索引不一致，已排除']
    scores = matrix @ vector.astype('float32')
    background = (matrix @ vectors[1:].astype('float32').T).max(axis=1)
    order = np.argsort(-scores)[:limit]
    hits = []
    for row in order:
        score = float(scores[int(row)])
        margin = score - float(background[int(row)])
        if score < SEMANTIC_MIN[channel] or margin + 1e-7 < MIN_MARGIN[channel]:
            continue
        record = by_vector[int(row)]
        if record.vectorRow is None:
            continue
        evidence_channel = 'metadata' if channel == 'text' and record.origin == 'e5-small:metadata' else channel
        hits.append(Hit(media.id, index.id, record.id, evidence_channel, score,
                        excerpt=record.text[:400] if channel == 'text' else
                            f'视觉余弦 {score:.5f}；背景差值 {margin:.5f}；{POLICY_VERSION}',
                        local_range=record.localRange,
                        frame=record.frame, model_identity=f'{model_name}@{identity["revision"][:12]}',
                        retriever=f'{channel}:{media.id}'))
    return hits, []


def _metadata(store: MaterialStore, media, query_tokens: set[str], limit: int) -> list[Hit]:
    try:
        source = store.get(media.data.sourceId, kind='material.source')
    except MaterialError:
        return []
    text = ' '.join(filter(None, [source.data.title, source.data.author,
                                  str(source.data.policy.description or '')]))
    record_tokens = set(tokens(text))
    overlap = len(record_tokens & query_tokens)
    if not overlap:
        return []
    score = overlap / math.sqrt(len(record_tokens) * max(1, len(query_tokens)))
    duration = media.data.probe.durationUs
    interval = None
    if duration:
        interval = TimeRange(startUs=0, endUs=duration)
    return [Hit(media.id, '', source.id, 'metadata', score, excerpt=text[:400],
                local_range=interval, retriever=f'metadata:{media.id}')][:limit]


def _scopes(store: MaterialStore, media_ids: Iterable[str] | None):
    if media_ids is not None:
        wanted = list(dict.fromkeys(media_ids))
        for item in wanted:
            yield store.get(item, kind='material.media')
        return
    for document in store.documents('material.media'):
        yield document


def _merge(hits: list[Hit], *, tolerance_us: int) -> list[list[Hit]]:
    by_media: dict[str, list[Hit]] = {}
    for hit in hits:
        by_media.setdefault(hit.media_id, []).append(hit)
    groups = []
    for media_hits in by_media.values():
        media_hits.sort(key=lambda item: (item.local_range.startUs if item.local_range else 0, -item.score))
        current: list[Hit] = []
        untimed: list[Hit] = []
        end = None
        for hit in media_hits:
            if hit.local_range is None:
                untimed.append(hit)
                continue
            if end is not None and hit.local_range.startUs <= end + tolerance_us:
                current.append(hit)
                end = max(end, hit.local_range.endUs)
                continue
            if current:
                groups.append(current)
            current, end = [hit], hit.local_range.endUs
        if current:
            groups.append(current)
        if untimed:
            groups.append(untimed)
    return groups


def _candidate(store: MaterialStore, requirement: Requirement, group: list[Hit],
               media, *, context_us: int = 0) -> CandidateData:
    intervals = [hit.local_range for hit in group if hit.local_range]
    window = None
    if intervals:
        duration = media.data.probe.durationUs
        start = max(0, min(item.startUs for item in intervals) - context_us)
        end = max(item.endUs for item in intervals) + context_us
        if duration is not None:
            end = min(end, duration)
        if end <= start:
            end = start + 1
        window = TimeRange(startUs=start, endUs=end)
    reasons = []
    for rank, hit in enumerate(sorted(group, key=lambda item: item.score, reverse=True), start=1):
        reasons.append(RetrievalReason(channel=hit.channel, rank=rank, score=max(-1e12, min(1e12, hit.score)),
                                       excerpt=hit.excerpt[:400], recordId=hit.record_id if hit.record_id else None,
                                       frame=hit.frame, modelIdentity=hit.model_identity))
    # RRF 只累加每个召回器在本组内的最好名次，避免同源多条命中重复加分。
    best = {}
    for hit in group:
        best[hit.retriever] = min(best.get(hit.retriever, hit.rank or len(group)), hit.rank or len(group))
    fused = sum(1.0 / (RRF_K + rank) for rank in best.values())
    limitations = []
    mapping = media.data.probe.timeline.sourceMapping
    if mapping.status != 'verified':
        limitations.append('源时间映射未验证；候选只有本地已哈希媒体窗口，不提供精确源区间')
    if requirement.data.identity.mustMatch:
        limitations.append('查询含身份/事件限定；相似召回不自动满足指定身份，须来源证据或实际查看')
    if any(hit.channel == 'lexical' for hit in group):
        limitations.append('字幕/转录/OCR 命中是文字依据，不等于目标画面、动作或身份已出现')
    if any(hit.channel in {'text', 'visual'} for hit in group):
        limitations.append('语义相似不是概率或事实；动作完整性与裁切可用性保持未知')
    observations = Observations(
        subjectMatch=Observation(), actionVisible=Observation(), actionComplete=Observation(),
        cropUsable=Observation(), factualIdentityMatch=Observation())
    index_ids = sorted({hit.index_id for hit in group if hit.index_id})
    return CandidateData(requirementId=requirement.id,
                         requirementDigest=fingerprint(requirement),
                         sourceId=media.data.sourceId, mediaId=media.id,
                         mediaSha256=media.data.artifact.sha256, indexIds=index_ids,
                         localRange=window, sourceRange=media.data.probe.timeline.source_range(window),
                         timelineMappingSha256=fingerprint(media.data.probe.timeline),
                         retrievalReasons=reasons, fusionScore=round(fused, 12),
                         observations=observations, previews=[], limitations=limitations)


def _accepted(media, source, *, orientation: str | None, min_duration_us: int,
              provider: str | None) -> bool:
    if provider is not None and (source is None or source.data.provider != provider):
        return False
    if min_duration_us and (media.data.probe.durationUs or 0) < min_duration_us:
        return False
    if orientation is not None:
        probe = media.data.probe
        if probe.width is None or probe.height is None:
            return False
        actual = ('square' if probe.width == probe.height else
                  'landscape' if probe.width > probe.height else 'portrait')
        if actual != orientation:
            return False
    return True


def find(store: MaterialStore, *, query: str | None = None, requirement: Requirement | None = None,
         manager: ModelManager | None = None, channels=('lexical', 'text', 'visual', 'metadata'),
         top_k: int = 10, context_us: int = 0, merge_gap_us: int = 1_000_000,
         media_ids: Iterable[str] | None = None, scene_id: str | None = None,
         orientation: str | None = None, min_duration_us: int = 0,
         provider: str | None = None) -> FindResult:
    _check(query, channels, top_k, context_us)
    if orientation not in {None, 'landscape', 'portrait', 'square'}:
        raise MaterialError('invalid-request', '画幅过滤只支持 landscape/portrait/square', stage='find')
    if type(min_duration_us) is not int or not 0 <= min_duration_us <= 24 * 3600 * 1_000_000:
        raise MaterialError('invalid-request', '最短时长过滤无效', stage='find')
    if provider is not None and (not isinstance(provider, str) or not provider.strip()):
        raise MaterialError('invalid-request', '来源过滤必须是非空来源名', stage='find')
    if 'text' in channels or 'visual' in channels:
        if manager is None:
            raise MaterialError('invalid-request', '语义通道需要显式模型根目录', stage='find')
    if type(merge_gap_us) is not int or not 0 <= merge_gap_us <= 3600 * 1_000_000:
        raise MaterialError('invalid-request', '相邻合并间隔无效', stage='find')
    media_ids = None if media_ids is None else list(media_ids)
    document = _requirement(store, requirement, query, scene_id)
    text = query or document.data.text
    query_tokens = set(tokens(text))
    result = FindResult(requirement=document)
    per_channel = {name: 0 for name in channels}
    hits: list[Hit] = []
    media_map = {item.id: item for item in _scopes(store, media_ids)}
    indexes = _index_map(store, media_map, result.excluded)
    query_cache, encoding_batches = {}, {}
    for media in media_map.values():
        try:
            # 内容对象不可变；查询只核对存在与大小，完整摘要校验留给 index/verify/preview。
            path = store.path(media.data.artifact.path, exists=True)
            if path.stat().st_size != media.data.artifact.bytes:
                raise MaterialError('hash-mismatch', '对象大小不一致', stage='find')
        except (MaterialError, OSError) as exc:
            result.excluded.append({'mediaId': media.id, 'reason': getattr(exc, 'code', 'not-found'),
                                    'note': '媒体字节缺失或大小不符，未参与检索'})
            continue
        try:
            source_document = store.get(media.data.sourceId, kind='material.source')
        except MaterialError:
            source_document = None
        if source_document is None and provider is not None:
            result.excluded.append({'mediaId': media.id, 'reason': 'metadata-filter',
                                    'note': '缺少来源身份，无法满足来源过滤'})
            continue
        if not _accepted(media, source_document, orientation=orientation,
                         min_duration_us=min_duration_us, provider=provider):
            result.excluded.append({'mediaId': media.id, 'reason': 'metadata-filter',
                                    'note': '未满足来源/画幅/时长过滤'})
            continue
        if 'lexical' in channels:
            found = _lexical(store, media, query_tokens, top_k * 3, indexes)
            per_channel['lexical'] += len(found)
            hits.extend(found)
        if 'text' in channels:
            found, notes = _semantic(store, media, manager, 'text', text, top_k * 3, indexes,
                                     query_cache, encoding_batches)
            per_channel['text'] += len(found)
            hits.extend(found)
            result.excluded.extend({'mediaId': media.id, 'reason': 'incompatible-index', 'note': note}
                                   for note in notes)
        if 'visual' in channels:
            found, notes = _semantic(store, media, manager, 'visual', text, top_k * 3, indexes,
                                     query_cache, encoding_batches)
            per_channel['visual'] += len(found)
            hits.extend(found)
            result.excluded.extend({'mediaId': media.id, 'reason': 'incompatible-index', 'note': note}
                                   for note in notes)
        if 'metadata' in channels:
            found = _metadata(store, media, query_tokens, top_k * 3)
            per_channel['metadata'] += len(found)
            hits.extend(found)
    # 每个召回器独立排名；同一记录被多通道命中时保留各通道依据。
    ranked: dict[tuple, Hit] = {}
    for hit in hits:
        ranked.setdefault((hit.retriever, hit.record_id), hit)
    runners: dict[str, list[Hit]] = {}
    for hit in ranked.values():
        runners.setdefault(hit.retriever, []).append(hit)
    for items in runners.values():
        items.sort(key=lambda item: item.score, reverse=True)
        for rank, hit in enumerate(items, start=1):
            hit.rank = rank
    # RRF 名次相同时，用同一通道内的标准分区分突出程度；不跨通道相加原始分数。
    families: dict[str, list[Hit]] = {}
    for hit in ranked.values():
        families.setdefault(hit.retriever.split(':', 1)[0], []).append(hit)
    for items in families.values():
        values = [hit.score for hit in items]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        deviation = variance ** 0.5
        for hit in items:
            hit.evidence = (hit.score - mean) / deviation if deviation > 0 else 0.0
    groups = _merge(list(ranked.values()), tolerance_us=merge_gap_us)
    built = []
    for group in groups:
        media = media_map.get(group[0].media_id)
        if media is None:
            continue
        candidate = _candidate(store, document, group, media, context_us=context_us)
        built.append((candidate, max((hit.evidence for hit in group), default=0.0),
                      min((hit.rank for hit in group if hit.rank), default=999)))
    # RRF 名次相同时，用通道顶部差距和最好名次排序；不把不同量纲分数直接相加。
    built.sort(key=lambda item: (item[0].fusionScore, item[1], -item[2]), reverse=True)
    result.candidates = [item[0] for item in built[:top_k]]
    result.channels = per_channel
    result.stats = {'mediaScanned': len(media_map), 'hits': len(ranked),
                    'requirementText': text[:64], 'queryDigest': hashlib.sha256(text.encode()).hexdigest()[:16],
                    'retrievalPolicy': POLICY_VERSION, 'queryEncodingBatches': encoding_batches}
    return result
