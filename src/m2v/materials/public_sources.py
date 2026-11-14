"""Commons / Internet Archive / NASA 官方公开接口适配；所有请求走 SafeHTTP。"""
from __future__ import annotations

import logging
from pathlib import PurePosixPath
from urllib.parse import quote, urlencode

from .contracts import SourceData, fingerprint
from .errors import MaterialError
from .network import SafeHTTP, validate_url
from .source_types import Capability, ResolvedSource, SearchPage, check_search, integer, page_number, snapshot, source, text, variant


logger = logging.getLogger(__name__)


def _json(http, endpoint: str, parameters: dict | None = None) -> dict:
    logger.debug('查询公开来源元数据 endpoint=%s', endpoint.split('/')[2])
    payload = http.get_json(endpoint + ('?' + urlencode(parameters, doseq=True) if parameters else ''), max_bytes=min(8*1024*1024, http.budget.max_bytes))
    if not isinstance(payload, dict):
        raise MaterialError('invalid-response', '来源接口未返回 JSON 对象', stage='discover')
    return payload


def _joined(value):
    return '; '.join(filter(None, (text(item) for item in value[:16]))) if isinstance(value, list) else text(value)


def _rights(*values):
    # 保留额外使用条件/限制，不让一个简短许可标签遮掉原始声明；仍不自动作采用判断。
    return '; '.join(dict.fromkeys(value for raw in values if (value := _joined(raw))))


def _updated(item: SourceData, variants) -> SourceData:
    return snapshot(item.model_copy(update={'variants': variants}))


class CommonsProvider:
    name = 'commons'
    capability = Capability(True, True, True, False, True,
        limitations=('API 元数据和许可是来源声明，不是实际画面观察或自动授权结论',))
    endpoint = 'https://commons.wikimedia.org/w/api.php'

    def __init__(self, http: SafeHTTP):
        self.http = http

    @staticmethod
    def _pages(payload):
        if 'error' in payload:
            raise MaterialError('source-error', 'Commons 接口拒绝当前查询，请缩短查询或稍后重试', stage='discover')
        if not any(key in payload for key in ('query', 'batchcomplete', 'continue')):
            raise MaterialError('invalid-response', 'Commons 响应缺少查询状态', stage='discover')
        query = payload.get('query', {})
        if not isinstance(query, dict):
            raise MaterialError('invalid-response', 'Commons query 结构无效', stage='discover')
        pages = query.get('pages', [])
        if isinstance(pages, dict):
            pages = list(pages.values())
        if not isinstance(pages, list):
            raise MaterialError('invalid-response', 'Commons pages 结构无效', stage='discover')
        return sorted((item for item in pages if isinstance(item, dict)), key=lambda item: integer(item.get('index')) or 0)

    @staticmethod
    def _source(page):
        title = text(page.get('title'))
        if not title:
            return None
        identifier = str(integer(page.get('pageid')) or title)
        information = page.get('imageinfo')
        if not isinstance(information, list) or not information or not isinstance(information[0], dict):
            return source('commons', identifier, 'https://commons.wikimedia.org/wiki/' + quote(title.replace(' ', '_')),
                title=title, publisher='Wikimedia Commons', source_type='open-library',
                limitations=['仅取得文件描述页，尚无可用文件元数据；不代表已取得媒体'])
        info = information[0]
        mime = text(info.get('mime'))
        kind = 'image' if mime.startswith('image/') else 'video' if mime.startswith('video/') else 'audio' if mime.startswith('audio/') else 'unknown'
        ext = info.get('extmetadata', {})
        if not isinstance(ext, dict):
            ext = {}
        def field(name):
            value = ext.get(name, {})
            return value.get('value') if isinstance(value, dict) else None
        url = info.get('descriptionurl') or 'https://commons.wikimedia.org/wiki/' + quote(title.replace(' ', '_'))
        return source('commons', identifier, url, title=title,
            author=field('Artist') or field('Credit'), license=_rights(field('LicenseShortName'), field('LicenseUrl'), field('UsageTerms'), field('Restrictions')),
            description=field('ImageDescription'), published=field('DateTimeOriginal'), publisher='Wikimedia Commons',
            source_type='open-library', variants=[variant('original', info.get('url'), kind=kind,
                width=info.get('width'), height=info.get('height'), size=info.get('size'), mime=mime)])

    def search(self, query, *, kind='any', limit=20, cursor=None):
        check_search(query, kind, limit)
        offset = page_number(cursor) if cursor else 0
        # Commons 的 CirrusSearch 不接受括号 OR 组合；位图与绘制合并为单个 filetype 查询。
        prefix = {'video': 'filetype:video ', 'image': 'filetype:bitmap|drawing ', 'audio': 'filetype:audio '}.get(kind, '')
        payload = _json(self.http, self.endpoint, {'action': 'query', 'format': 'json', 'formatversion': 2,
            'generator': 'search', 'gsrsearch': prefix + query, 'gsrnamespace': 6, 'gsrlimit': limit,
            'gsroffset': offset, 'prop': 'imageinfo', 'iiprop': 'url|size|mime|extmetadata'})
        items = [item for page in self._pages(payload) if (item := self._source(page))]
        next_offset = integer(payload.get('continue', {}).get('gsroffset'))
        return SearchPage(items, str(next_offset) if next_offset is not None else None)

    def resolve(self, item):
        if item.provider != self.name or not item.externalId:
            raise MaterialError('invalid-request', 'Commons 来源身份不匹配', stage='resolve')
        key = 'pageids' if item.externalId.isdigit() else 'titles'
        payload = _json(self.http, self.endpoint, {'action': 'query', 'format': 'json', 'formatversion': 2,
            key: item.externalId, 'prop': 'imageinfo', 'iiprop': 'url|size|mime|extmetadata'})
        pages = self._pages(payload)
        if not pages or (current := self._source(pages[0])) is None:
            raise MaterialError('not-found', 'Commons 条目没有可用文件元数据', stage='resolve')
        if item.externalId.isdigit() and current.externalId != item.externalId:
            raise MaterialError('source-changed', 'Commons 返回了不同条目，未沿用旧来源身份', stage='resolve')
        current.queries = item.queries.copy()
        information = pages[0].get('imageinfo')
        if not isinstance(information, list) or not information or not isinstance(information[0], dict):
            raise MaterialError('metadata-unavailable', 'Commons 仅有描述页，尚无可获取文件', stage='resolve')
        raw = information[0].get('url')
        locators = {'original': validate_url(raw).url} if isinstance(raw, str) else {}
        return ResolvedSource(current, locators)


class ArchiveProvider:
    name = 'archive'
    capability = Capability(True, True, True, True, True,
        limitations=('档案条目可能有多文件；字幕与文件仅声明存在，须获取后校验',))
    search_endpoint = 'https://archive.org/advancedsearch.php'
    metadata_endpoint = 'https://archive.org/metadata/'

    def __init__(self, http: SafeHTTP):
        self.http = http

    @staticmethod
    def _source(raw):
        identifier = text(raw.get('identifier'), limit=240)
        if not identifier or any(character not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-' for character in identifier):
            return None
        return source('archive', identifier, 'https://archive.org/details/' + quote(identifier),
            title=raw.get('title'), author=_joined(raw.get('creator')), license=_rights(raw.get('licenseurl'), raw.get('rights')),
            published=raw.get('date'), description=_joined(raw.get('description')),
            publisher=_joined(raw.get('publisher')) or 'Internet Archive（托管）', source_type='archive')

    def search(self, query, *, kind='any', limit=20, cursor=None):
        check_search(query, kind, limit)
        page = page_number(cursor)
        media_type = {'video': 'movies', 'image': 'image', 'audio': 'audio'}.get(kind)
        expression = f'({query})' + (f' AND mediatype:{media_type}' if media_type else ' AND mediatype:(movies OR image OR audio)')
        payload = _json(self.http, self.search_endpoint, {'q': expression,
            'fl[]': ['identifier', 'title', 'creator', 'date', 'description', 'licenseurl', 'rights', 'publisher'],
            'output': 'json', 'rows': limit, 'page': page})
        response = payload.get('response')
        if not isinstance(response, dict) or not isinstance(response.get('docs'), list):
            raise MaterialError('invalid-response', 'Archive 接口缺少有效 response/docs', stage='discover')
        items = [item for raw in response['docs'] if isinstance(raw, dict) and (item := self._source(raw))]
        total = integer(response.get('numFound'), zero=True)
        more = page * limit < total if total is not None else len(response['docs']) == limit
        return SearchPage(items, str(page+1) if more else None, total)

    def resolve(self, item):
        if item.provider != self.name or not item.externalId or self._source({'identifier': item.externalId}) is None:
            raise MaterialError('invalid-request', 'Archive 来源身份不匹配', stage='resolve')
        payload = _json(self.http, self.metadata_endpoint + quote(item.externalId, safe=''))
        metadata, files = payload.get('metadata'), payload.get('files')
        if not isinstance(metadata, dict) or not isinstance(files, list):
            raise MaterialError('invalid-response', 'Archive 条目缺少文件元数据', stage='resolve')
        if metadata.get('identifier') is not None and metadata['identifier'] != item.externalId:
            raise MaterialError('source-changed', 'Archive 返回了不同条目，未沿用旧来源身份', stage='resolve')
        current = self._source({**metadata, 'identifier': item.externalId})
        variants, locators = [], {}
        extensions = {'.mp4': 'video', '.webm': 'video', '.ogv': 'video', '.mov': 'video', '.mkv': 'video',
            '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image', '.webp': 'image',
            '.mp3': 'audio', '.wav': 'audio', '.flac': 'audio', '.ogg': 'audio', '.m4a': 'audio',
            '.srt': 'subtitle', '.vtt': 'subtitle', '.ass': 'subtitle'}
        for raw in files[:2048]:
            if not isinstance(raw, dict) or not isinstance(raw.get('name'), str):
                continue
            name = raw['name']
            path = PurePosixPath(name)
            if len(name) > 512 or '\\' in name or path.is_absolute() or '..' in path.parts:
                continue
            kind = extensions.get(path.suffix.lower())
            if not kind or name in locators:
                continue
            locator = 'https://archive.org/download/' + quote(item.externalId, safe='') + '/' + quote(name, safe='/')
            variants.append(variant(name, locator, kind=kind, size=raw.get('size'), width=raw.get('width'), height=raw.get('height')))
            locators[name] = validate_url(locator).url
            if len(variants) >= 128:
                break
        current.queries = item.queries.copy()
        if len(files) > 2048 or len(variants) == 128:
            current.limitations.append('大条目仅解析前 2048 项并保留至多 128 个可识别文件；未镜像全部档案')
        return ResolvedSource(_updated(current, variants), locators)


class NasaProvider:
    name = 'nasa'
    capability = Capability(True, True, True, True, True,
        limitations=('NASA 托管不等于所有内容均为公共领域；许可未知保持未知',))
    base = 'https://images-api.nasa.gov'

    def __init__(self, http: SafeHTTP):
        self.http = http

    @staticmethod
    def _source(raw):
        data = raw.get('data')
        if not isinstance(data, list) or not data or not isinstance(data[0], dict):
            return None
        metadata = data[0]
        identifier = text(metadata.get('nasa_id'), limit=512)
        if not identifier:
            return None
        kind = metadata.get('media_type')
        variants = [variant('original', None, kind=kind)] if kind in {'video', 'image', 'audio'} else []
        links = raw.get('links', [])
        if isinstance(links, list):
            for link in links[:8]:
                if isinstance(link, dict) and link.get('render') == 'image':
                    variants.append(variant(f'preview-{len(variants)}', link.get('href'), kind='image'))
        return source('nasa', identifier, 'https://images.nasa.gov/details/' + quote(identifier, safe=''),
            title=metadata.get('title'), author=metadata.get('secondary_creator') or metadata.get('photographer'),
            license=metadata.get('license') or metadata.get('rights'), published=metadata.get('date_created'),
            description=metadata.get('description'), publisher=metadata.get('center') or 'NASA', source_type='official',
            variants=variants, limitations=['NASA 托管不自动表示公共领域；许可仍需按原始来源记录'])

    def search(self, query, *, kind='any', limit=20, cursor=None):
        check_search(query, kind, limit)
        page = page_number(cursor)
        parameters = {'q': query, 'page': page, 'page_size': limit}
        if kind != 'any':
            parameters['media_type'] = kind
        payload = _json(self.http, self.base + '/search', parameters)
        collection = payload.get('collection')
        if not isinstance(collection, dict) or not isinstance(collection.get('items'), list):
            raise MaterialError('invalid-response', 'NASA 接口缺少有效 collection/items', stage='discover')
        items = [item for raw in collection['items'] if isinstance(raw, dict) and (item := self._source(raw))]
        metadata = collection.get('metadata')
        total = integer(metadata.get('total_hits'), zero=True) if isinstance(metadata, dict) else None
        more = page * limit < total if total is not None else len(collection['items']) == limit
        return SearchPage(items, str(page+1) if more else None, total)

    def resolve(self, item):
        if item.provider != self.name or not item.externalId:
            raise MaterialError('invalid-request', 'NASA 来源身份不匹配', stage='resolve')
        payload = _json(self.http, self.base + '/asset/' + quote(item.externalId, safe=''))
        collection = payload.get('collection')
        items = collection.get('items') if isinstance(collection, dict) else None
        if not isinstance(items, list):
            raise MaterialError('invalid-response', 'NASA 条目缺少资产列表', stage='resolve')
        variants, locators = [], {}
        kinds = {'.mp4': 'video', '.mov': 'video', '.webm': 'video', '.jpg': 'image', '.jpeg': 'image',
                 '.png': 'image', '.tif': 'image', '.tiff': 'image', '.mp3': 'audio', '.wav': 'audio',
                 '.srt': 'subtitle', '.vtt': 'subtitle'}
        for raw in items[:512]:
            locator = raw.get('href') if isinstance(raw, dict) else None
            if not isinstance(locator, str):
                continue
            target = validate_url(locator)
            suffix = PurePosixPath(target.path.split('?', 1)[0]).suffix.lower()
            if suffix not in kinds:
                continue
            identifier = 'asset-' + fingerprint(target.url.split('?', 1)[0])[:20]
            if identifier in locators:
                continue
            variants.append(variant(identifier, locator, kind=kinds[suffix]))
            locators[identifier] = target.url
            if len(variants) == 128:
                break
        current = _updated(item, variants)
        if (not any(entry.kind == 'subtitle' for entry in variants)
                and any(entry.kind in {'video', 'audio'} for entry in item.variants)):
            try:
                captions = _json(self.http, self.base + '/captions/' + quote(item.externalId, safe=''))
                locator = captions.get('location')
                if isinstance(locator, str):
                    target = validate_url(locator)
                    variants.append(variant('captions', target.url, kind='subtitle'))
                    locators['captions'] = target.url
            except MaterialError as exc:
                if exc.code != 'not-found':
                    logger.warning('NASA 可选字幕元数据受限 code=%s', exc.code)
                    current.limitations.append(f'字幕元数据未验证（{exc.code}）；可继续无字幕并稍后补查')
        return ResolvedSource(_updated(current, variants), locators)
