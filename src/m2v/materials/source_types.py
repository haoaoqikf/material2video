"""来源适配的窄接口与安全规范化；声明规格不是媒体实测或采用结论。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
import re
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from m2v.core.media_policy import SourceMetadata, Usage
from .contracts import Query, SourceData, Variant, fingerprint
from .errors import MaterialError
from .network import public_url as log_url, redact_text, validate_url


@dataclass(frozen=True)
class Capability:
    search: bool
    metadata: bool
    fetch: bool
    captions: bool
    pagination: bool
    credentials: str = 'none'
    limitations: tuple[str, ...] = ()
    kinds: tuple[str, ...] = ('image', 'video', 'audio', 'any')

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SearchPage:
    items: list[SourceData]
    cursor: str | None = None
    total: int | None = None
    limitations: list[str] = field(default_factory=list)


@dataclass
class ResolvedSource:
    """locators 只在内存传递；不能序列化进来源、receipt 或日志。"""
    source: SourceData
    locators: dict[str, str]


class SourceProvider(Protocol):
    name: str
    capability: Capability

    def search(self, query: str, *, kind: str, limit: int, cursor: str | None = None) -> SearchPage: ...
    def resolve(self, source: SourceData) -> ResolvedSource: ...


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data):
        self.parts.append(data)


def text(value, *, limit: int = 4000, secrets: tuple[str, ...] = ()) -> str:
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return ''
    parser = _PlainText()
    parser.feed(str(value)[:max(limit * 4, 16000)])
    result = re.sub(r'[\x00-\x1f\x7f\s]+', ' ', ' '.join(parser.parts)).strip()
    return redact_text(result, secrets=secrets, limit=limit)


def integer(value, *, zero: bool = False) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = int(value)
        return number if number >= (0 if zero else 1) and str(value) in {str(number), f'{number}.0'} else None
    except (ValueError, TypeError, OverflowError):
        return None


# 仅保留能解释条目身份的公开页参数；其余跟踪/签名/会话参数不入工作材料。
_PAGE_KEYS = frozenset({'v', 'list', 'p', 'page', 'id', 'aid', 'bvid', 'vid', 'video_id', 'title', 'q', 'query'})
_MEDIA_KEYS = frozenset({'w', 'h', 'width', 'height', 'format', 'fm', 'auto', 'fit', 'crop', 'q', 'quality', 'dpr'})


def page_url(value: str) -> str:
    target = validate_url(value)
    parts = urlsplit(target.url)
    query = urlencode([(key, item) for key, item in parse_qsl(parts.query) if key.lower() in _PAGE_KEYS])
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ''))


def media_url(value) -> str | None:
    """未知参数也视为临时地址；必要时由 resolve 重取，不猜哪个 token 是公开的。"""
    if not isinstance(value, str):
        return None
    try:
        target = validate_url(value)
        if ('[redacted]' in log_url(target.url)
                or any(key.lower() not in _MEDIA_KEYS for key, _ in parse_qsl(urlsplit(target.url).query))):
            return None
        return target.url
    except MaterialError:
        return None


def variant(identifier: str, url, *, kind: str, width=None, height=None, size=None, mime=None) -> Variant:
    return Variant(id=identifier, url=media_url(url), kind=kind, width=integer(width), height=integer(height),
                   bytes=integer(size, zero=True), mime=text(mime, limit=128) or None)


def source(provider: str, external_id: str, url: str, *, title=None, author=None, license=None,
           description=None, published=None, publisher=None, source_type='other',
           variants: list[Variant] | None = None, limitations: list[str] | None = None) -> SourceData:
    result = SourceData(provider=provider, externalId=external_id, sourceUrl=page_url(url),
        title=text(title) or external_id, author=text(author) or '未知', license=text(license) or '未知',
        publishedAt=text(published, limit=128) or None, variants=variants or [], limitations=limitations or [],
        policy=SourceMetadata(sourceType=source_type, publisher=text(publisher) or '未知',
                              description=text(description), usage=Usage(status='not-checked')))
    return snapshot(result)


def snapshot(data: SourceData) -> SourceData:
    # 摘要对应规范化元数据快照（它本身完整保存在 Source 文档）；不哈希带令牌的原始响应。
    result = data.model_copy(deep=True)
    result.metadataSnapshotSha256 = fingerprint(result.model_dump(mode='json', exclude={'queries', 'metadataSnapshotSha256'}))
    return result


def page_number(cursor: str | None) -> int:
    if cursor is None:
        return 1
    if not isinstance(cursor, str) or not re.fullmatch(r'[1-9][0-9]{0,5}', cursor):
        raise MaterialError('invalid-request', '来源页游标必须是受限正整数', stage='discover')
    return int(cursor)


def check_search(query: str, kind: str, limit: int):
    if not isinstance(query, str) or not query.strip() or len(query) > 1000:
        raise MaterialError('invalid-request', '查询必须为 1～1000 字符的文本', stage='discover')
    if kind not in {'image', 'video', 'audio', 'any'} or type(limit) is not int or not 1 <= limit <= 50:
        raise MaterialError('invalid-request', '来源查询类型或每页数量无效', stage='discover')


def attach_query(item: SourceData, query: Query) -> SourceData:
    result = item.model_copy(deep=True)
    if query not in result.queries:
        result.queries.append(query)
    return result
