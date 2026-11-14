"""有界静态 HTML / JSON-LD 媒体声明解析；不执行脚本、iframe、CSS 或浏览器。"""
from __future__ import annotations

from dataclasses import dataclass, field
from email.message import Message
import json
import logging
from urllib.parse import urljoin

from .contracts import SourceData
from .errors import MaterialError
from .network import SafeHTTP, validate_url
from .registration import page_limitations, public_reference
from .source_types import Capability, ResolvedSource, snapshot, text, variant


logger = logging.getLogger(__name__)


@dataclass
class Asset:
    url: str = field(repr=False)
    kind: str = 'unknown'
    mime: str | None = None
    width: int | None = None
    height: int | None = None


def _reject_constant(value):
    raise ValueError('JSON-LD contains a non-finite constant')


class PageMetadata:
    """lxml target：只收集声明，不自研 HTML 词法器，也不建立整页 DOM。"""
    def __init__(self, url: str, *, max_assets: int = 64):
        self.base = url
        self.max_assets = max_assets
        self.assets: list[Asset] = []
        self.metadata: dict[str, str] = {}
        self.limitations: list[str] = []
        self._media: list[str] = []
        self._seen: set[str] = set()
        self._title, self._title_chars, self._base_seen = False, 0, False
        self._title_text: list[str] = []
        self._script: list[str] | None = None
        self._script_chars, self._scripts, self._tags, self._json_nodes = 0, 0, 0, 0

    def start(self, tag, attributes):
        self.handle_starttag(tag, attributes)

    def end(self, tag):
        self.handle_endtag(tag)

    def data(self, value):
        self.handle_data(value)

    def close(self):
        return self

    def notice(self, message):
        if message not in self.limitations:
            self.limitations.append(message)

    def add(self, value, kind, *, mime=None, width=None, height=None):
        if not isinstance(value, str) or not value.strip():
            return
        if len(self.assets) >= self.max_assets:
            self.notice('静态媒体声明达到数量预算，其它声明未解析')
            return
        try:
            locator = validate_url(urljoin(self.base, value.strip())).url
        except MaterialError:
            self.notice('部分派生地址不符合 HTTP(S) 安全政策，未采用')
            return
        if locator not in self._seen:
            self._seen.add(locator)
            self.assets.append(Asset(locator, kind, mime, width, height))

    def handle_starttag(self, tag, attrs):
        self._tags += 1
        if self._tags > 50000:
            raise MaterialError('resource-limit', '页面标签超过解析预算', stage='webpage')
        attributes = dict(attrs)
        if tag == 'base' and attributes.get('href') and not self._base_seen:
            self._base_seen = True
            try:
                self.base = validate_url(urljoin(self.base, attributes['href'])).url
            except MaterialError:
                self.notice('不安全 base 地址未采用')
        elif tag in {'video', 'audio'}:
            if len(self._media) >= 64:
                raise MaterialError('resource-limit', '媒体标签嵌套超过解析预算', stage='webpage')
            self._media.append(tag)
            self.add(attributes.get('src'), tag)
            if tag == 'video':
                self.add(attributes.get('poster'), 'image')
        elif tag == 'source':
            mime = text(attributes.get('type'), limit=128) or None
            kind = self._media[-1] if self._media else 'video' if (mime or '').startswith('video/') else 'audio' if (mime or '').startswith('audio/') else 'unknown'
            self.add(attributes.get('src'), kind, mime=mime)
        elif tag == 'track' and attributes.get('kind', 'subtitles') in {'subtitles', 'captions'}:
            self.add(attributes.get('src'), 'subtitle', mime=attributes.get('type'))
        elif tag == 'img':
            self.add(attributes.get('src'), 'image', width=attributes.get('width'), height=attributes.get('height'))
            if attributes.get('srcset'):
                self.notice('srcset/懒加载仅保留显式 src；其它变体可用明确链接补充')
        elif tag == 'meta':
            key = (attributes.get('property') or attributes.get('name') or '').lower()
            value = attributes.get('content') or ''
            if key in {'og:video', 'og:video:url', 'og:video:secure_url', 'twitter:player:stream'}:
                self.add(value, 'video')
            elif key in {'og:image', 'og:image:url', 'twitter:image'}:
                self.add(value, 'image')
            elif key in {'og:audio', 'og:audio:url'}:
                self.add(value, 'audio')
            elif key in {'og:title', 'description', 'og:description', 'author', 'og:site_name', 'article:published_time'}:
                self.metadata.setdefault(key, text(value))
        elif tag == 'link' and 'license' in (attributes.get('rel') or '').lower().split():
            self.metadata.setdefault('license', text(urljoin(self.base, attributes.get('href') or '')))
        elif tag == 'title':
            self._title = True
        elif tag == 'script' and (attributes.get('type') or '').lower().split(';')[0].strip() == 'application/ld+json':
            self._scripts += 1
            if self._scripts <= 8:
                self._script, self._script_chars = [], 0
            else:
                self.notice('JSON-LD 块达到数量预算')
        elif tag == 'input' and attributes.get('type', '').lower() == 'password':
            self.notice('页面包含登录表单；未读取浏览器或尝试绕过，部分内容可能不可得')
        elif tag == 'iframe':
            self.notice('嵌入页面/播放器不自动递归；请提供发布页或公开媒体链接')

    def handle_data(self, data):
        if self._title and self._title_chars < 16000:
            value = data[:16000-self._title_chars]
            self._title_text.append(value)
            self._title_chars += len(value)
        if self._script is not None:
            self._script_chars += len(data)
            if self._script_chars > 512*1024:
                self._script = None
                self.notice('过大 JSON-LD 块未解析')
            else:
                self._script.append(data)

    def handle_endtag(self, tag):
        if tag in {'video', 'audio'} and tag in self._media:
            while self._media and self._media.pop() != tag:
                pass
        elif tag == 'title':
            self._title = False
            self.metadata.setdefault('title', text(' '.join(self._title_text)))
        elif tag == 'script' and self._script is not None:
            raw, self._script = ''.join(self._script), None
            try:
                value = json.loads(raw, parse_constant=_reject_constant)
            except (ValueError, RecursionError):
                self.notice('无效 JSON-LD 当作数据忽略，未执行脚本')
                return
            self.structured(value)

    def structured(self, value, depth=0):
        self._json_nodes += 1
        if depth > 6 or self._json_nodes > 256:
            self.notice('JSON-LD 嵌套/条目达到预算')
            return
        if isinstance(value, list):
            for item in value[:128]:
                if self._json_nodes >= 256:
                    self.notice('JSON-LD 条目达到预算')
                    break
                self.structured(item, depth+1)
        elif isinstance(value, dict):
            types = value.get('@type', [])
            types = [types] if isinstance(types, str) else types if isinstance(types, list) else []
            types = {item.rsplit('/', 1)[-1].lower() for item in types if isinstance(item, str)}
            kind = 'video' if 'videoobject' in types else 'audio' if 'audioobject' in types else 'image' if 'imageobject' in types else None
            if kind:
                self.add(value.get('contentUrl') or (value.get('url') if kind == 'image' else None), kind,
                         width=value.get('width'), height=value.get('height'))
                thumbnails = value.get('thumbnailUrl', [])
                for thumbnail in (thumbnails[:8] if isinstance(thumbnails, list) else [thumbnails]):
                    self.add(thumbnail, 'image')
                for target, key in (('title', 'name'), ('description', 'description'), ('license', 'license'), ('published', 'uploadDate')):
                    if isinstance(value.get(key), str):
                        self.metadata.setdefault(target, text(value[key]))
                author = value.get('author')
                self.metadata.setdefault('author', text(author.get('name') if isinstance(author, dict) else author))
            for item in value.values():
                if self._json_nodes >= 256:
                    self.notice('JSON-LD 条目达到预算')
                    break
                if isinstance(item, (dict, list)):
                    self.structured(item, depth+1)


def parse_page(body: bytes, url: str, *, content_type='text/html', max_assets=64) -> PageMetadata:
    if type(max_assets) is not int or not 1 <= max_assets <= 128 or len(body) > 2*1024*1024:
        raise MaterialError('resource-limit', '网页大小或媒体声明预算无效', stage='webpage')
    message = Message()
    message['content-type'] = content_type
    if message.get_content_type() not in {'text/html', 'application/xhtml+xml'}:
        raise MaterialError('not-html', '地址不是 HTML 页面；可改用公开文件获取', stage='webpage')
    charset = (message.get_content_charset() or 'utf-8').lower()
    supported = {'utf-8', 'utf8', 'gbk', 'gb18030', 'big5', 'iso-8859-1', 'windows-1252'}
    try:
        from lxml import etree
    except ImportError:
        raise MaterialError('dependency-missing', '静态网页解析依赖缺失；请运行 uv sync --locked 恢复项目环境', stage='webpage') from None
    parser = PageMetadata(validate_url(url).url, max_assets=max_assets)
    if charset not in supported:
        charset = 'utf-8'
        parser.notice('页面编码未识别，按 UTF-8 尽力读取元数据')
    class NoExternalResources(etree.Resolver):
        def resolve(self, url, public_id, context):
            raise MaterialError('security-blocked', '页面解析禁止外部 DTD、实体与本地文件引用', stage='webpage')
    # target 模式不建立 DOM；关闭网络及 huge-tree，且显式拒绝所有外部解析器资源。
    reader = etree.HTMLParser(target=parser, encoding='utf-8', no_network=True, huge_tree=False)
    reader.resolvers.add(NoExternalResources())
    try:
        decoded = body.decode(charset)
    except UnicodeDecodeError:
        decoded = body.decode(charset, errors='replace')
        parser.notice('响应头编码无法完整解码；文本元数据不保证完整，可用明确文件或本地素材补充')
    try:
        reader.feed(decoded.encode('utf-8'))
        reader.close()
    except (etree.XMLSyntaxError, ValueError, RecursionError):
        raise MaterialError('invalid-response', '页面结构无法在预算内解析', stage='webpage') from None
    return parser


class WebpageProvider:
    name = 'webpage'
    capability = Capability(False, True, True, True, False,
        limitations=('仅静态 HTML/JSON-LD 声明，不执行 JS、CSS、iframe 或浏览器；未知身份不自动满足',))

    def __init__(self, http: SafeHTTP):
        self.http = http

    def search(self, *args, **kwargs):
        raise MaterialError('explicit-source-required', '网页来源只接受显式链接；请提供原始发布页', stage='discover')

    def resolve(self, original: SourceData, *, locator: str | None = None) -> ResolvedSource:
        if original.provider not in {'webpage', 'url'}:
            raise MaterialError('invalid-request', '网页来源身份不匹配', stage='webpage')
        if locator is None and original.externalId is None:
            raise MaterialError('locator-required', '该地址已脱敏，请显式重新提供原链接；不猜测隐藏资源', stage='webpage')
        target = validate_url(locator or original.sourceUrl or '').url
        if original.sourceUrl is not None and public_reference(target).url != original.sourceUrl:
            raise MaterialError('source-changed', '显式页面地址与登记来源不一致；请作为独立来源登记', stage='webpage')
        with self.http.open(target, max_bytes=min(2*1024*1024, self.http.budget.max_bytes)) as response:
            parsed = parse_page(response.read(), response.url, content_type=response.headers.get('Content-Type', 'text/html'))
            reference = public_reference(response.url)
        self.http.check()
        data = original.model_copy(deep=True)
        data.provider, data.sourceUrl, data.externalId = 'webpage', reference.url, reference.external_id
        data.title = parsed.metadata.get('og:title') or parsed.metadata.get('title') or original.title
        data.author = original.author if original.author != '未知' else parsed.metadata.get('author') or '未知'
        data.license = original.license if original.license != '未知' else parsed.metadata.get('license') or '未知'
        data.publishedAt = parsed.metadata.get('article:published_time') or parsed.metadata.get('published') or original.publishedAt
        data.policy.description = parsed.metadata.get('og:description') or parsed.metadata.get('description') or original.policy.description
        data.policy.publisher = parsed.metadata.get('og:site_name') or original.policy.publisher
        data.queries = original.queries.copy()
        data.limitations = page_limitations([*original.limitations, *parsed.limitations], requires_locator=reference.requires_locator)
        data.variants, locators = [], {}
        for index, asset in enumerate(parsed.assets):
            identifier = f'{asset.kind}-{index}'
            data.variants.append(variant(identifier, asset.url, kind=asset.kind, width=asset.width, height=asset.height, mime=asset.mime))
            locators[identifier] = asset.url
        data.state = 'registered' if locators else 'limited'
        if not locators:
            data.limitations.append('仅取得页面候选，无静态媒体声明；请提供明确文件或换来源，不自动启用浏览器')
        logger.info('静态页面解析完成 variants=%d limited=%s', len(locators), not bool(locators))
        return ResolvedSource(snapshot(data), locators)
